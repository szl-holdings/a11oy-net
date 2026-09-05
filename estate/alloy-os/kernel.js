"use strict";

(() => {
  const DB_NAME = "a11oy-proof-local-kernel";
  const DB_VERSION = 1;
  const STORE = "kernel";
  const STATE_ID = "primary";
  const SCHEMA = "szl.alloy-local-kernel/v1";
  const SNAPSHOT_SCHEMA = "szl.alloy-local-snapshot/v1";
  const ADAPTER_CURRENT = "alloy-local-v1";
  const GENESIS = "sha256:" + "0".repeat(64);
  const MAX_TITLE_BYTES = 512;
  const MAX_BODY_BYTES = 65536;
  const encoder = new TextEncoder();
  const decoder = new TextDecoder("utf-8", { fatal: true });

  let db = null;
  let state = null;
  let ready = null;
  const listeners = new Set();

  const clone = (value) =>
    typeof structuredClone === "function"
      ? structuredClone(value)
      : JSON.parse(JSON.stringify(value));

  function notify() {
    for (const listener of listeners) {
      try {
        listener();
      } catch (_) {
        // A view listener cannot change kernel state.
      }
    }
  }

  function stable(value) {
    if (Array.isArray(value)) {
      return `[${value.map(stable).join(",")}]`;
    }
    if (value && typeof value === "object") {
      const keys = Object.keys(value).sort();
      return `{${keys.map((key) => `${JSON.stringify(key)}:${stable(value[key])}`).join(",")}}`;
    }
    return JSON.stringify(value);
  }

  function toBase64(bytes) {
    const view = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
    let binary = "";
    for (let offset = 0; offset < view.length; offset += 0x8000) {
      binary += String.fromCharCode(...view.subarray(offset, offset + 0x8000));
    }
    return btoa(binary);
  }

  function fromBase64(text) {
    const binary = atob(text);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) {
      bytes[index] = binary.charCodeAt(index);
    }
    return bytes;
  }

  function hex(bytes) {
    return [...new Uint8Array(bytes)]
      .map((value) => value.toString(16).padStart(2, "0"))
      .join("");
  }

  async function sha256Bytes(bytes) {
    return crypto.subtle.digest("SHA-256", bytes);
  }

  async function digestObject(value) {
    return `sha256:${hex(await sha256Bytes(encoder.encode(stable(value))))}`;
  }

  function now() {
    return new Date().toISOString();
  }

  function openDatabase() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);
      request.onupgradeneeded = () => {
        const database = request.result;
        if (!database.objectStoreNames.contains(STORE)) {
          database.createObjectStore(STORE, { keyPath: "id" });
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error || new Error("IndexedDB open failed"));
      request.onblocked = () => reject(new Error("IndexedDB upgrade blocked"));
    });
  }

  function readRecord() {
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(STORE, "readonly");
      const request = transaction.objectStore(STORE).get(STATE_ID);
      request.onsuccess = () => resolve(request.result || null);
      request.onerror = () => reject(request.error || new Error("IndexedDB read failed"));
    });
  }

  function writeRecord(record) {
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(STORE, "readwrite");
      transaction.oncomplete = () => resolve();
      transaction.onerror = () =>
        reject(transaction.error || new Error("IndexedDB write failed"));
      transaction.onabort = () =>
        reject(transaction.error || new Error("IndexedDB write aborted"));
      transaction.objectStore(STORE).put(record);
    });
  }

  async function createIdentity() {
    const signing = await crypto.subtle.generateKey(
      { name: "ECDSA", namedCurve: "P-256" },
      false,
      ["sign", "verify"],
    );
    const encryption = await crypto.subtle.generateKey(
      { name: "AES-GCM", length: 256 },
      false,
      ["encrypt", "decrypt"],
    );
    const publicSpki = await crypto.subtle.exportKey("spki", signing.publicKey);
    const kid = `p256-${hex(await sha256Bytes(publicSpki)).slice(0, 24)}`;
    return {
      kid,
      signing_private: signing.privateKey,
      signing_public: signing.publicKey,
      encryption,
    };
  }

  function snapshotBody() {
    return {
      schema: SNAPSHOT_SCHEMA,
      epoch: state.epoch,
      receipts: clone(state.receipts),
      capsules: clone(state.capsules),
      captured_at: now(),
    };
  }

  async function sealSnapshot() {
    const body = snapshotBody();
    state.last_good = {
      ...body,
      digest: await digestObject(body),
    };
  }

  async function persist({ refreshSnapshot = false } = {}) {
    if (refreshSnapshot) {
      await sealSnapshot();
    }
    state.updated_at = now();
    await writeRecord(state);
  }

  function receiptUnsigned(receipt) {
    return {
      schema: receipt.schema,
      seq: receipt.seq,
      type: receipt.type,
      note: receipt.note,
      ts: receipt.ts,
      prev_digest: receipt.prev_digest,
      payload_digest: receipt.payload_digest,
      adapter: receipt.adapter,
      policy_class: receipt.policy_class,
      decision: receipt.decision,
    };
  }

  async function signReceipt({ type, note, payload, adapter, policyClass, decision }) {
    const receipt = {
      schema: "szl.alloy-local-receipt/v1",
      seq: state.receipts.length,
      type,
      note,
      ts: now(),
      prev_digest:
        state.receipts.length > 0
          ? state.receipts[state.receipts.length - 1].digest
          : GENESIS,
      payload_digest: await digestObject(payload),
      adapter,
      policy_class: policyClass,
      decision,
    };
    const unsigned = receiptUnsigned(receipt);
    receipt.digest = await digestObject(unsigned);
    const signature = await crypto.subtle.sign(
      { name: "ECDSA", hash: "SHA-256" },
      state.identity.signing_private,
      encoder.encode(stable(unsigned)),
    );
    receipt.signature = {
      algorithm: "ECDSA-P256-SHA256",
      value: toBase64(signature),
      kid: state.identity.kid,
    };
    return receipt;
  }

  async function verifyReceipt(receipt, index, previousDigest) {
    if (!receipt || typeof receipt !== "object") return false;
    if (receipt.schema !== "szl.alloy-local-receipt/v1") return false;
    if (receipt.seq !== index || receipt.prev_digest !== previousDigest) return false;
    if (
      !receipt.signature ||
      receipt.signature.algorithm !== "ECDSA-P256-SHA256" ||
      receipt.signature.kid !== state.identity.kid
    ) {
      return false;
    }
    const unsigned = receiptUnsigned(receipt);
    if ((await digestObject(unsigned)) !== receipt.digest) return false;
    try {
      return await crypto.subtle.verify(
        { name: "ECDSA", hash: "SHA-256" },
        state.identity.signing_public,
        fromBase64(receipt.signature.value),
        encoder.encode(stable(unsigned)),
      );
    } catch (_) {
      return false;
    }
  }

  async function verifyLedger(receipts = state.receipts) {
    let previous = GENESIS;
    for (let index = 0; index < receipts.length; index += 1) {
      if (!(await verifyReceipt(receipts[index], index, previous))) {
        return false;
      }
      previous = receipts[index].digest;
    }
    return true;
  }

  function capsuleHeader(capsule) {
    return {
      schema: capsule.schema,
      id: capsule.id,
      digest: capsule.digest,
      title: capsule.title,
      adapter: capsule.adapter,
      policy_class: capsule.policy_class,
      algorithm: capsule.algorithm,
      created_at: capsule.created_at,
    };
  }

  async function verifyCapsule(capsule) {
    if (!capsule || capsule.schema !== "szl.alloy-local-capsule/v1") return false;
    if (capsule.algorithm !== "AES-256-GCM") return false;
    try {
      const plaintext = await crypto.subtle.decrypt(
        {
          name: "AES-GCM",
          iv: fromBase64(capsule.iv),
          additionalData: encoder.encode(stable(capsuleHeader(capsule))),
          tagLength: 128,
        },
        state.identity.encryption,
        fromBase64(capsule.ciphertext),
      );
      const payload = JSON.parse(decoder.decode(plaintext));
      return (
        payload.title === capsule.title &&
        payload.adapter === capsule.adapter &&
        payload.policy_class === capsule.policy_class &&
        (await digestObject(payload)) === capsule.digest
      );
    } catch (_) {
      return false;
    }
  }

  async function verifyAll() {
    if (!(await verifyLedger())) {
      return { ok: false, reason: "LEDGER_VERIFICATION_FAILED" };
    }
    for (const capsule of state.capsules) {
      if (!(await verifyCapsule(capsule))) {
        return { ok: false, reason: `CAPSULE_VERIFICATION_FAILED:${capsule.id}` };
      }
    }
    return { ok: true, reason: "VERIFIED" };
  }

  async function makeCapsule({ title, body, policyClass, adapter }) {
    const payload = {
      schema: "szl.alloy-local-payload/v1",
      title,
      body,
      adapter,
      policy_class: policyClass,
      created_at: now(),
    };
    const digest = await digestObject(payload);
    const capsule = {
      schema: "szl.alloy-local-capsule/v1",
      id: digest,
      digest,
      title,
      adapter,
      policy_class: policyClass,
      algorithm: "AES-256-GCM",
      created_at: payload.created_at,
      status: "SEALED",
    };
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const ciphertext = await crypto.subtle.encrypt(
      {
        name: "AES-GCM",
        iv,
        additionalData: encoder.encode(stable(capsuleHeader(capsule))),
        tagLength: 128,
      },
      state.identity.encryption,
      encoder.encode(stable(payload)),
    );
    capsule.iv = toBase64(iv);
    capsule.ciphertext = toBase64(ciphertext);
    return capsule;
  }

  async function block(reason, input) {
    state.health.blocked += 1;
    const receipt = await signReceipt({
      type: "POLICY_BLOCK",
      note: reason,
      payload: {
        reason,
        title_digest: await digestObject({ title: input.title || "" }),
      },
      adapter: input.adapter || "UNAVAILABLE",
      policyClass: input.policyClass || "UNAVAILABLE",
      decision: "BLOCK",
    });
    state.receipts.push(receipt);
    state.health.ledgerReplayable = await verifyLedger();
    state.health.lastVerify = now();
    await persist({ refreshSnapshot: true });
    notify();
    return { decision: "BLOCK", reason, receipt };
  }

  async function govern(input = {}) {
    await boot();
    const title = String(input.title || "").trim();
    const body = String(input.body || "");
    const adapter = String(input.adapter || "");
    const policyClass = String(input.policyClass || "");

    if (adapter !== ADAPTER_CURRENT) {
      return block("ADAPTER_NOT_PINNED", { title, adapter, policyClass });
    }
    if (policyClass !== "private") {
      return block("POLICY_CLASS_NOT_LOCAL_PRIVATE", {
        title,
        adapter,
        policyClass,
      });
    }
    if (!title || encoder.encode(title).length > MAX_TITLE_BYTES) {
      return block("TITLE_INVALID_OR_OVERSIZE", { title, adapter, policyClass });
    }
    if (!body || encoder.encode(body).length > MAX_BODY_BYTES) {
      return block("PAYLOAD_INVALID_OR_OVERSIZE", { title, adapter, policyClass });
    }

    const capsule = await makeCapsule({ title, body, policyClass, adapter });
    const receipt = await signReceipt({
      type: "CAPSULE_SEALED",
      note: "Encrypted locally; no network or product authority.",
      payload: {
        capsule_digest: capsule.digest,
        algorithm: capsule.algorithm,
        title_digest: await digestObject({ title }),
      },
      adapter,
      policyClass,
      decision: "ALLOW",
    });
    state.capsules.push(capsule);
    state.receipts.push(receipt);
    state.health.ledgerReplayable = await verifyLedger();
    state.health.lastVerify = now();
    state.status = "LOCAL_VERIFIED";
    await persist({ refreshSnapshot: true });
    notify();
    return { decision: "ALLOW", reason: "LOCAL_POLICY_SATISFIED", receipt };
  }

  async function restoreSnapshot(reason) {
    const snapshot = state.last_good;
    if (!snapshot || snapshot.schema !== SNAPSHOT_SCHEMA) {
      state.status = "LOCAL_DEGRADED";
      state.health.ledgerReplayable = false;
      state.health.lastVerify = now();
      await persist();
      notify();
      return false;
    }
    const body = {
      schema: snapshot.schema,
      epoch: snapshot.epoch,
      receipts: snapshot.receipts,
      capsules: snapshot.capsules,
      captured_at: snapshot.captured_at,
    };
    if ((await digestObject(body)) !== snapshot.digest) {
      state.status = "LOCAL_DEGRADED";
      state.health.ledgerReplayable = false;
      state.health.lastVerify = now();
      await persist();
      notify();
      return false;
    }

    state.receipts = clone(snapshot.receipts);
    state.capsules = clone(snapshot.capsules);
    state.epoch += 1;
    state.health.healed += 1;
    const receipt = await signReceipt({
      type: "LOCAL_SNAPSHOT_HEAL",
      note: reason,
      payload: {
        snapshot_digest: snapshot.digest,
        restored_receipts: state.receipts.length,
        restored_capsules: state.capsules.length,
      },
      adapter: ADAPTER_CURRENT,
      policyClass: "private",
      decision: "ALLOW",
    });
    state.receipts.push(receipt);
    state.health.ledgerReplayable = await verifyLedger();
    state.health.lastVerify = now();
    state.status = state.health.ledgerReplayable
      ? "LOCAL_VERIFIED"
      : "LOCAL_DEGRADED";
    await persist({ refreshSnapshot: state.health.ledgerReplayable });
    notify();
    return state.health.ledgerReplayable;
  }

  async function runWatchdog() {
    await boot();
    const verdict = await verifyAll();
    if (verdict.ok) {
      state.health.ledgerReplayable = true;
      state.health.lastVerify = now();
      state.status = "LOCAL_VERIFIED";
      await persist({ refreshSnapshot: true });
      notify();
      return verdict;
    }
    const healed = await restoreSnapshot(verdict.reason);
    return {
      ok: healed,
      reason: healed ? `HEALED:${verdict.reason}` : `UNRECOVERABLE:${verdict.reason}`,
    };
  }

  async function injectFault() {
    await boot();
    if (state.capsules.length === 0) {
      return "No capsule exists to fault; seal one first.";
    }
    const capsule = state.capsules[state.capsules.length - 1];
    const bytes = fromBase64(capsule.ciphertext);
    if (bytes.length === 0) {
      return "Fault injection refused: ciphertext is empty.";
    }
    bytes[Math.floor(bytes.length / 2)] ^= 0x01;
    capsule.ciphertext = toBase64(bytes);
    capsule.status = "TAMPERED_FOR_LOCAL_TEST";
    state.status = "LOCAL_TAMPER_OBSERVED";
    state.health.ledgerReplayable = false;
    state.health.lastVerify = now();
    await persist({ refreshSnapshot: false });
    notify();
    return "One ciphertext byte changed locally. Run the healer to restore the last verified snapshot.";
  }

  async function newState() {
    return {
      id: STATE_ID,
      schema: SCHEMA,
      epoch: 1,
      status: "LOCAL_BOOTSTRAP",
      created_at: now(),
      updated_at: now(),
      identity: await createIdentity(),
      receipts: [],
      capsules: [],
      last_good: null,
      health: {
        healed: 0,
        blocked: 0,
        ledgerReplayable: true,
        lastVerify: null,
      },
    };
  }

  async function bootImpl() {
    if (!globalThis.crypto?.subtle || !globalThis.indexedDB) {
      throw new Error("WebCrypto and IndexedDB are required");
    }
    db = await openDatabase();
    state = await readRecord();
    if (!state) {
      state = await newState();
      const receipt = await signReceipt({
        type: "LOCAL_KERNEL_GENESIS",
        note: "Non-authoritative browser-local kernel initialized.",
        payload: {
          schema: SCHEMA,
          kid: state.identity.kid,
          origin: location.origin,
        },
        adapter: ADAPTER_CURRENT,
        policyClass: "private",
        decision: "ALLOW",
      });
      state.receipts.push(receipt);
      state.health.lastVerify = now();
      state.status = "LOCAL_VERIFIED";
      await persist({ refreshSnapshot: true });
    } else {
      if (
        state.schema !== SCHEMA ||
        !state.identity?.signing_private ||
        !state.identity?.signing_public ||
        !state.identity?.encryption
      ) {
        throw new Error("Stored local-kernel state is incompatible");
      }
      const verdict = await verifyAll();
      if (!verdict.ok) {
        await restoreSnapshot(`BOOT_${verdict.reason}`);
      } else {
        state.health.ledgerReplayable = true;
        state.health.lastVerify = now();
        state.status = "LOCAL_VERIFIED";
        await persist({ refreshSnapshot: true });
      }
    }
    notify();
    return api;
  }

  function boot() {
    if (!ready) {
      ready = bootImpl().catch((error) => {
        state = state || {
          id: STATE_ID,
          schema: SCHEMA,
          epoch: 0,
          status: "LOCAL_UNAVAILABLE",
          identity: null,
          receipts: [],
          capsules: [],
          health: {
            healed: 0,
            blocked: 0,
            ledgerReplayable: false,
            lastVerify: now(),
          },
        };
        state.status = "LOCAL_UNAVAILABLE";
        notify();
        throw error;
      });
    }
    return ready;
  }

  function subscribe(listener) {
    if (typeof listener !== "function") {
      throw new TypeError("listener must be a function");
    }
    listeners.add(listener);
    return () => listeners.delete(listener);
  }

  function shortHex(value) {
    const text = String(value || "");
    return text.length > 18 ? `${text.slice(0, 14)}…${text.slice(-4)}` : text;
  }

  const api = {
    ADAPTER_CURRENT,
    boot,
    govern,
    injectFault,
    runWatchdog,
    subscribe,
    shortHex,
    get status() {
      return state?.status || "LOCAL_NOT_BOOTED";
    },
    get identity() {
      return state?.identity ? { kid: state.identity.kid } : null;
    },
    get epoch() {
      return state?.epoch || 0;
    },
    get receipts() {
      return state?.receipts || [];
    },
    get capsules() {
      return state?.capsules || [];
    },
    get health() {
      return (
        state?.health || {
          healed: 0,
          blocked: 0,
          ledgerReplayable: false,
          lastVerify: null,
        }
      );
    },
  };

  Object.freeze(api);
  Object.defineProperty(globalThis, "Alloy", {
    value: api,
    writable: false,
    configurable: false,
    enumerable: true,
  });
})();
