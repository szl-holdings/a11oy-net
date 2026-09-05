/* SPDX-License-Identifier: Apache-2.0
 * Alloy local kernel: browser-only encrypted capsules and signed receipt chain.
 * No network calls. No product authority. Keys remain scoped to this origin.
 */
(() => {
  "use strict";

  const DB_NAME = "a11oy-alloy-local-kernel-v1";
  const DB_VERSION = 1;
  const ADAPTER_CURRENT = "alloy-local-v1";
  const enc = new TextEncoder();
  const dec = new TextDecoder();
  const listeners = new Set();
  let db = null;
  let keys = null;

  const Alloy = {
    ADAPTER_CURRENT,
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
    subscribe(callback) {
      if (typeof callback === "function") listeners.add(callback);
      return () => listeners.delete(callback);
    },
    shortHex(value) {
      const text = String(value || "UNAVAILABLE");
      return text.length > 16 ? `${text.slice(0, 8)}…${text.slice(-6)}` : text;
    },
    boot,
    govern,
    injectFault,
    runWatchdog,
  };
  window.Alloy = Alloy;

  function emit() {
    for (const callback of listeners) {
      try { callback(Alloy); } catch (_) { /* UI subscribers cannot alter kernel state. */ }
    }
  }

  function canonical(value) {
    if (value === null || typeof value !== "object") return JSON.stringify(value);
    if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
    return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(",")}}`;
  }

  function toBase64(bytes) {
    let binary = "";
    const view = new Uint8Array(bytes);
    for (let offset = 0; offset < view.length; offset += 0x8000) {
      binary += String.fromCharCode(...view.subarray(offset, offset + 0x8000));
    }
    return btoa(binary);
  }

  function fromBase64(value) {
    const binary = atob(value);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
    return bytes;
  }

  function hex(bytes) {
    return [...new Uint8Array(bytes)].map(value => value.toString(16).padStart(2, "0")).join("");
  }

  async function sha256(value) {
    const bytes = value instanceof Uint8Array ? value : enc.encode(String(value));
    return hex(await crypto.subtle.digest("SHA-256", bytes));
  }

  function requestResult(request) {
    return new Promise((resolve, reject) => {
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error || new Error("IndexedDB request failed"));
    });
  }

  function transactionDone(transaction) {
    return new Promise((resolve, reject) => {
      transaction.oncomplete = () => resolve();
      transaction.onerror = () => reject(transaction.error || new Error("IndexedDB transaction failed"));
      transaction.onabort = () => reject(transaction.error || new Error("IndexedDB transaction aborted"));
    });
  }

  function openDatabase() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);
      request.onupgradeneeded = () => {
        const database = request.result;
        if (!database.objectStoreNames.contains("meta")) database.createObjectStore("meta", { keyPath: "key" });
        if (!database.objectStoreNames.contains("capsules")) database.createObjectStore("capsules", { keyPath: "id" });
        if (!database.objectStoreNames.contains("receipts")) database.createObjectStore("receipts", { keyPath: "seq" });
        if (!database.objectStoreNames.contains("snapshots")) {
          const store = database.createObjectStore("snapshots", { keyPath: "id" });
          store.createIndex("capsuleId", "capsuleId", { unique: false });
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error || new Error("IndexedDB open failed"));
      request.onblocked = () => reject(new Error("IndexedDB upgrade blocked"));
    });
  }

  async function get(store, key) {
    const transaction = db.transaction(store, "readonly");
    const result = await requestResult(transaction.objectStore(store).get(key));
    await transactionDone(transaction);
    return result;
  }

  async function all(store) {
    const transaction = db.transaction(store, "readonly");
    const result = await requestResult(transaction.objectStore(store).getAll());
    await transactionDone(transaction);
    return result;
  }

  async function put(store, value) {
    const transaction = db.transaction(store, "readwrite");
    transaction.objectStore(store).put(value);
    await transactionDone(transaction);
  }

  async function createKeys() {
    const encryptionKey = await crypto.subtle.generateKey(
      { name: "AES-GCM", length: 256 },
      false,
      ["encrypt", "decrypt"],
    );
    const generated = await crypto.subtle.generateKey(
      { name: "ECDSA", namedCurve: "P-256" },
      true,
      ["sign", "verify"],
    );
    const publicJwk = await crypto.subtle.exportKey("jwk", generated.publicKey);
    const privateJwk = await crypto.subtle.exportKey("jwk", generated.privateKey);
    const signPublicKey = await crypto.subtle.importKey(
      "jwk",
      publicJwk,
      { name: "ECDSA", namedCurve: "P-256" },
      true,
      ["verify"],
    );
    const signPrivateKey = await crypto.subtle.importKey(
      "jwk",
      privateJwk,
      { name: "ECDSA", namedCurve: "P-256" },
      false,
      ["sign"],
    );
    return {
      encryptionKey,
      signPublicKey,
      signPrivateKey,
      publicJwk,
      kid: await sha256(canonical(publicJwk)),
    };
  }

  async function ensureKeys() {
    const stored = await get("meta", "keys");
    if (stored?.value?.encryptionKey && stored?.value?.signPrivateKey && stored?.value?.signPublicKey) {
      return stored.value;
    }
    const created = await createKeys();
    await put("meta", { key: "keys", value: created });
    return created;
  }

  async function addReceipt(type, note, payload = {}) {
    const seq = Alloy.receipts.length ? Alloy.receipts[Alloy.receipts.length - 1].seq + 1 : 1;
    const previous = Alloy.receipts.length ? Alloy.receipts[Alloy.receipts.length - 1].digest : "0".repeat(64);
    const core = {
      seq,
      type,
      note,
      createdAt: new Date().toISOString(),
      prevDigest: previous,
      payloadDigest: await sha256(canonical(payload)),
      kid: keys.kid,
    };
    const digest = await sha256(canonical(core));
    const signature = toBase64(await crypto.subtle.sign(
      { name: "ECDSA", hash: "SHA-256" },
      keys.signPrivateKey,
      enc.encode(digest),
    ));
    const receipt = { ...core, digest, signature };
    await put("receipts", receipt);
    Alloy.receipts.push(receipt);
    return receipt;
  }

  async function verifyReceiptChain() {
    let previous = "0".repeat(64);
    for (let index = 0; index < Alloy.receipts.length; index += 1) {
      const receipt = Alloy.receipts[index];
      if (receipt.seq !== index + 1 || receipt.prevDigest !== previous || receipt.kid !== keys.kid) return false;
      const { digest, signature, ...core } = receipt;
      if (await sha256(canonical(core)) !== digest) return false;
      const valid = await crypto.subtle.verify(
        { name: "ECDSA", hash: "SHA-256" },
        keys.signPublicKey,
        fromBase64(signature),
        enc.encode(digest),
      );
      if (!valid) return false;
      previous = digest;
    }
    return true;
  }

  async function verifyCapsule(capsule) {
    try {
      const plaintext = await crypto.subtle.decrypt(
        {
          name: "AES-GCM",
          iv: fromBase64(capsule.iv),
          additionalData: enc.encode(capsule.digest),
        },
        keys.encryptionKey,
        fromBase64(capsule.ciphertext),
      );
      const decoded = dec.decode(plaintext);
      return (await sha256(decoded)) === capsule.digest;
    } catch (_) {
      return false;
    }
  }

  async function verifyAll() {
    const capsulesValid = (await Promise.all(Alloy.capsules.map(verifyCapsule))).every(Boolean);
    Alloy.health.ledgerReplayable = capsulesValid && await verifyReceiptChain();
    Alloy.health.lastVerify = new Date().toISOString();
    return Alloy.health.ledgerReplayable;
  }

  async function boot() {
    if (!globalThis.crypto?.subtle || !globalThis.indexedDB) {
      Alloy.status = "UNAVAILABLE";
      Alloy.health.blocked += 1;
      emit();
      throw new Error("WebCrypto or IndexedDB unavailable");
    }
    try {
      db = await openDatabase();
      keys = await ensureKeys();
      const epochRow = await get("meta", "epoch");
      Alloy.epoch = Number(epochRow?.value || 0) + 1;
      await put("meta", { key: "epoch", value: Alloy.epoch });
      Alloy.identity = { kid: keys.kid, algorithm: "ECDSA-P256-SHA256", origin: location.origin };
      Alloy.receipts = (await all("receipts")).sort((a, b) => a.seq - b.seq);
      Alloy.capsules = (await all("capsules")).sort((a, b) => String(a.createdAt).localeCompare(String(b.createdAt)));
      if (!Alloy.receipts.length) await addReceipt("BOOT", "Local kernel initialized", { epoch: Alloy.epoch });
      await verifyAll();
      Alloy.status = Alloy.health.ledgerReplayable ? "READY" : "DEGRADED";
    } catch (error) {
      Alloy.status = "UNAVAILABLE";
      Alloy.health.blocked += 1;
      emit();
      throw error;
    }
    emit();
    return Alloy;
  }

  async function govern({ title, body, policyClass = "private", adapter = ADAPTER_CURRENT } = {}) {
    if (!keys || Alloy.status === "BOOTING") throw new Error("kernel not booted");
    const normalizedTitle = String(title || "Untitled").trim().slice(0, 160);
    const normalizedBody = String(body || "").trim();
    if (adapter !== ADAPTER_CURRENT) {
      Alloy.health.blocked += 1;
      const receipt = await addReceipt("BLOCK", "Adapter pin mismatch", { adapter, expected: ADAPTER_CURRENT });
      emit();
      return { decision: "BLOCK", reason: `adapter must equal ${ADAPTER_CURRENT}`, receipt };
    }
    if (policyClass !== "private" || !normalizedBody) {
      Alloy.health.blocked += 1;
      const receipt = await addReceipt("BLOCK", "Local policy rejected envelope", {
        policyClass,
        bodyPresent: Boolean(normalizedBody),
      });
      emit();
      return { decision: "BLOCK", reason: "private non-empty envelopes only", receipt };
    }

    const plaintext = canonical({
      adapter,
      body: normalizedBody,
      policyClass,
      title: normalizedTitle,
    });
    const digest = await sha256(plaintext);
    const existing = Alloy.capsules.find(capsule => capsule.digest === digest && capsule.status === "SEALED");
    if (existing) {
      const receipt = await addReceipt("REUSE", "Content-addressed capsule reused", { capsuleId: existing.id });
      await verifyAll();
      emit();
      return { decision: "ALLOW", reason: "existing encrypted capsule reused", capsule: existing, receipt };
    }

    const iv = crypto.getRandomValues(new Uint8Array(12));
    const ciphertext = await crypto.subtle.encrypt(
      { name: "AES-GCM", iv, additionalData: enc.encode(digest) },
      keys.encryptionKey,
      enc.encode(plaintext),
    );
    const capsule = {
      id: digest,
      title: normalizedTitle,
      digest,
      iv: toBase64(iv),
      ciphertext: toBase64(ciphertext),
      adapter,
      policyClass,
      createdAt: new Date().toISOString(),
      status: "SEALED",
    };
    await put("capsules", capsule);
    Alloy.capsules.push(capsule);
    const receipt = await addReceipt("SEAL", "AES-256-GCM capsule committed", { capsuleId: capsule.id });
    await verifyAll();
    Alloy.status = Alloy.health.ledgerReplayable ? "READY" : "DEGRADED";
    emit();
    return { decision: "ALLOW", reason: "encrypted capsule committed locally", capsule, receipt };
  }

  async function injectFault() {
    const capsule = [...Alloy.capsules].reverse().find(item => item.status === "SEALED");
    if (!capsule) return "No sealed capsule is available for the one-byte fault probe.";
    const snapshot = {
      id: `${capsule.id}:${Date.now()}`,
      capsuleId: capsule.id,
      createdAt: new Date().toISOString(),
      capsule: structuredClone(capsule),
    };
    await put("snapshots", snapshot);
    const bytes = fromBase64(capsule.ciphertext);
    bytes[0] ^= 1;
    capsule.ciphertext = toBase64(bytes);
    capsule.status = "TAMPERED";
    await put("capsules", capsule);
    Alloy.health.blocked += 1;
    await addReceipt("FAULT", "One-byte ciphertext fault injected and detected", { capsuleId: capsule.id });
    await verifyAll();
    Alloy.status = "DEGRADED";
    emit();
    return `One-byte tamper detected for ${Alloy.shortHex(capsule.id)}.`;
  }

  async function latestSnapshot(capsuleId) {
    const rows = (await all("snapshots")).filter(row => row.capsuleId === capsuleId);
    rows.sort((a, b) => String(b.createdAt).localeCompare(String(a.createdAt)));
    return rows[0] || null;
  }

  async function runWatchdog() {
    for (let index = 0; index < Alloy.capsules.length; index += 1) {
      const capsule = Alloy.capsules[index];
      if (await verifyCapsule(capsule)) continue;
      const snapshot = await latestSnapshot(capsule.id);
      if (!snapshot || !(await verifyCapsule(snapshot.capsule))) {
        Alloy.health.blocked += 1;
        await addReceipt("BLOCK", "Tampered capsule has no valid local snapshot", { capsuleId: capsule.id });
        continue;
      }
      const restored = { ...snapshot.capsule, status: "SEALED", healedAt: new Date().toISOString() };
      await put("capsules", restored);
      Alloy.capsules[index] = restored;
      Alloy.health.healed += 1;
      await addReceipt("HEAL", "Encrypted capsule restored from IndexedDB snapshot", { capsuleId: restored.id });
    }
    await verifyAll();
    Alloy.status = Alloy.health.ledgerReplayable ? "READY" : "DEGRADED";
    emit();
    return Alloy.health;
  }
})();
