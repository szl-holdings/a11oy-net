/*
 * A11oy Proof Network — Holographic Evidence Vault v2.0.0
 * Interactive enhancement only. Zero-JavaScript evidence documents use the
 * equivalent CSS-only rail installed by the source binder.
 * SPDX-License-Identifier: Apache-2.0
 */
(() => {
  "use strict";
  if (window.__SZL_PROOF_HOLO_V2__) return;
  window.__SZL_PROOF_HOLO_V2__ = true;

  const VERSION = "2.0.0";
  const PRODUCT = "https://a-11-oy.com";
  const PROOF = "https://a11oy.net";
  const REDUCE_MOTION = window.matchMedia("(prefers-reduced-motion: reduce)");
  const FINE_POINTER = window.matchMedia("(pointer: fine)");
  const SAVE_DATA = Boolean(navigator.connection && navigator.connection.saveData);
  const ROUTES = [
    ["/record", "RECORD", "Proof"], ["/diligence", "Diligence Room", "Proof"],
    ["/estate", "Estate Atlas", "Models"], ["/atelier", "Atelier Record", "Models"],
    ["/khipu", "KHIPU Record", "Kernels"], ["/decision", "Decision Record", "Products"],
    ["/security", "Security Record", "Proof"], ["/notes", "Research Notes", "Proof"],
    ["/origin", "Origin Record", "Proof"], ["/vessels", "Vessels Record", "Products"],
    ["/terra", "Terra Record", "Products"], ["/aegis", "Aegis Record", "Products"],
    ["/counsel", "Counsel Record", "Products"], ["/factory", "Factory Record", "Products"],
    ["/frontiers", "Frontiers Record", "Proof"], ["/", "A11oy Proof Network", "Start"],
  ];
  const LINKS = [
    ["Start", `${PROOF}/`], ["Products", `${PRODUCT}/`], ["Models", `${PROOF}/estate/`],
    ["Kernels", `${PROOF}/khipu/`], ["Proof", `${PROOF}/record/`],
  ];

  function route() {
    const path = location.pathname.replace(/\/+$/, "") || "/";
    for (const [prefix, label, journey] of ROUTES) {
      if (prefix === "/" || path === prefix || path.startsWith(`${prefix}/`)) return { prefix, label, journey };
    }
    return { prefix: "/", label: "A11oy Proof Network", journey: "Start" };
  }

  function element(name, attributes = {}, text = null) {
    const node = document.createElement(name);
    for (const [key, value] of Object.entries(attributes)) {
      if (key === "className") node.className = value;
      else if (key === "dataset") Object.assign(node.dataset, value);
      else node.setAttribute(key, value);
    }
    if (text !== null) node.textContent = text;
    return node;
  }

  function addSkipLink() {
    if (document.querySelector(".szl-proof-holo-skip, .skip, .skip-link")) return;
    const main = document.querySelector("main, [role='main']");
    if (!main) return;
    if (!main.id) main.id = "szl-proof-holo-main";
    document.body.prepend(element("a", { className: "szl-proof-holo-skip", href: `#${main.id}` }, "Skip to main content"));
  }

  function adoptExistingRail() {
    const existing = document.querySelector(".szl-proof-rail, .szl-proof-static-rail");
    if (!existing) return false;
    existing.dataset.szlProofHoloAdopted = "true";
    return true;
  }

  function buildRail(currentRoute) {
    if (adoptExistingRail() || document.querySelector(".szl-proof-holo-rail")) return;
    const rail = element("header", { className: "szl-proof-holo-rail", dataset: { szlProofHoloRail: "v2" } });
    const identity = element("a", { className: "szl-proof-holo-identity", href: `${PROOF}/`, "aria-label": "Open the A11oy Proof Network" });
    identity.append(element("span", { className: "szl-proof-holo-mark", "aria-hidden": "true" }));
    const copy = element("span", { className: "szl-proof-holo-copy" });
    copy.append(element("span", { className: "szl-proof-holo-eyebrow" }, "SZL · Evidence Vault"));
    copy.append(element("span", { className: "szl-proof-holo-label" }, currentRoute.label));
    identity.append(copy);

    const controls = element("div", { className: "szl-proof-holo-controls" });
    const menu = element("button", { className: "szl-proof-holo-menu", type: "button", "aria-label": "Open proof navigation", "aria-expanded": "false", "aria-controls": "szl-proof-holo-nav" }, "Menu");
    const nav = element("nav", { className: "szl-proof-holo-nav", id: "szl-proof-holo-nav", "aria-label": "A11oy proof journeys", dataset: { open: "false" } });
    for (const [label, href] of LINKS) {
      const attributes = { className: "szl-proof-holo-link", href };
      if (label === currentRoute.journey) attributes["aria-current"] = "page";
      nav.append(element("a", attributes, label));
    }
    controls.append(menu, nav);
    rail.append(identity, controls);
    document.body.prepend(rail);

    const close = (focus = false) => {
      nav.dataset.open = "false";
      menu.setAttribute("aria-expanded", "false");
      menu.setAttribute("aria-label", "Open proof navigation");
      menu.textContent = "Menu";
      if (focus) menu.focus();
    };
    menu.addEventListener("click", () => {
      const open = nav.dataset.open !== "true";
      nav.dataset.open = String(open);
      menu.setAttribute("aria-expanded", String(open));
      menu.setAttribute("aria-label", open ? "Close proof navigation" : "Open proof navigation");
      menu.textContent = open ? "Close" : "Menu";
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && nav.dataset.open === "true") close(true);
    });
    document.addEventListener("pointerdown", (event) => {
      if (nav.dataset.open === "true" && !rail.contains(event.target)) close(false);
    });
  }

  function addAmbientAndProgress() {
    if (!document.getElementById("szl-proof-holo-ambient")) {
      document.body.prepend(element("div", { id: "szl-proof-holo-ambient", "aria-hidden": "true", dataset: { szlProofHoloDecorative: "true" } }));
    }
    if (!document.querySelector(".szl-proof-holo-progress")) {
      document.body.append(element("div", { className: "szl-proof-holo-progress", "aria-hidden": "true", dataset: { szlProofHoloDecorative: "true" } }));
    }
  }

  function enhancePanels() {
    if (document.documentElement.hasAttribute("data-szl-proof-holo-no-auto-panels")) return;
    const selectors = ["main .card", "main .panel", "main .record-card", "main .evidence-card", "main [data-panel]"];
    const seen = new Set();
    for (const node of document.querySelectorAll(selectors.join(","))) {
      if (seen.size >= 20) break;
      if (seen.has(node) || node.closest("nav, header, footer, table, pre, code, form, dialog")) continue;
      seen.add(node);
      node.setAttribute("data-szl-proof-holo-panel", "auto");
    }
  }

  function installMotion() {
    const root = document.documentElement;
    let pointerFrame = 0;
    let scrollFrame = 0;
    let x = window.innerWidth * .72;
    let y = Math.min(window.innerHeight * .18, 220);
    const commitPointer = () => {
      pointerFrame = 0;
      root.style.setProperty("--szl-proof-v2-pointer-x", `${Math.round((x / Math.max(window.innerWidth, 1)) * 1000) / 10}%`);
      root.style.setProperty("--szl-proof-v2-pointer-y", `${Math.round((y / Math.max(window.innerHeight, 1)) * 1000) / 10}%`);
    };
    const pointer = (event) => {
      if (REDUCE_MOTION.matches || !FINE_POINTER.matches || SAVE_DATA || document.hidden) return;
      x = event.clientX; y = event.clientY;
      if (!pointerFrame) pointerFrame = requestAnimationFrame(commitPointer);
    };
    const commitScroll = () => {
      scrollFrame = 0;
      const maximum = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
      root.style.setProperty("--szl-proof-v2-progress", Math.max(0, Math.min(100, window.scrollY / maximum * 100)).toFixed(2));
    };
    const scroll = () => { if (!scrollFrame) scrollFrame = requestAnimationFrame(commitScroll); };
    if (!SAVE_DATA) window.addEventListener("pointermove", pointer, { passive: true });
    window.addEventListener("scroll", scroll, { passive: true });
    window.addEventListener("resize", scroll, { passive: true });
    document.addEventListener("visibilitychange", () => {
      root.dataset.szlProofHoloPaused = String(document.hidden);
      if (!document.hidden) scroll();
    });
    root.dataset.szlProofHoloReducedMotion = String(REDUCE_MOTION.matches);
    root.dataset.szlProofHoloSaveData = String(SAVE_DATA);
    commitPointer(); commitScroll();
  }

  function boot() {
    if (!document.body || document.documentElement.hasAttribute("data-szl-proof-holo-disabled")) return;
    const currentRoute = route();
    document.documentElement.dataset.szlProofHolo = "v2";
    document.documentElement.dataset.szlProofHoloRoute = currentRoute.prefix;
    addAmbientAndProgress(); addSkipLink(); buildRail(currentRoute); enhancePanels(); installMotion();
    window.SZLProofHolo = Object.freeze({ version: VERSION, route: Object.freeze(currentRoute), decorativeMotion: true, measuredTelemetry: false, zeroJavascriptDocumentsSupported: true });
    document.dispatchEvent(new CustomEvent("szl:proof-holo-ready", { detail: { version: VERSION, route: currentRoute.prefix, label: currentRoute.label } }));
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot, { once: true });
  else boot();
})();
