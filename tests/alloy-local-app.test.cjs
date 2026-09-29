// SPDX-License-Identifier: Apache-2.0
// (c) 2026 Lutar, Stephen P. - SZL Holdings - ORCID 0009-0001-0110-4173
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { webcrypto } = require('node:crypto');
const { createKernel } = require('../estate/alloy-os/kernel.js');
const source = fs.readFileSync(path.join(__dirname, '../estate/alloy-os/app.js'), 'utf8');
const snapshot = JSON.parse(fs.readFileSync(path.join(__dirname, '../estate/alloy-os/live.json'), 'utf8'));
const tick = () => new Promise(resolve => setImmediate(resolve));
const deferred = () => { let resolve; const promise = new Promise(r => resolve = r); return {promise, resolve}; };
function harness(fetcher = () => new Promise(() => {}), actualKernel) {
  const elements = new Map(), listeners = {}, timers = new Map(); let timerId = 0, boots = 0;
  for (const id of ['bake-rail', 'align-table', 'kernel-app', 'kproof']) elements.set(id, {
    innerHTML: '', listeners: {}, querySelectorAll: () => [],
    addEventListener(type, callback) { this.listeners[type] = callback; }
  });
  const kernel = actualKernel || {status:'LOCAL_READY', health:{ledgerReplayable:true}, identity:{kid:'identifier-only'},
    stages:[], receipts:[], capsules:[], energy:{}, ADAPTER_CURRENT:'alloy-local-v1',
    subscribe(){}, async boot(){boots++;}, shortHex: v => v};
  vm.runInNewContext(source, {URL, AbortController, Number, Error, Date,
    window:{Alloy:kernel, location:{href:'http://localhost/estate/alloy-os/'}, addEventListener:(type, cb) => listeners[type] = cb},
    document:{getElementById:id => elements.get(id) || null}, fetch:fetcher,
    setTimeout:fn => {timers.set(++timerId, fn); return timerId;}, clearTimeout:id => timers.delete(id)}, {timeout:1000});
  return {kernel, timers, listeners, boots:()=>boots, html:id=>elements.get(id).innerHTML,
    key:key=>listeners.keydown({key, target:{tagName:'BODY'}, preventDefault(){}}),
    proof:()=>elements.get('kproof').listeners.click()};
}
const ok = value => ({ok:true, status:200, json:async()=>value});
test('a hanging snapshot cannot block local boot or keyboard controls', async()=>{
  const h=harness(); await tick(); assert.equal(h.boots(),1); assert.match(h.html('kernel-app'),/LOCAL_READY/);
  h.listeners.keydown({key:'k',ctrlKey:true,preventDefault(){}}); assert.match(h.html('kernel-app'),/role="dialog"/);
  h.key('Escape'); assert.doesNotMatch(h.html('kernel-app'),/role="dialog"/);
  h.key('3'); assert.match(h.html('kernel-app'),/Replayable:/);
  for(const fire of h.timers.values()) fire(); await tick();
  assert.match(h.html('align-table'),/UNAVAILABLE.*timed out/); assert.match(h.html('kernel-app'),/LOCAL_READY/);
  assert.equal(h.timers.size,0);
});
test('timeout includes a stalled body and late completion cannot overwrite failure', async()=>{
  const body=deferred(); let signal;
  const h=harness(async(_,options)=>{signal=options.signal;return {ok:true,json:()=>body.promise};});await tick();
  for(const fire of h.timers.values())fire();await tick();assert.equal(signal.aborted,true);
  body.resolve(snapshot);await tick();assert.match(h.html('align-table'),/UNAVAILABLE.*timed out/);assert.equal(h.html('bake-rail'),'');
});
test('dated snapshot never becomes a live measurement and identifiers never verify signers',async()=>{
  const h=harness(async()=>ok({...snapshot,truth_label:'MEASURED'}));await tick();
  assert.match(h.html('bake-rail'),/SNAPSHOT/);assert.match(h.html('bake-rail'),/not a current measurement/);
  assert.doesNotMatch(h.html('bake-rail'),/>MEASURED</);
  assert.match(h.html('kernel-app'),/Device signer<\/td><td class="warn">UNAVAILABLE/);
  assert.match(h.html('kernel-app'),/Product signer<\/td><td class="">NOT_PROBED/);
  assert.equal(h.timers.size,0);
});
for(const kind of ['http','no date','bad count','bad row'])test(`invalid snapshot (${kind}) fails visibly without blocking the kernel`,async()=>{
  const data=JSON.parse(JSON.stringify(snapshot));if(kind==='no date')delete data.capturedAt;
  if(kind==='bad count')data.inventory.huggingface_models=-1;if(kind==='bad row')data.alignment=[null];
  const h=harness(async()=>kind==='http'?{ok:false,status:503}:ok(data));await tick();
  assert.match(h.html('align-table'),/UNAVAILABLE/);assert.match(h.html('kernel-app'),/LOCAL_READY/);assert.equal(h.timers.size,0);
});
const complete=()=>({commit:{decision:'ALLOW'},reuse:{decision:'ALLOW'},blocked:{decision:'DENY'},
  tamper:'A local fault was injected',heal:{verified:true,restored:1}});
for(const kind of ['complete','commit denied','reuse denied','adapter allowed','no fault','unverified heal','no restore','unreplayable'])
test(`local proof summary checks every step (${kind})`,async()=>{
  const h=harness();await tick();const result=complete();
  if(kind==='commit denied')result.commit.decision='DENY';if(kind==='reuse denied')result.reuse.decision='DENY';
  if(kind==='adapter allowed')result.blocked.decision='ALLOW';if(kind==='no fault')result.tamper=null;
  if(kind==='unverified heal')result.heal.verified=false;if(kind==='no restore')result.heal.restored=0;
  if(kind==='unreplayable')h.kernel.health.ledgerReplayable=false;
  h.kernel.runLocalProof=async()=>result;await h.proof();
  assert.match(h.html('kernel-app'),kind==='complete'?/Local proof complete —/:/Local proof incomplete —/);
});
test('real WebCrypto kernel completes the five-step local experiment with this UI',async()=>{
  let value;const store={kind:'TEST_MEMORY',durability:'VOLATILE',async load(){return value;},async save(next){value=structuredClone(next);}};
  let writer=Promise.resolve();
  const lock=work=>{const result=writer.then(work);writer=result.catch(()=>{});return result;};
  const kernel=createKernel({crypto:webcrypto,store,lock});await kernel.boot();
  const h=harness(async()=>ok(snapshot),kernel);await kernel.boot();await tick();await h.proof();
  assert.match(h.html('kernel-app'),/Local proof complete —/);assert.equal(kernel.health.ledgerReplayable,true);
  assert.ok(kernel.receipts.some(r=>r.type==='FAULT_TEST'));assert.ok(kernel.receipts.some(r=>r.type==='RESTORE'));
});
