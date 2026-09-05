(() => {
  "use strict";

  const DB_NAME = "a11oy-alloy-local-v1";
  const DB_VERSION = 1;
  const STORE = "kernel";
  const STATE_KEY = "state";
  const ADAPTER_CURRENT = "alloy-local-v1";
  const MAX_RECEIPTS = 256;
  const MAX_CAPSULES = 64;
  const enc = new TextEncoder();
  const dec = new TextDecoder();
  const listeners = new Set();

  const state = {
    status: "BOOTING",
    epoch: 0,
    identity: null,
    keys: { signing: null, verifying: null, sealing: null },
    receipts: [],
    capsules: [],
    health: {
      healed: 0,
      blocked: 0,
      ledgerReplayable: false,
      lastVerify: "not-run",
      persistence: "probing",
    },
    db: null,
  };

  function notify() {
    for (const listener of [...listeners]) {
      try { listener(snapshot()); } catch (_) { /* observers are non-authoritative */ }
    }
  }

  function snapshot() {
    return {
      status: state.status,
      epoch: state.epoch,
      identity: state.identity ? { kid: state.identity.kid } : null,
      health: { ...state.health },
      receipts: state.receipts.map((row) => ({ ...row })),
      capsules: state.capsules.map((row) => ({ ...row })),
    };
  }

  function stable(value) {
    if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
    if (value && typeof value === "object") {
      return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stable(value[key])}`).join(",")}}`;
    }
    return JSON.stringify(value);
  }

  function b64url(bytes) {
    let binary = "";
    const view = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
    for (let index = 0; index < view.length; index += 1) binary += String.fromCharCode(view[index]);
    return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
  }

  function fromB64url(value) {
    const padded = String(value).replace(/-/g, "+").replace(/_/g, "/") + "===".slice((String(value).length + 3) % 4);
    const binary = atob(padded);
    const out = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) out[index] = binary.charCodeAt(index);
    return out;
  }

  async function sha256(value) {
    const bytes = typeof value === "string" ? enc.encode(value) : value;
    return b64url(await crypto.subtle.digest("SHA-256", bytes));
  }

  function shortHex(value) {
    const text = String(value || "UNKNOWN");
    return text.length > 18 ? `${text.slice(0, 10)}…${text.slice(-6)}` : text;
  }

  function openDb() {
    return new Promise((resolve, reject) => {
      if (!("indexedDB" in window)) {
        reject(new Error("IndexedDB unavailable"));
        return;
      }
      const request = indexedDB.open(DB_NAME, DB_VERSION);
      request.onupgradeneeded = () => {
        const db = request.result;
        if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE);
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error || new Error("IndexedDB open failed"));
      request.onblocked = () => reject(new Error("IndexedDB upgrade blocked"));
    });
  }

  function dbGet(db, key) {
    return new Promise((resolve, reject) => {
      const request = db.transaction(STORE, "readonly").objectStore(STORE).get(key);
      request.onsuccess = () => resolve(request.result ?? null);
      request.onerror = () => reject(request.error || new Error("IndexedDB read failed"));
    });
  }

  function dbPut(db, key, value) {
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, "readwrite");
      tx.objectStore(STORE).put(value, key);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error || new Error("IndexedDB write failed"));
      tx.onabort = () => reject(tx.error || new Error("IndexedDB write aborted"));
    });
  }

  async function importKeys(identity) {
    const signing = await crypto.subtle.importKey(
      "jwk",
      identity.privateJwk,
      { name: "ECDSA", namedCurve: "P-256" },
      false,
      ["sign"],
    );
    const verifying = await crypto.subtle.importKey(
      "jwk",
      identity.publicJwk,
      { name: "ECDSA", namedCurve: "P-256" },
      false,
      ["verify"],
    );
    const sealing = await crypto.subtle.importKey(
      "jwk",
      identity.sealingJwk,
      { name: "AES-GCM", length: 256 },
      false,
      ["encrypt", "decrypt"],
    );
    state.keys = { signing, verifying, sealing };
  }

  async function createIdentity() {
    const signPair = await crypto.subtle.generateKey(
      { name: "ECDSA", namedCurve: "P-256" },
      true,
      ["sign", "verify"],
    );
    const sealing = await crypto.subtle.generateKey(
      { name: "AES-GCM", length: 256 },
      true,
      ["encrypt", "decrypt"],
    );
    const publicJwk = await crypto.subtle.exportKey("jwk", signPair.publicKey);
    const privateJwk = await crypto.subtle.exportKey("jwk", signPair.privateKey);
    const sealingJwk = await crypto.subtle.exportKey("jwk", sealing);
    const kid = `local-${(await sha256(stable(publicJwk))).slice(0, 16)}`;
    const identity = { kid, publicJwk, privateJwk, sealingJwk };
    await importKeys(identity);
    return identity;
  }

  function persistedState() {
    return {
      schema: "a11oy.local-kernel-state/v1",
      adapter: ADAPTER_CURRENT,
      epoch: state.epoch,
      identity: state.identity,
      receipts: state.receipts.slice(-MAX_RECEIPTS),
      capsules: state.capsules.slice(-MAX_CAPSULES),
      health: {
        healed: state.health.healed,
        blocked: state.health.blocked,
      },
    };
  }

  async function persist() {
    if (!state.db) return;
    try {
      await dbPut(state.db, STATE_KEY, persistedState());
      state.health.persistence = "indexeddb";
    } catch (_) {
      state.health.persistence = "degraded";
      state.status = "DEGRADED · PERSISTENCE FAILED";
    }
  }

  async function appendReceipt(type, note, detail = {}) {
    const seq = state.receipts.length ? state.receipts[state.receipts.length - 1].seq + 1 : 1;
    const prev = state.receipts.length ? state.receipts[state.receipts.length - 1].digest : "GENESIS";
    const body = {
      schema: "a11oy.local-receipt/v1",
      seq,
      type,
      note,
      detail,
      prev,
      epoch: state.epoch,
      at: new Date().toISOString(),
      kid: state.identity.kid,
    };
    const digest = await sha256(stable(body));
    const signature = b64url(await crypto.subtle.sign(
      { name: "ECDSA", hash: "SHA-256" },
      state.keys.signing,
      enc.encode(stable(body)),
    ));
    const receipt = { ...body, digest, signature, algorithm: "ECDSA-P256-SHA256" };
    state.receipts.push(receipt);
    if (state.receipts.length > MAX_RECEIPTS) state.receipts.splice(0, state.receipts.length - MAX_RECEIPTS);
    return receipt;
  }

  async function verifyLedger() {
    let prev = state.receipts.length ? state.receipts[0].prev : "GENESIS";
    let expectedSeq = state.receipts.length ? state.receipts[0].seq : 1;
    for (const receipt of state.receipts) {
      const { digest, signature, algorithm: _, ...body } = receipt;
      if (receipt.seq !== expectedSeq || receipt.prev !== prev) return false;
      if (await sha256(stable(body)) !== digest) return false;
      const valid = await crypto.subtle.verify(
        { name: "ECDSA", hash: "SHA-256" },
        state.keys.verifying,
        fromB64url(signature),
        enc.encode(stable(body)),
      );
      if (!valid) return false;
      prev = digest;
      expectedSeq += 1;
    }
    return true;
  }

  async function verifyCapsule(capsule) {
    try {
      const plaintext = await crypto.subtle.decrypt(
        { name: "AES-GCM", iv: fromB64url(capsule.iv), additionalData: enc.encode(capsule.adapter) },
        state.keys.sealing,
        fromB64url(capsule.ciphertext),
      );
      return (await sha256(plaintext)) === capsule.digest;
    } catch (_) {
      return false;
    }
  }

  async function govern(input = {}) {
    if (!state.identity) throw new Error("kernel not booted");
    const title = String(input.title || "Untitled").slice(0, 160);
    const body = String(input.body || "");
    const policyClass = String(input.policyClass || "private").slice(0, 64);
    const adapter = String(input.adapter || "");

    if (adapter !== ADAPTER_CURRENT) {
      state.health.blocked += 1;
      const receipt = await appendReceipt("policy.block", "stale or unknown adapter denied", {
        adapter,
        expected: ADAPTER_CURRENT,
        policyClass,
      });
      await persist();
      notify();
      return { decision: "BLOCK", reason: `adapter must equal ${ADAPTER_CURRENT}`, receipt };
    }
    if (!body.trim()) {
      state.health.blocked += 1;
      const receipt = await appendReceipt("policy.block", "empty payload denied", { policyClass, adapter });
      await persist();
      notify();
      return { decision: "BLOCK", reason: "payload is empty", receipt };
    }

    const plaintext = enc.encode(body);
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const ciphertext = new Uint8Array(await crypto.subtle.encrypt(
      { name: "AES-GCM", iv, additionalData: enc.encode(adapter) },
      state.keys.sealing,
      plaintext,
    ));
    const digest = await sha256(plaintext);
    const capsule = {
      id: `cap-${digest.slice(0, 18)}-${Date.now().toString(36)}`,
      title,
      policyClass,
      adapter,
      digest,
      iv: b64url(iv),
      ciphertext: b64url(ciphertext),
      backupCiphertext: b64url(ciphertext),
      status: "sealed",
      createdAt: new Date().toISOString(),
    };
    state.capsules.push(capsule);
    if (state.capsules.length > MAX_CAPSULES) state.capsules.splice(0, state.capsules.length - MAX_CAPSULES);
    const receipt = await appendReceipt("capsule.sealed", "payload encrypted and content-addressed locally", {
      capsuleId: capsule.id,
      digest,
      policyClass,
      adapter,
    });
    state.health.ledgerReplayable = await verifyLedger();
    state.health.lastVerify = new Date().toISOString();
    await persist();
    notify();
    return { decision: "ALLOW", reason: "policy accepted; capsule sealed on-device", receipt, capsule: { ...capsule, backupCiphertext: undefined } };
  }

  async function injectFault() {
    if (!state.identity) throw new Error("kernel not booted");
    const capsule = [...state.capsules].reverse().find((row) => row.status !== "quarantined");
    if (!capsule) return "No capsule exists. Submit an envelope first.";
    const bytes = fromB64url(capsule.ciphertext);
    if (!bytes.length) return "Capsule has no ciphertext to perturb.";
    bytes[Math.floor(bytes.length / 2)] ^= 0x01;
    capsule.ciphertext = b64url(bytes);
    capsule.status = "tampered";
    await appendReceipt("fault.injected", "one ciphertext bit flipped for local recovery test", { capsuleId: capsule.id });
    state.health.ledgerReplayable = await verifyLedger();
    state.health.lastVerify = new Date().toISOString();
    await persist();
    notify();
    return `Tamper injected into ${capsule.id}. Run healer to verify and restore the sealed snapshot.`;
  }

  async function runWatchdog() {
    if (!state.identity) throw new Error("kernel not booted");
    let healedNow = 0;
    let quarantinedNow = 0;
    for (const capsule of state.capsules) {
      if (await verifyCapsule(capsule)) {
        if (capsule.status === "healed") capsule.status = "sealed";
        continue;
      }
      if (capsule.backupCiphertext) {
        const damaged = capsule.ciphertext;
        capsule.ciphertext = capsule.backupCiphertext;
        if (await verifyCapsule(capsule)) {
          capsule.status = "healed";
          capsule.lastFaultCiphertext = damaged;
          healedNow += 1;
          await appendReceipt("capsule.healed", "tampered ciphertext restored from local sealed snapshot", { capsuleId: capsule.id, digest: capsule.digest });
          continue;
        }
      }
      capsule.status = "quarantined";
      quarantinedNow += 1;
      await appendReceipt("capsule.quarantined", "capsule failed cryptographic verification and had no valid recovery image", { capsuleId: capsule.id });
    }
    state.health.healed += healedNow;
    state.health.ledgerReplayable = await verifyLedger();
    state.health.lastVerify = new Date().toISOString();
    if (!state.health.ledgerReplayable) state.status = "DEGRADED · LEDGER VERIFY FAILED";
    else if (quarantinedNow) state.status = "DEGRADED · CAPSULE QUARANTINED";
    else state.status = state.db ? "LOCAL REAL · VERIFIED" : "DEGRADED · MEMORY ONLY";
    await persist();
    notify();
    return { healed: healedNow, quarantined: quarantinedNow, ledgerReplayable: state.health.ledgerReplayable };
  }

  async function boot() {
    if (!(window.crypto && crypto.subtle && crypto.getRandomValues)) {
      state.status = "UNAVAILABLE · WEBCRYPTO REQUIRED";
      state.health.lastVerify = "unavailable";
      notify();
      throw new Error("WebCrypto unavailable");
    }
    let saved = null;
    try {
      state.db = await openDb();
      saved = await dbGet(state.db, STATE_KEY);
      state.health.persistence = "indexeddb";
    } catch (_) {
      state.db = null;
      state.health.persistence = "memory-only";
    }

    if (saved && saved.schema === "a11oy.local-kernel-state/v1" && saved.identity) {
      state.identity = saved.identity;
      state.epoch = Number(saved.epoch || 0) + 1;
      state.receipts = Array.isArray(saved.receipts) ? saved.receipts.slice(-MAX_RECEIPTS) : [];
      state.capsules = Array.isArray(saved.capsules) ? saved.capsules.slice(-MAX_CAPSULES) : [];
      state.health.healed = Number(saved.health?.healed || 0);
      state.health.blocked = Number(saved.health?.blocked || 0);
      try {
        await importKeys(state.identity);
      } catch (_) {
        state.identity = await createIdentity();
        state.receipts = [];
        state.capsules = [];
        state.epoch = 1;
      }
    } else {
      state.identity = await createIdentity();
      state.epoch = 1;
    }

    state.health.ledgerReplayable = await verifyLedger();
    state.health.lastVerify = new Date().toISOString();
    if (!state.receipts.length) await appendReceipt("kernel.boot", "local WebCrypto kernel initialized", { persistence: state.health.persistence, adapter: ADAPTER_CURRENT });
    else await appendReceipt("kernel.resume", "local WebCrypto kernel resumed", { persistence: state.health.persistence, adapter: ADAPTER_CURRENT });
    state.health.ledgerReplayable = await verifyLedger();
    state.health.lastVerify = new Date().toISOString();
    state.status = state.db ? "LOCAL REAL · VERIFIED" : "DEGRADED · MEMORY ONLY";
    await persist();
    notify();
    return snapshot();
  }

  const Alloy = {
    ADAPTER_CURRENT,
    get status() { return state.status; },
    get epoch() { return state.epoch; },
    get identity() { return state.identity ? { kid: state.identity.kid } : null; },
    get receipts() { return state.receipts; },
    get capsules() { return state.capsules; },
    get health() { return state.health; },
    shortHex,
    subscribe(listener) {
      if (typeof listener !== "function") throw new TypeError("listener must be a function");
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    boot,
    govern,
    injectFault,
    runWatchdog,
  };

  Object.defineProperty(window, "Alloy", {
    value: Object.freeze(Alloy),
    writable: false,
    configurable: false,
    enumerable: true,
  });
})();
