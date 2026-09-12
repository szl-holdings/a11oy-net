/* SPDX-License-Identifier: Apache-2.0
 * Local-real Alloy OS desk. Remotes are observed fail-soft. Product origin is
 * not required. connect-src 'self' — do not fetch a-11-oy.com from this page.
 */
(() => {
  "use strict";

  const APPS = [
    { id: "command", key: "1", title: "Command" },
    { id: "mesh", key: "2", title: "Mesh" },
    { id: "ledger", key: "3", title: "Ledger" },
    { id: "capsules", key: "4", title: "Capsules" },
    { id: "energy", key: "5", title: "Energy" },
    { id: "alignment", key: "6", title: "Alignment" },
    { id: "kernel", key: "7", title: "Kernel" },
    { id: "honesty", key: "8", title: "Honesty" },
  ];

  const state = {
    title: "Genesis capsule",
    body: "Local-real kernel proof. Product origin is not required.",
    adapter: "alloy-local-v1",
    policy: "private",
    message: "",
    tone: "",
    busy: false,
    proof: null,
    open: ["command", "mesh"],
    active: "command",
    palette: false,
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (character) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    })[character]);
  }

  function safeHref(value) {
    try {
      const url = new URL(String(value), window.location.href);
      return ["http:", "https:"].includes(url.protocol) ? url.href : "#";
    } catch (_) {
      return "#";
    }
  }

  async function loadJson(url) {
    const response = await fetch(url, {
      cache: "no-store",
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    });
    if (!response.ok) throw new Error(`${url} returned HTTP ${response.status}`);
    const value = await response.json();
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      throw new Error(`${url} did not return an object`);
    }
    return value;
  }

  async function bootAlignment() {
    const rail = byId("bake-rail");
    const table = byId("align-table");
    if (!rail || !table) return;

    let snapshot;
    try {
      snapshot = await loadJson("./live.json");
    } catch (error) {
      rail.innerHTML = "";
      table.innerHTML = `<p class="bad" role="status">Alignment snapshot UNAVAILABLE — ${escapeHtml(error.message)}</p>`;
      return;
    }

    const inventory = snapshot.inventory || {};
    const rows = [
      ["Snapshot", snapshot.truth_label || "UNAVAILABLE", snapshot.capturedAt || "timestamp unavailable"],
      ["GitHub repositories", inventory.github_public_repositories ?? "—", "public organization inventory"],
      ["Hugging Face models", inventory.huggingface_models ?? "—", "public Hub listing"],
      ["Hugging Face datasets", inventory.huggingface_datasets ?? "—", "public Hub listing"],
      ["Hugging Face Spaces", inventory.huggingface_spaces ?? "—", "public Hub listing; reachability not inferred"],
      ["Hub collections", inventory.huggingface_collections ?? "—", "public collection inventory"],
    ];

    rail.innerHTML = rows.map(([label, value, detail]) => (
      `<article><span>${escapeHtml(label)}</span><b>${escapeHtml(value)}</b><p>${escapeHtml(detail)}</p></article>`
    )).join("");

    const alignment = Array.isArray(snapshot.alignment) ? snapshot.alignment : [];
    if (!alignment.length) {
      table.innerHTML = '<p class="bad" role="status">No origin bindings were published in the snapshot.</p>';
      return;
    }
    table.innerHTML = `<div class="align-scroll" tabindex="0" aria-label="Origin alignment table"><table class="align"><thead><tr><th scope="col">Plane</th><th scope="col">Class</th><th scope="col">Bind</th></tr></thead><tbody>${alignment.map((row) => {
      const href = safeHref(row.url);
      return `<tr><td>${escapeHtml(row.plane)}<br><a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">${escapeHtml(row.url)}</a></td><td>${escapeHtml(row.class)}</td><td>${escapeHtml(row.note)}</td></tr>`;
    }).join("")}</tbody></table></div>`;
  }

  function kernelAvailable() {
    return typeof window.Alloy === "object" && window.Alloy !== null;
  }

  function localMesh() {
    if (!kernelAvailable()) {
      return [
        { id: "signer", plane: "local", label: "Device signer", state: "UNAVAILABLE" },
        { id: "lake", plane: "local", label: "Local lake", state: "UNAVAILABLE" },
        { id: "ledger", plane: "local", label: "Hash-chained ledger", state: "UNAVAILABLE" },
        { id: "fabric", plane: "local", label: "Capsule fabric", state: "UNAVAILABLE" },
      ];
    }
    const kernel = window.Alloy;
    const ready = kernel.status === "READY" || kernel.health.ledgerReplayable;
    return [
      { id: "signer", plane: "local", label: "Device signer", state: kernel.identity?.kid ? "MEASURED" : "UNAVAILABLE" },
      { id: "lake", plane: "local", label: "Local lake", state: ready ? "MEASURED" : "PARTIAL" },
      { id: "ledger", plane: "local", label: "Hash-chained ledger", state: kernel.health.ledgerReplayable ? "MEASURED" : "PARTIAL" },
      { id: "fabric", plane: "local", label: "Capsule fabric", state: ready ? "MEASURED" : "PARTIAL" },
    ];
  }

  function remoteMesh() {
    return [
      { id: "product-signer", plane: "remote", label: "Product signer", state: "UNAVAILABLE", note: "Observed fail-soft. connect-src 'self' does not fetch a-11-oy.com." },
      { id: "rapl", plane: "remote", label: "RAPL joules", state: "UNAVAILABLE", note: "Energy here is a MODELED 15 W CPU-time proxy, not RAPL/NVML." },
      { id: "www", plane: "remote", label: "www identity", state: "UNAVAILABLE", note: "Owner-metal. This desk does not mutate Cloudflare." },
      { id: "lake-remote", plane: "remote", label: "Product lake", state: "UNAVAILABLE", note: "Receipts stay on the product origin. This kernel does not clone them." },
    ];
  }

  function openApp(id) {
    if (!APPS.some((app) => app.id === id)) return;
    if (!state.open.includes(id)) state.open.push(id);
    state.active = id;
    state.palette = false;
    renderDesk();
  }

  function closeApp(id) {
    if (state.open.length <= 1) {
      state.message = "Last window cannot be closed empty.";
      state.tone = "warn";
      renderDesk();
      return;
    }
    state.open = state.open.filter((item) => item !== id);
    if (state.active === id) state.active = state.open[0];
    renderDesk();
  }

  function appBody(id) {
    const kernel = kernelAvailable() ? window.Alloy : null;
    if (id === "command") {
      const stages = (kernel?.stages || []).map((stage) => (
        `<li class="${stage.fired ? "ok" : ""}">${escapeHtml(stage.name)}${stage.fired ? " · fired" : ""}</li>`
      )).join("");
      const proof = state.proof;
      const proofLines = proof ? [
        `commit ${proof.commit?.decision || "—"}`,
        `reuse ${proof.reuse?.decision || "—"}`,
        `adapter ${proof.blocked?.decision || "—"}`,
        `tamper ${proof.tamper ? "FAULT_TEST" : "—"}`,
        `heal restored ${proof.heal?.restored ?? "—"}`,
      ].map((line) => `<li>${escapeHtml(line)}</li>`).join("") : "<li>No local proof yet.</li>";
      return `<p class="eyebrow">${escapeHtml(kernel?.status || "UNAVAILABLE")} · kid ${escapeHtml(kernel?.identity?.kid || "booting")}</p>
        <p>This desk is the live fabric. Product origin can be down.</p>
        <button type="button" class="button primary" id="kproof"${state.busy ? " disabled" : ""}>Run local proof</button>
        <ol class="klog stages">${stages || "<li>Stages idle.</li>"}</ol>
        <p class="eyebrow">Five-step check</p>
        <ol class="klog">${proofLines}</ol>
        <p class="${escapeHtml(state.tone)}" role="status">${escapeHtml(state.message)}</p>`;
    }
    if (id === "mesh") {
      const rows = [...localMesh(), ...remoteMesh()].map((row) => (
        `<tr><td>${escapeHtml(row.plane)}</td><td>${escapeHtml(row.label)}</td><td class="${row.state === "MEASURED" ? "ok" : row.state === "UNAVAILABLE" ? "warn" : ""}">${escapeHtml(row.state)}</td><td>${escapeHtml(row.note || (row.plane === "local" ? "This browser." : "Observed fail-soft."))}</td></tr>`
      )).join("");
      return `<p>Local gates do not wait on a-11-oy.com. Remotes are observed, never blocking.</p>
        <table class="align"><thead><tr><th>Plane</th><th>Gate</th><th>State</th><th>Note</th></tr></thead><tbody>${rows}</tbody></table>`;
    }
    if (id === "ledger") {
      const receipts = (kernel?.receipts || []).slice(-12).reverse().map((receipt) => (
        `<li>#${escapeHtml(receipt.seq)} <b>${escapeHtml(receipt.type)}</b> ${escapeHtml(receipt.note)} <span>${escapeHtml(kernel.shortHex(receipt.digest))}</span></li>`
      )).join("");
      return `<p>Replayable: ${kernel?.health.ledgerReplayable ? "MEASURED" : "degraded"} · ${escapeHtml(kernel?.receipts.length || 0)} receipts</p>
        <ol class="klog">${receipts || "<li>No receipts yet.</li>"}</ol>`;
    }
    if (id === "capsules") {
      const capsules = (kernel?.capsules || []).slice(-8).reverse().map((capsule) => (
        `<li>${escapeHtml(capsule.title)} · ${escapeHtml(capsule.status)} · ${escapeHtml(kernel.shortHex(capsule.digest))}</li>`
      )).join("");
      return `<ol class="klog">${capsules || "<li>None.</li>"}</ol>`;
    }
    if (id === "energy") {
      const energy = kernel?.energy || {};
      return `<p><b>${escapeHtml(energy.label || "UNAVAILABLE")}</b> · ${escapeHtml(energy.watts ?? 15)} W proxy · ${escapeHtml(energy.joules ?? "—")} J modeled</p>
        <p>${escapeHtml(energy.note || "CPU-time proxy. Not RAPL. Not NVML.")}</p>`;
    }
    if (id === "alignment") {
      return `<p>Baked same-origin snapshot. Product URLs are binds, not cloned runtimes.</p><div id="align-inline"></div>`;
    }
    if (id === "kernel") {
      const storage = kernel?.storage || {};
      return `<p>Storage ${escapeHtml(storage.kind || "UNKNOWN")} · durability ${escapeHtml(storage.durability || "UNKNOWN")}</p>
        <p>IndexedDB when the browser allows it. In-memory fallback is labeled PARTIAL, not durable.</p>
        <label for="ktitle">Title</label><input id="ktitle" maxlength="160" value="${escapeHtml(state.title)}">
        <label for="kbody">Payload</label><textarea id="kbody" maxlength="20000">${escapeHtml(state.body)}</textarea>
        <div class="kactions">
          <button type="button" class="button" id="ksubmit">Submit envelope</button>
          <button type="button" class="button" id="ktamper">Tamper one byte</button>
          <button type="button" class="button" id="kheal">Run healer</button>
        </div>`;
    }
    return `<ul class="klog">
      <li>Product signer / RAPL joules / www identity — observed, often UNAVAILABLE</li>
      <li>Λ uniqueness — Conjecture 1</li>
      <li>Post-quantum KEM — ROADMAP</li>
      <li>Hugging Face / Cloudflare writes — not from this desk</li>
      <li>Unhackable — not claimed</li>
    </ul>`;
  }

  function renderDesk() {
    const element = byId("kernel-app");
    if (!element) return;
    if (!kernelAvailable()) {
      element.innerHTML = '<p class="bad" role="alert">Local kernel UNAVAILABLE — kernel.js did not initialize.</p>';
      return;
    }
    const dock = APPS.map((app) => (
      `<button type="button" class="dock-key${state.active === app.id ? " on" : ""}" data-open="${escapeHtml(app.id)}" title="${escapeHtml(app.key)} ${escapeHtml(app.title)}">${escapeHtml(app.key)} ${escapeHtml(app.title)}</button>`
    )).join("");
    const windows = state.open.map((id) => {
      const app = APPS.find((item) => item.id === id);
      return `<section class="oswin${state.active === id ? " active" : ""}" data-app="${escapeHtml(id)}">
        <header><button type="button" class="win-focus" data-focus="${escapeHtml(id)}">${escapeHtml(app.title)}</button>
        <button type="button" class="win-close" data-close="${escapeHtml(id)}" aria-label="Close ${escapeHtml(app.title)}">×</button></header>
        <div class="win-body">${appBody(id)}</div>
      </section>`;
    }).join("");
    const palette = state.palette ? `<div class="palette" role="dialog" aria-label="App palette">${APPS.map((app) => (
      `<button type="button" data-open="${escapeHtml(app.id)}">${escapeHtml(app.key)} · ${escapeHtml(app.title)}</button>`
    )).join("")}</div>` : "";

    element.innerHTML = `<div class="osdesk">
      <div class="osdock" aria-label="Apps">${dock}</div>
      <div class="oswins">${windows}</div>
      ${palette}
    </div>`;

    element.querySelectorAll("[data-open]").forEach((node) => {
      node.addEventListener("click", () => openApp(node.getAttribute("data-open")));
    });
    element.querySelectorAll("[data-focus]").forEach((node) => {
      node.addEventListener("click", () => openApp(node.getAttribute("data-focus")));
    });
    element.querySelectorAll("[data-close]").forEach((node) => {
      node.addEventListener("click", () => closeApp(node.getAttribute("data-close")));
    });
    bindActions();
  }

  function captureForm() {
    state.title = byId("ktitle")?.value ?? state.title;
    state.body = byId("kbody")?.value ?? state.body;
  }

  function bindActions() {
    const proof = byId("kproof");
    const submit = byId("ksubmit");
    const tamper = byId("ktamper");
    const heal = byId("kheal");
    const kernel = window.Alloy;
    if (proof) proof.addEventListener("click", () => runAction(async () => {
      state.proof = await kernel.runLocalProof({
        title: state.title,
        body: state.body,
        policyClass: state.policy,
        adapter: kernel.ADAPTER_CURRENT,
      });
      const blocked = state.proof.blocked?.decision === "DENY";
      state.message = blocked
        ? "Local proof complete — commit, reuse, adapter BLOCKED, tamper, heal."
        : "Local proof ran; adapter block did not fire.";
      state.tone = blocked ? "ok" : "warn";
      state.active = "command";
    }));
    if (submit) submit.addEventListener("click", () => runAction(async () => {
      captureForm();
      const outcome = await kernel.govern({
        title: state.title,
        body: state.body,
        policyClass: state.policy,
        adapter: kernel.ADAPTER_CURRENT,
      });
      state.message = `${outcome.decision} — ${outcome.reason}`;
      state.tone = outcome.decision === "ALLOW" ? "ok" : "bad";
    }));
    if (tamper) tamper.addEventListener("click", () => runAction(async () => {
      state.message = await kernel.injectFault();
      state.tone = "warn";
    }));
    if (heal) heal.addEventListener("click", () => runAction(async () => {
      const outcome = await kernel.runWatchdog();
      state.message = outcome.verified
        ? `Watchdog restored ${outcome.restored} snapshot(s).`
        : "Watchdog degraded.";
      state.tone = outcome.verified ? "ok" : "bad";
    }));
  }

  async function runAction(operation) {
    if (state.busy) return;
    state.busy = true;
    renderDesk();
    try {
      await operation();
    } catch (error) {
      state.message = `UNAVAILABLE — ${error instanceof Error ? error.message : String(error)}`;
      state.tone = "bad";
    } finally {
      state.busy = false;
      renderDesk();
    }
  }

  function onKey(event) {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      state.palette = !state.palette;
      renderDesk();
      return;
    }
    if (event.key === "Escape" && state.palette) {
      state.palette = false;
      renderDesk();
      return;
    }
    if (event.target && /input|textarea|select/i.test(event.target.tagName)) return;
    const app = APPS.find((item) => item.key === event.key);
    if (app) openApp(app.id);
  }

  async function start() {
    await bootAlignment();
    if (!kernelAvailable()) {
      renderDesk();
      return;
    }
    window.Alloy.subscribe(renderDesk);
    try {
      await window.Alloy.boot();
      state.message = `${window.Alloy.status} · local fabric. Remotes fail-soft.`;
      state.tone = "ok";
    } catch (error) {
      state.message = `UNAVAILABLE — ${error instanceof Error ? error.message : String(error)}`;
      state.tone = "bad";
    }
    renderDesk();
    window.addEventListener("keydown", onKey);
  }

  void start();
})();
