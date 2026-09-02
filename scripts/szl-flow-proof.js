/* SZL Proof Flow Shell v2 — forensic journeys with adaptive spectral depth. */
(function () {
  "use strict";

  if (window.__SZL_PROOF_FLOW_SHELL__) return;
  window.__SZL_PROOF_FLOW_SHELL__ = true;

  var VERSION = "2.0.0";
  var PRODUCT = "https://a-11-oy.com";
  var PROOF = "https://a11oy.net";
  var SPECTRAL_STYLE = "/assets/szl-spectral-proof-v2.css";
  var ROUTES = [
    { prefix: "/record", theme: "forensic", journey: "proofs", label: "Receipt Record", mode: "Checksum instrument" },
    { prefix: "/diligence", theme: "dossier", journey: "proofs", label: "Diligence Room", mode: "Evidence dossier" },
    { prefix: "/estate", theme: "atlas-mono", journey: "models", label: "Estate Record", mode: "Topology record" },
    { prefix: "/atelier", theme: "atelier-mono", journey: "models", label: "Atelier Record", mode: "Artifact specimen" },
    { prefix: "/khipu", theme: "weave-mono", journey: "kernels", label: "KHIPU Record", mode: "Memory record" },
    { prefix: "/decision", theme: "decision-mono", journey: "products", label: "Decision Record", mode: "Adjudication record" },
    { prefix: "/security", theme: "security-mono", journey: "proofs", label: "Security Record", mode: "Control record" },
    { prefix: "/notes", theme: "notebook", journey: "proofs", label: "Research Notes", mode: "Notebook record" },
    { prefix: "/origin", theme: "dossier", journey: "proofs", label: "Origin Record", mode: "Source dossier" },
    { prefix: "/", theme: "ledger", journey: "start", label: "A11oy Proof", mode: "Independent record origin" }
  ];
  var JOURNEYS = [
    { id: "start", label: "Start Here", href: PROOF + "/" },
    { id: "products", label: "Products & Demos", href: PRODUCT + "/" },
    { id: "models", label: "Models & Data", href: PROOF + "/estate/" },
    { id: "kernels", label: "Kernels & SDKs", href: PROOF + "/khipu/" },
    { id: "proofs", label: "Proofs & Research", href: PROOF + "/record/" }
  ];

  var state = {
    route: null,
    active: !document.hidden,
    pointerX: 50,
    pointerY: 42,
    targetX: 50,
    targetY: 42,
    velocity: 0,
    lastPointerX: 50,
    lastPointerY: 42,
    raf: 0
  };

  function pathNow() {
    var path = window.location.pathname || "/";
    if (path.length > 1) path = path.replace(/\/+$/, "");
    return path || "/";
  }

  function routeNow() {
    var path = pathNow();
    for (var i = 0; i < ROUTES.length; i += 1) {
      var row = ROUTES[i];
      if (row.prefix === "/" || path === row.prefix || path.indexOf(row.prefix + "/") === 0) return row;
    }
    return ROUTES[ROUTES.length - 1];
  }

  function el(name, attrs, text) {
    var node = document.createElement(name);
    Object.keys(attrs || {}).forEach(function (key) {
      if (key === "className") node.className = attrs[key];
      else if (key === "dataset") Object.keys(attrs.dataset).forEach(function (d) { node.dataset[d] = attrs.dataset[d]; });
      else node.setAttribute(key, attrs[key]);
    });
    if (text != null) node.textContent = text;
    return node;
  }

  function ensureSpectralStyle() {
    if (document.querySelector('link[data-szl-proof-spectral-v2="true"]')) return;
    var link = el("link", {
      rel: "stylesheet",
      href: SPECTRAL_STYLE,
      dataset: { szlProofSpectralV2: "true" }
    });
    document.head.appendChild(link);
  }

  function performanceTier() {
    var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var saveData = Boolean(navigator.connection && navigator.connection.saveData);
    var memory = Number(navigator.deviceMemory || 8);
    var cores = Number(navigator.hardwareConcurrency || 8);
    if (reduced || saveData || memory <= 2 || cores <= 2) return "quiet";
    if (window.innerWidth <= 820 || memory <= 4 || cores <= 4) return "balanced";
    return "full";
  }

  function announce(message) {
    var box = document.querySelector(".szl-proof-announcement");
    if (!box) return;
    box.textContent = message;
    box.dataset.open = "true";
    window.clearTimeout(announce.timer);
    announce.timer = window.setTimeout(function () { box.dataset.open = "false"; }, 1800);
  }

  function buildSpectralField() {
    if (document.querySelector(".szl-proof-spectral-field")) return;
    var field = el("div", {
      className: "szl-proof-spectral-field",
      "aria-hidden": "true",
      dataset: { version: VERSION }
    });
    ["grid", "ledger", "nodes", "beam", "scan", "bloom"].forEach(function (name) {
      field.appendChild(el("span", { className: "szl-proof-spectral-layer szl-proof-spectral-" + name }));
    });
    document.body.appendChild(field);
  }

  function markProofCards() {
    if (!document.body) return;
    var candidates = document.querySelectorAll(
      "main .card, main .panel, main .tile, main article, main [data-card], main [data-panel]"
    );
    Array.prototype.slice.call(candidates, 0, 120).forEach(function (node) {
      if (node.closest(".szl-proof-rail")) return;
      node.dataset.szlProofCard = "true";
    });
    Array.prototype.slice.call(document.querySelectorAll("main > section, main > article"), 0, 80).forEach(function (node) {
      node.dataset.szlProofReveal = "true";
    });
  }

  function updateTheme() {
    var route = routeNow();
    state.route = route;
    document.body.dataset.szlProofTheme = route.theme;
    document.body.dataset.szlProofFlow = "record";
    document.body.dataset.szlProofSpectral = "record";
    document.body.dataset.szlProofInstrument = route.label;
    document.documentElement.dataset.szlProofFlowReady = "true";
    document.documentElement.dataset.szlProofSpectralV2 = "true";
    document.documentElement.dataset.szlProofPerformance = performanceTier();
    document.querySelectorAll(".szl-proof-link").forEach(function (link) {
      if (link.dataset.journey === route.journey) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    });
    var context = document.querySelector(".szl-proof-context");
    var mode = document.querySelector(".szl-proof-mode");
    if (context) context.textContent = route.label;
    if (mode) mode.textContent = route.mode;
  }

  function updateProgress() {
    var root = document.documentElement;
    var total = Math.max(1, root.scrollHeight - window.innerHeight);
    var pct = Math.max(0, Math.min(100, (window.scrollY / total) * 100));
    var progress = pct / 100;
    root.style.setProperty("--szl-proof-progress", pct.toFixed(2) + "%");
    root.style.setProperty("--szl-proof-spectral-grid-shift-y", (-progress * 16).toFixed(2) + "px");
    root.style.setProperty("--szl-proof-spectral-scroll-shift", (-progress * 11).toFixed(2) + "px");
    root.style.setProperty("--szl-proof-spectral-rotate", (progress * 5).toFixed(2) + "deg");
  }

  function flushPointer() {
    state.raf = 0;
    if (!state.active) return;
    state.pointerX += (state.targetX - state.pointerX) * .16;
    state.pointerY += (state.targetY - state.pointerY) * .16;
    state.velocity *= .82;
    var velocity = Math.min(1, state.velocity / 18);
    var root = document.documentElement;
    root.style.setProperty("--szl-proof-spectral-pointer-x", state.pointerX.toFixed(2) + "%");
    root.style.setProperty("--szl-proof-spectral-pointer-y", state.pointerY.toFixed(2) + "%");
    root.style.setProperty("--szl-proof-spectral-grid-shift-x", ((50 - state.pointerX) * .62).toFixed(2) + "px");
    root.style.setProperty("--szl-proof-spectral-ledger-shift-x", ((state.pointerX - 50) * .68).toFixed(2) + "px");
    root.style.setProperty("--szl-proof-spectral-ledger-shift-y", ((state.pointerY - 50) * .48).toFixed(2) + "px");
    root.style.setProperty("--szl-proof-spectral-node-position-x", (50 + (state.pointerX - 50) * .1).toFixed(2) + "%");
    root.style.setProperty("--szl-proof-spectral-node-position-y", (50 + (state.pointerY - 50) * .1).toFixed(2) + "%");
    root.style.setProperty("--szl-proof-spectral-bloom-opacity", (.34 + velocity * .13).toFixed(3));
    root.style.setProperty("--szl-proof-spectral-bloom-scale", (1 + velocity * .02).toFixed(4));
    if (
      Math.abs(state.targetX - state.pointerX) > .08 ||
      Math.abs(state.targetY - state.pointerY) > .08 ||
      state.velocity > .3
    ) schedulePointer();
  }

  function schedulePointer() {
    if (!state.raf) state.raf = window.requestAnimationFrame(flushPointer);
  }

  function onPointer(event) {
    if (document.documentElement.dataset.szlProofPerformance === "quiet") return;
    var nextX = Math.max(0, Math.min(100, (event.clientX / Math.max(1, window.innerWidth)) * 100));
    var nextY = Math.max(0, Math.min(100, (event.clientY / Math.max(1, window.innerHeight)) * 100));
    var dx = nextX - state.lastPointerX;
    var dy = nextY - state.lastPointerY;
    state.velocity = Math.min(28, state.velocity + Math.sqrt(dx * dx + dy * dy));
    state.lastPointerX = nextX;
    state.lastPointerY = nextY;
    state.targetX = nextX;
    state.targetY = nextY;
    schedulePointer();
  }

  function build() {
    if (!document.body || document.querySelector(".szl-proof-rail")) return;
    ensureSpectralStyle();
    buildSpectralField();

    var progress = el("div", { className: "szl-proof-progress", "aria-hidden": "true" });
    var rail = el("nav", {
      className: "szl-proof-rail",
      "aria-label": "SZL public-estate journeys",
      dataset: { open: "false", version: VERSION }
    });
    var origin = el("div", { className: "szl-proof-origin", title: "a11oy.net independent proof origin" });
    origin.appendChild(el("span", {}, "Record"));
    origin.appendChild(el("span", { className: "szl-proof-context" }, "A11oy Proof"));
    origin.appendChild(el("span", { className: "szl-proof-mode" }, "Independent record origin"));

    var links = el("div", { className: "szl-proof-links", id: "szl-proof-links" });
    JOURNEYS.forEach(function (journey) {
      links.appendChild(el("a", {
        className: "szl-proof-link",
        href: journey.href,
        dataset: { journey: journey.id }
      }, journey.label));
    });

    var actions = el("div", { className: "szl-proof-actions" });
    var toggle = el("button", {
      className: "szl-proof-toggle",
      type: "button",
      "aria-controls": "szl-proof-links",
      "aria-expanded": "false",
      "aria-label": "Open journey navigation"
    }, "Menu");
    toggle.addEventListener("click", function () {
      var open = rail.dataset.open !== "true";
      rail.dataset.open = String(open);
      toggle.setAttribute("aria-expanded", String(open));
      toggle.textContent = open ? "Close" : "Menu";
      if (open) announce("Journey navigation opened");
    });

    var switcher = el("a", {
      className: "szl-proof-switch",
      href: PRODUCT + "/",
      title: "Open the product command origin"
    });
    switcher.appendChild(el("span", {}, "Open"));
    switcher.appendChild(el("strong", {}, "Product"));

    actions.appendChild(toggle);
    actions.appendChild(switcher);
    rail.appendChild(origin);
    rail.appendChild(links);
    rail.appendChild(actions);

    var live = el("div", {
      className: "szl-proof-announcement",
      role: "status",
      "aria-live": "polite",
      dataset: { open: "false" }
    });

    document.body.appendChild(progress);
    document.body.appendChild(rail);
    document.body.appendChild(live);
    markProofCards();
    updateTheme();
    updateProgress();
    schedulePointer();

    var scheduled = false;
    window.addEventListener("scroll", function () {
      if (scheduled) return;
      scheduled = true;
      window.requestAnimationFrame(function () {
        scheduled = false;
        updateProgress();
      });
    }, { passive: true });
    window.addEventListener("resize", function () {
      document.documentElement.dataset.szlProofPerformance = performanceTier();
      updateProgress();
    }, { passive: true });
    if (window.matchMedia && window.matchMedia("(pointer: fine)").matches) {
      window.addEventListener("pointermove", onPointer, { passive: true });
    }
    document.addEventListener("visibilitychange", function () {
      state.active = !document.hidden;
      if (state.active) schedulePointer();
    });
    document.addEventListener("click", function (event) {
      if (rail.dataset.open !== "true" || rail.contains(event.target)) return;
      rail.dataset.open = "false";
      toggle.setAttribute("aria-expanded", "false");
      toggle.textContent = "Menu";
    });
    document.addEventListener("keydown", function (event) {
      if (event.key !== "Escape" || rail.dataset.open !== "true") return;
      rail.dataset.open = "false";
      toggle.setAttribute("aria-expanded", "false");
      toggle.textContent = "Menu";
      toggle.focus();
    });

    document.dispatchEvent(new CustomEvent("szl:proof-spectral-ready", {
      detail: { version: VERSION, theme: state.route.theme, instrument: state.route.label }
    }));
  }

  function routeChanged() {
    updateTheme();
    window.requestAnimationFrame(function () {
      markProofCards();
      updateProgress();
    });
  }

  ["pushState", "replaceState"].forEach(function (name) {
    var original = history[name];
    if (typeof original !== "function") return;
    history[name] = function () {
      var result = original.apply(this, arguments);
      window.dispatchEvent(new Event("szl:proof-routechange"));
      return result;
    };
  });
  window.addEventListener("popstate", routeChanged);
  window.addEventListener("szl:proof-routechange", routeChanged);

  ensureSpectralStyle();
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", build, { once: true });
  else build();
}());
