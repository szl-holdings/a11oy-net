/* SPDX-License-Identifier: Apache-2.0 */
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { webcrypto } = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../estate/alloy-os/kernel.js'), 'utf8');
const sandbox = { module: { exports: {} }, TextEncoder, TextDecoder, Uint8Array, console };
vm.runInNewContext(source, sandbox);
const { createKernel } = sandbox.module.exports;
function fixture() {
  let data;
  let writer = Promise.resolve();
  const store = { load: async () => structuredClone(data), save: async value => { data = structuredClone(value); } };
  const lock = work => { const out = writer.then(work); writer = out.catch(() => {}); return out; };
  const create = () => createKernel({ crypto: webcrypto, store, lock });
  return { store, create, get: () => structuredClone(data), put: value => { data = structuredClone(value); } };
}
const input = { title: 'PRIVATE TITLE MARKER', body: 'PRIVATE BODY MARKER', policyClass: 'private', adapter: 'alloy-local-v1' };
test('actual encryption, signed admission and nonextractable private keys', async () => {
  const f = fixture(), k = f.create(); await k.boot();
  const result = await k.govern(input);
  assert.equal(result.decision, 'ALLOW'); assert.equal(result.receipt.signature.length, 128);
  assert.equal(k.capsules[0].status, 'VERIFIED'); assert.equal(k.health.ledgerReplayable, true);
  const state = f.get();
  assert.equal(state.encryptionKey.extractable, false); assert.equal(state.keys.privateKey.extractable, false);
  assert.equal(JSON.stringify(state).includes(input.body), false);
  assert.equal(JSON.stringify(state).includes(input.title), false);
  await assert.rejects(webcrypto.subtle.exportKey('raw', state.encryptionKey));
  await assert.rejects(webcrypto.subtle.exportKey('pkcs8', state.keys.privateKey));
});
test('reload preserves identity, decryptable payload and receipt chain', async () => {
  const f = fixture(), first = f.create(); await first.boot(); await first.govern(input);
  const second = f.create(); await second.boot();
  assert.equal(second.identity.kid, first.identity.kid); assert.equal(second.receipts[0].digest, first.receipts[0].digest);
  assert.equal(second.capsules[0].title, input.title); assert.equal(second.status, 'LOCAL_READY');
});
test('duplicate payload reuses a verified capsule with a new chained receipt', async () => {
  const f = fixture(), k = f.create(); await k.boot(); await k.govern(input); await k.govern(input);
  assert.equal(k.capsules.length, 1); assert.equal(k.receipts.length, 2);
  assert.equal(k.receipts[1].type, 'REUSE'); assert.equal(k.receipts[1].prev, k.receipts[0].digest);
});
test('stale adapter, public policy, malformed input and oversized canonical bytes fail closed', async () => {
  const f = fixture(), k = f.create(); await k.boot();
  for (const value of [null, {...input, adapter:'alloy-local-v0'}, {...input, policyClass:'public'}, {...input, title:''}, {...input, body:'\0'.repeat(32768)}]) {
    const out = await k.govern(value); assert.equal(out.decision,'DENY');
  }
  assert.equal(k.capsules.length, 0); assert.equal(k.health.blocked, 5);
});
test('one-byte fault is detected and only an authenticated snapshot is restored', async () => {
  const f = fixture(), k = f.create(); await k.boot(); await k.govern(input);
  const before = f.get(); await k.injectFault();
  const after = f.get();
  const a = Buffer.from(before.capsules[0].ciphertext,'hex'), b = Buffer.from(after.capsules[0].ciphertext,'hex');
  assert.equal(a.filter((v,i) => v !== b[i]).length, 1);
  assert.equal(k.status,'DEGRADED'); assert.equal(k.capsules[0].status,'CORRUPT');
  const out = await k.runWatchdog(); assert.equal(out.restored,1); assert.equal(out.verified,true);
  assert.equal(k.status,'LOCAL_READY'); assert.equal(k.health.healed,1);
  assert.equal(f.get().capsules[0].ciphertext,before.capsules[0].ciphertext);
});
test('tampered backup is not called healing and no bytes are overwritten', async () => {
  const f = fixture(), k = f.create(); await k.boot(); await k.govern(input); await k.injectFault();
  const state=f.get(); state.capsules[0].backup.ciphertext='00'+state.capsules[0].backup.ciphertext.slice(2);
  if (state.capsules[0].backup.ciphertext === f.get().capsules[0].backup.ciphertext) state.capsules[0].backup.ciphertext='ff'+state.capsules[0].backup.ciphertext.slice(2);
  f.put(state); const preserved=JSON.stringify(f.get());
  await assert.rejects(k.runWatchdog(), /No verified local snapshot/);
  assert.equal(JSON.stringify(f.get()),preserved); assert.equal(k.status,'UNAVAILABLE');
});
test('receipt tampering is rejected on reload, with no reset or key replacement', async () => {
  const f = fixture(), k = f.create(); await k.boot(); await k.govern(input);
  const state=f.get(); state.receipts[0].note='forged'; f.put(state);
  const preserved=JSON.stringify(f.get()); const next=f.create();
  await assert.rejects(next.boot(), /verification failed/);
  assert.equal(JSON.stringify(f.get()),preserved); assert.equal(next.health.ledgerReplayable,false);
});
test('storage failures cannot produce an ALLOW or phantom committed state', async () => {
  const f=fixture(), k=f.create(); await k.boot(); const before=JSON.stringify(f.get());
  f.store.save=async () => { throw new Error('simulated quota failure'); };
  await assert.rejects(k.govern(input), /quota/); assert.equal(JSON.stringify(f.get()),before);
  assert.equal(k.receipts.length,0); assert.equal(k.status,'UNAVAILABLE');
});
test('two local instances serialize writes against the same persisted snapshot', async () => {
  const f=fixture(), a=f.create(), b=f.create(); await Promise.all([a.boot(),b.boot()]);
  await Promise.all([a.govern(input),b.govern({...input, body:'second'}),a.govern({...input,body:'third'})]);
  const final=f.create(); await final.boot(); assert.equal(final.receipts.length,3); assert.equal(final.capsules.length,3);
  assert.equal(final.health.ledgerReplayable,true); assert.equal(final.receipts[2].prev, final.receipts[1].digest);
});
test('missing Web Locks is unavailable, not unsafe in-memory fallback', async () => {
  const f=fixture(), k=createKernel({crypto:webcrypto,store:f.store,lock:null});
  await assert.rejects(k.boot(), /Web Locks/); assert.equal(f.get(),undefined);
});
test('returned views cannot mutate the authoritative state', async () => {
  const f=fixture(), k=f.create(); await k.boot(); await k.govern(input);
  const rows=k.receipts; rows[0].note='changed view'; const caps=k.capsules; caps[0].status='invented';
  assert.notEqual(k.receipts[0].note,'changed view'); assert.equal(k.capsules[0].status,'VERIFIED');
});
test('kernel has no network, third-party loader, timers or string-code execution', () => {
  for (const token of ['fetch(', 'XMLHttpRequest', 'sendBeacon', 'WebSocket', 'eval(', 'new Function', 'setInterval', 'localStorage', 'sessionStorage']) assert.equal(source.includes(token), false, token);
});
