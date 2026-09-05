"use strict";

/*
 * Alloy local kernel — proof-origin, browser-local execution only.
 *
 * This module performs no network requests. Keys and snapshots stay in this
 * origin's IndexedDB. A signature proves origin of bytes, not semantic truth.
 */
(() => {
  const ADAPTER_CURRENT = "alloy-local-v1";
  const DB_NAME = "a11oy-alloy-local-kernel";
  const DB_VERSION = 1;
  const STORE = "kernel";
  const CURRENT_KEY = "current";
  const SNAPSHOT_KEY = "last-verified";
  const encoder = new TextEncoder();
  const decoder = new TextDecoder();
  const listeners = new Set();

  let database = null;
  let encryptionKey = null;
  let signingKeys = null;
  let bootPromise = null;
  let state = freshState();

  function freshState() {
    return {
      schema: "szl.alloy-local-kernel/v1",
      status: "BOOTING",
      epoch: 0,
      identity: null,
      receipts: [],
      capsules: [],
      health: {
        healed: 0,
        blocked: 0,
        ledgerReplayable: false,
        lastVerify: null,
      },
    };
  }

  function stable(value) {
    if (Array.isArray(value)) return value.map(stable);
    if (value && typeof value === "object") {
      return Object.fromEntries(
        Object.keys(value)
          .sort()
          .map((key) => [key, stable(value[key])]),
      );
    }
    return value;
  }

  function canonical(value) {
    return JSON.stringify(stable(value));
  }

  function bytes(value) {
    return value instanceof Uint8Array ? value : encoder.encode(String(value));
  }

  function hex(buffer) {
    return [...new Uint8Array(buffer)]
      .map((value) => value.toString(16).padStart(2, "0"))
      .join("");
  }

  function base64url(buffer) {
    const binary = [...new Uint8Array(buffer)]
      .map((value) => String.fromCharCode(value))
      .join("");
    return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/u, "");
  }

  function fromBase64url(value) {
    const normalized = String(value).replaceAll("-", "+").replaceAll("_", "/");
    const padded = normalized + "=".repeat((4 - (normalized.length % 4)) % 4);
    return Uint8Array.from(atob(padded), (character) => character.charCodeAt(0));
  }

  async function sha256(value) {
    return hex(await crypto.subtle.digest("SHA-256", bytes(value)));
  }

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function shortHex(value) {
    const text = String(value || "");
    return text.length > 18 ? `${text.slice(0, 10)}…${text.slice(-6)}` : text || "—";
  }

  function notify() {
    for (const listener of listeners) {
      try {
        listener(snapshot());
      } catch (_error) {
        // A presentation listener cannot change kernel state.
      }
    }
  }

  function snapshot() {
    return {
      status: state.status,
      epoch: state.epoch,
      identity: clone(state.identity),
      receipts: clone(state.receipts),
      capsules: clone(state.capsules),
      health: clone(state.health),
    };
  }

  function openDatabase() {
    if (database) return Promise.resolve(database);
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);
      request.onupgradeneeded = () => {
        if (!request.result.objectStoreNames.contains(STORE)) {
          request.result.createObjectStore(STORE);
        }
      };
      request.onsuccess = () => {
        database = request.result;
        resolve(database);
      };
      request.onerror = () => reject(request.error || new Error("IndexedDB open failed"));
      request.onblocked = () => reject(new Error("IndexedDB upgrade blocked"));
    });
  }

  async function readRecord(key) {
    const db = await openDatabase();
    return new Promise((resolve, reject) => {
      const request = db.transaction(STORE, "readonly").objectStore(STORE).get(key);
      request.onsuccess = () => resolve(request.result || null);
      request.onerror = () => reject(request.error || new Error(`IndexedDB read failed: ${key}`));
    });
  }

  async function writeRecord(key, value) {
    const db = await openDatabase();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, "readwrite");
      tx.objectStore(STORE).put(value, key);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error || new Error(`IndexedDB write failed: ${key}`));
      tx.onabort = () => reject(tx.error || new Error(`IndexedDB write aborted: ${key}`));
    });
  }

  async function generateKeys() {
    encryptionKey = await crypto.subtle.generateKey(
      { name: "AES-GCM", length: 256 },
      true,
      ["encrypt", "decrypt"],
    );
    signingKeys = await crypto.subtle.generateKey(
      { name: "ECDSA", namedCurve: "P-256" },
      true,
      ["sign", "verify"],
    );
    const publicJwk = await crypto.subtle.exportKey("jwk", signingKeys.publicKey);
    state.identity = {
      algorithm: "ECDSA-P256-SHA256",
      kid: (await sha256(canonical(publicJwk))).slice(0, 24),
    };
  }

  async function exportKeys() {
    return {
      encryption: await crypto.subtle.exportKey("jwk", encryptionKey),
      signingPrivate: await crypto.subtle.exportKey("jwk", signingKeys.privateKey),
      signingPublic: await crypto.subtle.exportKey("jwk", signingKeys.publicKey),
    };
  }

  async function importKeys(keys) {
    encryptionKey = await crypto.subtle.importKey(
      "jwk",
      keys.encryption,
      { name: "AES-GCM", length: 256 },
      true,
      ["encrypt", "decrypt"],
    );
    signingKeys = {
      privateKey: await crypto.subtle.importKey(
        "jwk",
        keys.signingPrivate,
        { name: "ECDSA", namedCurve: "P-256" },
        true,
        ["sign"],
      ),
      publicKey: await crypto.subtle.importKey(
        "jwk",
        keys.signingPublic,
        { name: "ECDSA", namedCurve: "P-256" },
        true,
        ["verify"],
      ),
    };
  }

  async function serializedState() {
    return {
      schema: state.schema,
      status: state.status,
      epoch: state.epoch,
      identity: clone(state.identity),
      receipts: clone(state.receipts),
      capsules: clone(state.capsules),
      health: clone(state.health),
      keys: await exportKeys(),
    };
  }

  async function hydrate(record) {
    if (!record || record.schema !== "szl.alloy-local-kernel/v1" || !record.keys) {
      throw new Error("unsupported local-kernel snapshot");
    }
    await importKeys(record.keys);
    state = {
      schema: record.schema,
      status: String(record.status || "RECOVERING"),
      epoch: Number(record.epoch || 0),
      identity: clone(record.identity),
      receipts: Array.isArray(record.receipts) ? clone(record.receipts) : [],
      capsules: Array.isArray(record.capsules) ? clone(record.capsules) : [],
      health: {
        healed: Number(record.health?.healed || 0),
        blocked: Number(record.health?.blocked || 0),
        ledgerReplayable: Boolean(record.health?.ledgerReplayable),
        lastVerify: record.health?.lastVerify || null,
      },
    };
  }

  async function persist({ verifiedSnapshot = true } = {}) {
    const record = await serializedState();
    await writeRecord(CURRENT_KEY, record);
    if (verifiedSnapshot) await writeRecord(SNAPSHOT_KEY, record);
  }

  async function issueReceipt(type, note, subjectDigest) {
    const body = {
      schema: "szl.alloy-local-receipt/v1",
      seq: state.receipts.length,
      type,
      note,
      subjectDigest,
      prevDigest: state.receipts.at(-1)?.digest || "GENESIS",
      issuedAt: new Date().toISOString(),
      keyId: state.identity.kid,
    };
    const payload = canonical(body);
    const signature = await crypto.subtle.sign(
      { name: "ECDSA", hash: "SHA-256" },
      signingKeys.privateKey,
      bytes(payload),
    );
    const receipt = {
      ...body,
      digest: await sha256(payload),
      signature: base64url(signature),
    };
    state.receipts.push(receipt);
    return receipt;
  }

  async function verifyReceipts() {
    let previous = "GENESIS";
    for (let index = 0; index < state.receipts.length; index += 1) {
      const receipt = state.receipts[index];
      const body = {
        schema: receipt.schema,
        seq: receipt.seq,
        type: receipt.type,
        note: receipt.note,
        subjectDigest: receipt.subjectDigest,
        prevDigest: receipt.prevDigest,
        issuedAt: receipt.issuedAt,
        keyId: receipt.keyId,
      };
      const payload = canonical(body);
      if (receipt.seq !== index || receipt.prevDigest !== previous) return false;
      if ((await sha256(payload)) !== receipt.digest) return false;
      const valid = await crypto.subtle.verify(
        { name: "ECDSA", hash: "SHA-256" },
        signingKeys.publicKey,
        fromBase64url(receipt.signature),
        bytes(payload),
      );
      if (!valid) return false;
      previous = receipt.digest;
    }
    return true;
  }

  async function verifyCapsules() {
    for (const capsule of state.capsules) {
      if (capsule.status !== "SEALED" || capsule.adapter !== ADAPTER_CURRENT) return false;
      let plaintext;
      try {
        plaintext = await crypto.subtle.decrypt(
          {
            name: "AES-GCM",
            iv: fromBase64url(capsule.iv),
            additionalData: bytes(capsule.adapter),
            tagLength: 128,
          },
          encryptionKey,
          fromBase64url(capsule.ciphertext),
        );
      } catch (_error) {
        return false;
      }
      let payload;
      try {
        payload = JSON.parse(decoder.decode(plaintext));
      } catch (_error) {
        return false;
      }
      if (canonical(payload) !== decoder.decode(plaintext)) return false;
      if ((await sha256(canonical(payload))) !== capsule.digest) return false;
      if (payload.adapter !== capsule.adapter || payload.title !== capsule.title) return false;
    }
    return true;
  }

  async function verifyState() {
    try {
      const receiptsValid = await verifyReceipts();
      const capsulesValid = await verifyCapsules();
      state.health.ledgerReplayable = receiptsValid && capsulesValid;
      state.health.lastVerify = new Date().toISOString();
      return state.health.ledgerReplayable;
    } catch (_error) {
      state.health.ledgerReplayable = false;
      state.health.lastVerify = new Date().toISOString();
      return false;
    }
  }

  async function resetKernel(reason) {
    state = freshState();
    state.epoch = 1;
    await generateKeys();
    state.status = "READY";
    await issueReceipt("BOOT", reason, await sha256(state.identity.kid));
    await verifyState();
    await persist({ verifiedSnapshot: true });
  }

  async function restoreVerifiedSnapshot(reason) {
    const backup = await readRecord(SNAPSHOT_KEY);
    if (!backup) return false;
    try {
      await hydrate(backup);
      if (!(await verifyState())) return false;
      state.health.healed += 1;
      state.status = "HEALED";
      const subject = state.capsules.at(-1)?.digest || state.receipts.at(-1)?.digest || "STATE";
      await issueReceipt("HEAL", reason, subject);
      await verifyState();
      await persist({ verifiedSnapshot: true });
      return true;
    } catch (_error) {
      return false;
    }
  }

  async function boot() {
    if (bootPromise) return bootPromise;
    bootPromise = (async () => {
      if (!globalThis.crypto?.subtle || !globalThis.indexedDB) {
        state.status = "UNAVAILABLE";
        state.health.ledgerReplayable = false;
        notify();
        throw new Error("WebCrypto or IndexedDB unavailable");
      }
      const current = await readRecord(CURRENT_KEY);
      if (!current) {
        await resetKernel("new origin-local kernel");
      } else {
        try {
          await hydrate(current);
          if (!(await verifyState())) {
            const restored = await restoreVerifiedSnapshot("boot detected invalid current state");
            if (!restored) await resetKernel("invalid local state reset");
          } else {
            state.status = "READY";
            await persist({ verifiedSnapshot: true });
          }
        } catch (_error) {
          const restored = await restoreVerifiedSnapshot("boot could not hydrate current state");
          if (!restored) await resetKernel("unreadable local state reset");
        }
      }
      notify();
      return snapshot();
    })();
    return bootPromise;
  }

  async function deny(reason, request) {
    const subjectDigest = await sha256(canonical(request));
    state.health.blocked += 1;
    const receipt = await issueReceipt("DENY", reason, subjectDigest);
    state.status = "READY";
    await verifyState();
    await persist({ verifiedSnapshot: true });
    notify();
    return { decision: "DENY", reason, receipt };
  }

  async function govern(request = {}) {
    await boot();
    const title = String(request.title || "").trim().slice(0, 160);
    const body = String(request.body || "").slice(0, 32768);
    const policyClass = String(request.policyClass || "private").slice(0, 64);
    const adapter = String(request.adapter || "");
    const normalizedRequest = { title, body, policyClass, adapter };

    if (adapter !== ADAPTER_CURRENT) {
      return deny(`adapter hard-block: expected ${ADAPTER_CURRENT}`, normalizedRequest);
    }
    if (!title || !body) return deny("title and payload are required", normalizedRequest);

    const payload = {
      schema: "szl.alloy-local-capsule/v1",
      title,
      body,
      policyClass,
      adapter,
      createdAt: new Date().toISOString(),
    };
    const plaintext = canonical(payload);
    const digest = await sha256(plaintext);
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const ciphertext = await crypto.subtle.encrypt(
      {
        name: "AES-GCM",
        iv,
        additionalData: bytes(adapter),
        tagLength: 128,
      },
      encryptionKey,
      bytes(plaintext),
    );
    const capsule = {
      schema: payload.schema,
      id: digest,
      title,
      adapter,
      policyClass,
      createdAt: payload.createdAt,
      digest,
      iv: base64url(iv),
      ciphertext: base64url(ciphertext),
      status: "SEALED",
    };
    state.capsules.push(capsule);
    const receipt = await issueReceipt("ALLOW", "capsule sealed on this origin", digest);
    state.status = "READY";
    if (!(await verifyState())) throw new Error("post-write verification failed");
    await persist({ verifiedSnapshot: true });
    notify();
    return { decision: "ALLOW", reason: "verified adapter; capsule sealed", receipt, capsule: clone(capsule) };
  }

  async function injectFault() {
    await boot();
    const capsule = state.capsules.at(-1);
    if (!capsule) return "No capsule exists to tamper.";
    const corrupted = fromBase64url(capsule.ciphertext);
    if (!corrupted.length) return "Capsule ciphertext is empty; no fault injected.";
    corrupted[0] ^= 0x01;
    capsule.ciphertext = base64url(corrupted);
    capsule.status = "TAMPERED";
    state.status = "DEGRADED";
    state.health.ledgerReplayable = false;
    await persist({ verifiedSnapshot: false });
    notify();
    return "One ciphertext byte changed. Current state is degraded; the last verified snapshot is intact.";
  }

  async function runWatchdog() {
    await boot();
    if (await verifyState()) {
      state.status = "READY";
      await persist({ verifiedSnapshot: true });
      notify();
      return { healed: false, reason: "current state verified" };
    }
    const restored = await restoreVerifiedSnapshot("watchdog restored last verified snapshot");
    if (!restored) {
      await resetKernel("watchdog could not restore snapshot");
      state.status = "RESET";
    }
    notify();
    return { healed: restored, reason: restored ? "restored last verified snapshot" : "reset after unrecoverable state" };
  }

  function subscribe(listener) {
    if (typeof listener !== "function") return () => {};
    listeners.add(listener);
    return () => listeners.delete(listener);
  }

  globalThis.Alloy = Object.freeze({
    ADAPTER_CURRENT,
    get status() { return state.status; },
    get epoch() { return state.epoch; },
    get identity() { return state.identity; },
    get receipts() { return state.receipts; },
    get capsules() { return state.capsules; },
    get health() { return state.health; },
    boot,
    govern,
    injectFault,
    runWatchdog,
    subscribe,
    shortHex,
    snapshot,
  });
})();
