/* SPDX-License-Identifier: Apache-2.0
 * Local-device demonstration only. Same-origin keys are not an independent
 * trust anchor. Browser storage can be cleared; this is not a product ledger.
 * Recovery restores only a verified local ciphertext snapshot, never evidence.
 */
(function (root) {
  'use strict';
  const ADAPTER = 'alloy-local-v1';
  const SCHEMA = 'szl.local-capsule/v1';
  const MAX_RECEIPTS = 1024;
  const MAX_CAPSULES = 128;
  const encoder = new TextEncoder();
  const decoder = new TextDecoder('utf-8', { fatal: true });
  const HEX = /^[0-9a-f]{64}$/;
  const encode = value => encoder.encode(JSON.stringify(value));
  const hex = bytes => Array.from(new Uint8Array(bytes), b => b.toString(16).padStart(2, '0')).join('');
  function unhex(value) {
    if (typeof value !== 'string' || value.length % 2 || !/^[0-9a-f]*$/.test(value)) throw new Error('Invalid encoded bytes');
    return Uint8Array.from(value.match(/../g) || [], byte => parseInt(byte, 16));
  }
  function fields(receipt) {
    return { seq: receipt.seq, prev: receipt.prev, type: receipt.type, note: receipt.note,
      capsuleDigest: receipt.capsuleDigest, encryptedDigest: receipt.encryptedDigest,
      kid: receipt.kid, at: receipt.at };
  }
  function browserStore() {
    let promise;
    function open() {
      if (!root.indexedDB) return Promise.reject(new Error('IndexedDB is unavailable'));
      if (!promise) promise = new Promise((resolve, reject) => {
        const request = root.indexedDB.open('szl-alloy-local-v1', 1);
        request.onupgradeneeded = () => request.result.createObjectStore('state');
        request.onerror = () => reject(new Error('Local storage could not be opened'));
        request.onblocked = () => reject(new Error('Close an older local-kernel tab before upgrading'));
        request.onsuccess = () => {
          const database = request.result;
          database.onversionchange = () => { database.close(); promise = null; };
          resolve(database);
        };
      });
      return promise;
    }
    async function transact(mode, value) {
      const database = await open();
      return new Promise((resolve, reject) => {
        const tx = database.transaction('state', mode);
        const store = tx.objectStore('state');
        const request = mode === 'readonly' ? store.get('kernel') : store.put(value, 'kernel');
        let result;
        request.onsuccess = () => { result = request.result; };
        tx.oncomplete = () => resolve(result);
        tx.onabort = tx.onerror = () => reject(new Error('Local storage transaction failed; no success is claimed'));
      });
    }
    return { load: () => transact('readonly'), save: value => transact('readwrite', value) };
  }
  function createKernel(options) {
    const crypto = options.crypto;
    const store = options.store;
    const lock = options.lock;
    const now = options.now || (() => new Date().toISOString());
    const listeners = new Set();
    let queue = Promise.resolve();
    let view = { status: 'NOT_STARTED', identity: null, epoch: 0, receipts: [], capsules: [],
      health: { healed: 0, blocked: 0, ledgerReplayable: false, lastVerify: null } };
    const hash = async value => hex(await crypto.subtle.digest('SHA-256', value));
    const cipherHash = capsule => hash(encode({ iv: capsule.iv, ciphertext: capsule.ciphertext }));
    const notify = () => { for (const fn of listeners) { try { fn(); } catch (_) { /* UI errors do not commit data. */ } } };
    const snapshot = value => JSON.parse(JSON.stringify(value));
    async function identity(keys) {
      return (await hash(await crypto.subtle.exportKey('spki', keys.publicKey))).slice(0, 32);
    }
    async function fresh() {
      const encryptionKey = await crypto.subtle.generateKey({ name: 'AES-GCM', length: 256 }, false, ['encrypt', 'decrypt']);
      const keys = await crypto.subtle.generateKey({ name: 'ECDSA', namedCurve: 'P-256' }, false, ['sign', 'verify']);
      return { schema: SCHEMA, encryptionKey, keys, kid: await identity(keys), receipts: [], capsules: [], epoch: 0 };
    }
    async function decrypt(state, capsule) {
      const plain = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: unhex(capsule.iv),
        additionalData: encoder.encode(capsule.digest), tagLength: 128 }, state.encryptionKey, unhex(capsule.ciphertext));
      if (await hash(plain) !== capsule.digest) throw new Error('Capsule content address mismatch');
      const value = JSON.parse(decoder.decode(plain));
      if (typeof value.title !== 'string' || typeof value.body !== 'string' || value.policyClass !== 'private') throw new Error('Invalid decrypted capsule');
      return value;
    }
    async function verify(state) {
      if (!state || state.schema !== SCHEMA || !Array.isArray(state.receipts) || !Array.isArray(state.capsules)
        || state.receipts.length > MAX_RECEIPTS || state.capsules.length > MAX_CAPSULES
        || state.epoch !== state.receipts.length || !state.keys || state.keys.privateKey.extractable !== false
        || state.encryptionKey.extractable !== false || await identity(state.keys) !== state.kid) throw new Error('Local state or key identity is invalid; preserved without replacement');
      let previous = '0'.repeat(64);
      const seals = new Map();
      for (let i = 0; i < state.receipts.length; i++) {
        const receipt = state.receipts[i];
        if (receipt.seq !== i + 1 || receipt.prev !== previous || receipt.kid !== state.kid
          || !['SEAL', 'REUSE', 'DENY', 'FAULT_TEST', 'RESTORE'].includes(receipt.type)
          || typeof receipt.note !== 'string' || receipt.note.length > 160
          || typeof receipt.at !== 'string' || receipt.at.length > 40
          || !HEX.test(receipt.capsuleDigest) || !HEX.test(receipt.encryptedDigest)
          || !HEX.test(receipt.digest) || typeof receipt.signature !== 'string' || receipt.signature.length !== 128) throw new Error('Receipt structure or chain link is invalid');
        const bytes = encode(fields(receipt));
        if (await hash(bytes) !== receipt.digest || !await crypto.subtle.verify({ name: 'ECDSA', hash: 'SHA-256' },
          state.keys.publicKey, unhex(receipt.signature), bytes)) throw new Error('Local receipt verification failed');
        if (receipt.type === 'SEAL') {
          if (seals.has(receipt.capsuleDigest)) throw new Error('Duplicate capsule admission');
          seals.set(receipt.capsuleDigest, receipt.encryptedDigest);
        }
        previous = receipt.digest;
      }
      if (seals.size !== state.capsules.length) throw new Error('Capsule inventory does not match signed admissions');
      const seen = new Set();
      const capsules = [];
      for (const capsule of state.capsules) {
        if (!HEX.test(capsule.digest) || seen.has(capsule.digest) || !seals.has(capsule.digest)) throw new Error('Capsule identity is invalid');
        seen.add(capsule.digest);
        let title = 'Encrypted capsule', status = 'CORRUPT';
        try {
          if (typeof capsule.iv !== 'string' || capsule.iv.length !== 24 || typeof capsule.ciphertext !== 'string'
            || capsule.ciphertext.length > 140000 || await cipherHash(capsule) !== seals.get(capsule.digest)) throw new Error('Ciphertext integrity mismatch');
          title = (await decrypt(state, capsule)).title;
          status = 'VERIFIED';
        } catch (_) { /* Preserve corrupt ciphertext; only a verified snapshot can restore it. */ }
        capsules.push({ title, status, digest: capsule.digest });
      }
      return { capsules, seals };
    }
    function present(state, checked) {
      view = { status: checked.capsules.some(c => c.status !== 'VERIFIED') ? 'DEGRADED' : 'LOCAL_READY',
        identity: { kid: state.kid, scope: 'THIS_BROWSER_ORIGIN_ONLY' }, epoch: state.epoch,
        receipts: state.receipts.map(r => ({ ...fields(r), digest: r.digest, signature: r.signature })),
        capsules: checked.capsules, health: {
          healed: state.receipts.filter(r => r.type === 'RESTORE').length,
          blocked: state.receipts.filter(r => r.type === 'DENY').length,
          ledgerReplayable: true, lastVerify: now() } };
      notify();
    }
    async function append(state, type, note, capsuleDigest = '0'.repeat(64), encryptedDigest = '0'.repeat(64)) {
      if (state.receipts.length >= MAX_RECEIPTS) throw new Error('Local ledger capacity reached; existing evidence is preserved');
      const receipt = { seq: state.receipts.length + 1, prev: state.receipts.at(-1)?.digest || '0'.repeat(64),
        type, note, capsuleDigest, encryptedDigest, kid: state.kid, at: now() };
      const bytes = encode(fields(receipt));
      receipt.digest = await hash(bytes);
      receipt.signature = hex(await crypto.subtle.sign({ name: 'ECDSA', hash: 'SHA-256' }, state.keys.privateKey, bytes));
      state.receipts.push(receipt);
      state.epoch = state.receipts.length;
      return snapshot(receipt);
    }
    function exclusive(work) {
      const task = queue.then(async () => {
        if (!crypto?.subtle || typeof lock !== 'function') throw new Error('Secure WebCrypto and cross-tab Web Locks are required');
        return lock(work);
      });
      queue = task.catch(() => {});
      return task.catch(error => {
        view = { ...view, status: 'UNAVAILABLE', health: { ...view.health, ledgerReplayable: false } };
        notify();
        throw error;
      });
    }
    function change(operation) {
      return exclusive(async () => {
        const state = await store.load();
        const before = await verify(state);
        const result = await operation(state, before);
        const after = await verify(state);
        await store.save(state);
        present(state, after);
        return result;
      });
    }
    return Object.freeze({
      ADAPTER_CURRENT: ADAPTER,
      get status() { return view.status; },
      get identity() { return snapshot(view.identity); },
      get epoch() { return view.epoch; },
      get receipts() { return snapshot(view.receipts); },
      get capsules() { return snapshot(view.capsules); },
      get health() { return snapshot(view.health); },
      shortHex: value => String(value || '').slice(0, 12),
      subscribe(fn) { if (typeof fn !== 'function') throw new TypeError('Subscriber must be a function'); listeners.add(fn); return () => listeners.delete(fn); },
      boot() {
        return exclusive(async () => {
          const existing = await store.load();
          const state = existing === undefined ? await fresh() : existing;
          const checked = await verify(state);
          if (existing === undefined) await store.save(state);
          present(state, checked);
        });
      },
      govern(input) {
        return change(async (state, checked) => {
          if (checked.capsules.some(c => c.status !== 'VERIFIED')) throw new Error('Restore or inspect corrupted local capsules before admitting new data');
          const valid = input && input.adapter === ADAPTER && input.policyClass === 'private'
            && typeof input.title === 'string' && input.title.trim().length > 0 && input.title.length <= 200
            && typeof input.body === 'string' && input.body.length <= 32768
            && encode({ title: input.title, body: input.body, policyClass: 'private' }).length <= 32768;
          if (!valid) return { decision: 'DENY', reason: 'Adapter, local-private policy, or input bounds rejected',
            receipt: await append(state, 'DENY', 'Local input contract rejected') };
          const plaintext = encode({ title: input.title, body: input.body, policyClass: 'private' });
          const digest = await hash(plaintext);
          const prior = state.capsules.find(c => c.digest === digest);
          if (prior) return { decision: 'ALLOW', reason: 'Verified local capsule reused',
            receipt: await append(state, 'REUSE', 'Verified local capsule reused', digest, checked.seals.get(digest)) };
          if (state.capsules.length >= MAX_CAPSULES) throw new Error('Local capsule capacity reached; nothing was evicted');
          const iv = crypto.getRandomValues(new Uint8Array(12));
          const ciphertext = await crypto.subtle.encrypt({ name: 'AES-GCM', iv, additionalData: encoder.encode(digest), tagLength: 128 }, state.encryptionKey, plaintext);
          const capsule = { digest, iv: hex(iv), ciphertext: hex(ciphertext) };
          capsule.backup = { iv: capsule.iv, ciphertext: capsule.ciphertext };
          state.capsules.push(capsule);
          const receipt = await append(state, 'SEAL', 'Encrypted local capsule admitted', digest, await cipherHash(capsule));
          return { decision: 'ALLOW', reason: 'Encrypted, signed, and committed to this browser only', receipt };
        });
      },
      injectFault() {
        return change(async (state, checked) => {
          const capsule = state.capsules.at(-1);
          if (!capsule) throw new Error('Create a local capsule before the one-byte fault test');
          if (checked.capsules.some(c => c.status !== 'VERIFIED')) throw new Error('A fault is already present; no further corruption was applied');
          const bytes = unhex(capsule.ciphertext); bytes[0] ^= 1; capsule.ciphertext = hex(bytes);
          await append(state, 'FAULT_TEST', 'User-requested local one-byte fault test', capsule.digest, checked.seals.get(capsule.digest));
          return 'One byte changed in the local working ciphertext. The signed snapshot remains available for verification.';
        });
      },
      runWatchdog() {
        return change(async (state, checked) => {
          let restored = 0;
          for (let i = 0; i < checked.capsules.length; i++) {
            if (checked.capsules[i].status === 'VERIFIED') continue;
            const capsule = state.capsules[i];
            const backup = { ...capsule.backup, digest: capsule.digest };
            if (!capsule.backup || typeof backup.iv !== 'string' || backup.iv.length !== 24
              || typeof backup.ciphertext !== 'string' || backup.ciphertext.length > 140000
              || await cipherHash(backup) !== checked.seals.get(capsule.digest)) throw new Error('No verified local snapshot exists; original bytes are preserved');
            await decrypt(state, backup);
            capsule.iv = backup.iv; capsule.ciphertext = backup.ciphertext;
            await append(state, 'RESTORE', 'Restored only a verified local ciphertext snapshot', capsule.digest, checked.seals.get(capsule.digest));
            restored += 1;
          }
          return { restored, verified: true, scope: 'LOCAL_CIPHERTEXT_ONLY' };
        });
      }
    });
  }
  if (typeof module === 'object' && module.exports) module.exports = { createKernel };
  else root.Alloy = createKernel({ crypto: root.crypto, store: browserStore(),
    lock: root.navigator?.locks ? work => root.navigator.locks.request('szl-alloy-local-v1-writer', { mode: 'exclusive' }, work) : null });
})(globalThis);
