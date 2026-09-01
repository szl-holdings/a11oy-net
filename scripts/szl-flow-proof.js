/* SZL Proof Flow Shell v1 — shared journeys for the independent record origin. */
(function () {
  "use strict";

  if (window.__SZL_PROOF_FLOW_SHELL__) return;
  window.__SZL_PROOF_FLOW_SHELL__ = true;

  var PRODUCT = "https://a-11-oy.com";
  var PROOF = "https://a11oy.net";
  var ROUTES = [
    { prefix: "/record", theme: "forensic", journey: "proofs" },
    { prefix: "/diligence", theme: "dossier", journey: "proofs" },
    { prefix: "/estate", theme: "atlas-mono", journey: "models" },
    { prefix: "/atelier", theme: "atelier-mono", journey: "models" },
    { prefix: "/khipu", theme: "weave-mono", journey: "kernels" },
    { prefix: "/decision", theme: "decision-mono", journey: "products" },
    { prefix: "/security", theme: "security-mono", journey: "proofs" },
    { prefix: "/notes", theme: "notebook", journey: "proofs" },
    { prefix: "/origin", theme: "dossier", journey: "proofs" },
    { prefix: "/", theme: "ledger", journey: "start" }
  ];
  var JOURNEYS = [
    { id: "start", label: "Start Here", href: PROOF + "/" },
    { id: "products", label: "Products & Demos", href: PRODUCT + "/" },
    { id: "models", label: "Models & Data", href: PROOF + "/estate/" },
    { id: "kernels", label: "Kernels & SDKs", href: PROOF + "/khipu/" },
    { id: "proofs", label: "Proofs & Research", href: PROOF + "/record/" }
  ];

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
  function announce(message) {
    var box = document.querySelector(".szl-proof-announcement");
    if (!box) return;
    box.textContent = message;
    box.dataset.open = "true";
    window.clearTimeout(announce.timer);
    announce.timer = window.setTimeout(function () { box.dataset.open = "false"; }, 1800);
  }
  function updateTheme() {
    var route = routeNow();
    document.body.dataset.szlProofTheme = route.theme;
    document.body.dataset.szlProofFlow = "record";
    document.documentElement.dataset.szlProofFlowReady = "true";
    document.querySelectorAll(".szl-proof-link").forEach(function (link) {
      if (link.dataset.journey === route.journey) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    });
  }
  function updateProgress() {
    var root = document.documentElement;
    var total = Math.max(1, root.scrollHeight - window.innerHeight);
    var pct = Math.max(0, Math.min(100, (window.scrollY / total) * 100));
    root.style.setProperty("--szl-proof-progress", pct.toFixed(2) + "%");
  }
  function build() {
    if (!document.body || document.querySelector(".szl-proof-rail")) return;
    var progress = el("div", { className: "szl-proof-progress", "aria-hidden": "true" });
    var rail = el("nav", { className: "szl-proof-rail", "aria-label": "SZL public-estate journeys", dataset: { open: "false" } });
    var origin = el("div", { className: "szl-proof-origin", title: "a11oy.net independent proof origin" });
    origin.appendChild(el("span", {}, "Record"));
    var links = el("div", { className: "szl-proof-links", id: "szl-proof-links" });
    JOURNEYS.forEach(function (journey) {
      links.appendChild(el("a", { className: "szl-proof-link", href: journey.href, dataset: { journey: journey.id } }, journey.label));
    });
    var actions = el("div", { className: "szl-proof-actions" });
    var toggle = el("button", { className: "szl-proof-toggle", type: "button", "aria-controls": "szl-proof-links", "aria-expanded": "false", "aria-label": "Open journey navigation" }, "Menu");
    toggle.addEventListener("click", function () {
      var open = rail.dataset.open !== "true";
      rail.dataset.open = String(open);
      toggle.setAttribute("aria-expanded", String(open));
      toggle.textContent = open ? "Close" : "Menu";
      if (open) announce("Journey navigation opened");
    });
    var switcher = el("a", { className: "szl-proof-switch", href: PRODUCT + "/", title: "Open the product command origin" });
    switcher.appendChild(el("span", {}, "Open"));
    switcher.appendChild(el("strong", {}, "Product"));
    actions.appendChild(toggle);
    actions.appendChild(switcher);
    rail.appendChild(origin);
    rail.appendChild(links);
    rail.appendChild(actions);
    var live = el("div", { className: "szl-proof-announcement", role: "status", "aria-live": "polite", dataset: { open: "false" } });
    document.body.appendChild(progress);
    document.body.appendChild(rail);
    document.body.appendChild(live);
    updateTheme();
    updateProgress();
    var scheduled = false;
    window.addEventListener("scroll", function () {
      if (scheduled) return;
      scheduled = true;
      window.requestAnimationFrame(function () { scheduled = false; updateProgress(); });
    }, { passive: true });
    window.addEventListener("resize", updateProgress, { passive: true });
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
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", build, { once: true });
  else build();
}());
