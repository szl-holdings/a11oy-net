/* SPDX-License-Identifier: Apache-2.0 */
(() => {
  "use strict";

  const state = {
    title: "Session note",
    body: "A thought sealed on this device.",
    adapter: "alloy-local-v1",
    policy: "private",
    message: "",
    tone: "",
    busy: false,
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

  function captureForm() {
    state.title = byId("ktitle")?.value ?? state.title;
    state.body = byId("kbody")?.value ?? state.body;
    state.adapter = byId("kadapter")?.value ?? state.adapter;
  }

  function kernelAvailable() {
    return typeof window.Alloy === "object" && window.Alloy !== null;
  }

  function renderKernel() {
    const element = byId("kernel-app");
    if (!element) return;
    if (!kernelAvailable()) {
      element.innerHTML = '<p class="bad" role="alert">Local kernel UNAVAILABLE — kernel.js did not initialize.</p>';
      return;
    }

    const kernel = window.Alloy;
    state.adapter ||= kernel.ADAPTER_CURRENT;
    const receipts = [...kernel.receipts].slice(-8).reverse().map((receipt) => (
      `<li>#${escapeHtml(receipt.seq)} <b>${escapeHtml(receipt.type)}</b> ${escapeHtml(receipt.note)} <span>${escapeHtml(kernel.shortHex(receipt.digest))}</span></li>`
    )).join("");
    const capsules = [...kernel.capsules].slice(-6).reverse().map((capsule) => (
      `<li>${escapeHtml(capsule.title)} · ${escapeHtml(capsule.status)} · ${escapeHtml(kernel.shortHex(capsule.digest))}</li>`
    )).join("");
    const disabled = state.busy || kernel.status === "UNAVAILABLE" ? " disabled" : "";

    element.innerHTML = `<div class="kbox">
      <div class="kcard">
        <p class="eyebrow">${escapeHtml(kernel.status)} · kid ${escapeHtml(kernel.identity?.kid || "booting")} · epoch ${escapeHtml(kernel.epoch)}</p>
        <label for="ktitle">Title</label><input id="ktitle" maxlength="160" autocomplete="off" value="${escapeHtml(state.title)}"${disabled}>
        <label for="kbody">Payload</label><textarea id="kbody" maxlength="20000"${disabled}>${escapeHtml(state.body)}</textarea>
        <label for="kadapter">Adapter</label>
        <select id="kadapter"${disabled}>
          <option value="${escapeHtml(kernel.ADAPTER_CURRENT)}"${state.adapter === kernel.ADAPTER_CURRENT ? " selected" : ""}>${escapeHtml(kernel.ADAPTER_CURRENT)} pinned</option>
          <option value="alloy-local-v0"${state.adapter === "alloy-local-v0" ? " selected" : ""}>alloy-local-v0 stale</option>
        </select>
        <div class="kactions">
          <button type="button" class="button primary" id="ksubmit"${disabled}>Submit envelope</button>
          <button type="button" class="button" id="ktamper"${disabled}>Tamper one byte</button>
          <button type="button" class="button" id="kheal"${disabled}>Run healer</button>
        </div>
        <p class="${escapeHtml(state.tone)}" role="status" aria-live="polite">${escapeHtml(state.busy ? "Working locally…" : state.message)}</p>
      </div>
      <div class="kcard">
        <p class="eyebrow">Ledger ${escapeHtml(kernel.receipts.length)} · capsules ${escapeHtml(kernel.capsules.length)} · healed ${escapeHtml(kernel.health.healed)} · blocked ${escapeHtml(kernel.health.blocked)}</p>
        <p>Replayable: ${kernel.health.ledgerReplayable ? "MEASURED" : "degraded"} · last verify ${escapeHtml(kernel.health.lastVerify || "—")}</p>
        <ol class="klog">${receipts || "<li>No receipts yet.</li>"}</ol>
        <p class="eyebrow">Capsules</p>
        <ol class="klog">${capsules || "<li>None.</li>"}</ol>
      </div>
    </div>`;

    const submit = byId("ksubmit");
    const tamper = byId("ktamper");
    const heal = byId("kheal");
    if (submit) submit.addEventListener("click", () => runAction(async () => {
      captureForm();
      const outcome = await kernel.govern({
        title: state.title,
        body: state.body,
        policyClass: state.policy,
        adapter: state.adapter,
      });
      state.message = `${outcome.decision} — ${outcome.reason} · receipt ${outcome.receipt.seq}`;
      state.tone = outcome.decision === "ALLOW" ? "ok" : "bad";
    }));
    if (tamper) tamper.addEventListener("click", () => runAction(async () => {
      captureForm();
      state.message = await kernel.injectFault();
      state.tone = "warn";
    }));
    if (heal) heal.addEventListener("click", () => runAction(async () => {
      captureForm();
      const outcome = await kernel.runWatchdog();
      const verified = outcome.verified === true && kernel.health.ledgerReplayable === true;
      state.message = verified
        ? `Watchdog complete — restored ${outcome.restored} authenticated local snapshot(s).`
        : "Watchdog complete — degraded state remains.";
      state.tone = verified ? "ok" : "bad";
    }));
  }

  async function runAction(operation) {
    if (state.busy) return;
    captureForm();
    state.busy = true;
    renderKernel();
    try {
      await operation();
    } catch (error) {
      state.message = `UNAVAILABLE — ${error instanceof Error ? error.message : String(error)}`;
      state.tone = "bad";
    } finally {
      state.busy = false;
      renderKernel();
    }
  }

  async function start() {
    await bootAlignment();
    if (!kernelAvailable()) {
      renderKernel();
      return;
    }
    window.Alloy.subscribe(renderKernel);
    try {
      await window.Alloy.boot();
    } catch (error) {
      state.message = `UNAVAILABLE — ${error instanceof Error ? error.message : String(error)}`;
      state.tone = "bad";
    }
    renderKernel();
  }

  void start();
})();