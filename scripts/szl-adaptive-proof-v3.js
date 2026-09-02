/*
 * SZL Adaptive Proof Theatre v3
 * Progressive viewport controller for interactive proof records.
 * Zero-JavaScript records inherit the CSS contract only.
 */
(function () {
  "use strict";

  if (window.__SZL_ADAPTIVE_PROOF_V3__) return;
  window.__SZL_ADAPTIVE_PROOF_V3__ = true;

  var root = document.documentElement;
  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  var coarse = window.matchMedia("(pointer: coarse)");
  var state = { raf: 0, mode: "", orientation: "", motion: "", observer: null };

  function viewport() {
    var visual = window.visualViewport;
    return {
      width: Math.max(1, Math.round(visual ? visual.width : window.innerWidth)),
      height: Math.max(1, Math.round(visual ? visual.height : window.innerHeight)),
    };
  }

  function saveData() {
    var connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    return Boolean(connection && connection.saveData);
  }

  function lowResource() {
    var memory = Number(navigator.deviceMemory || 0);
    var cores = Number(navigator.hardwareConcurrency || 0);
    return (memory > 0 && memory <= 2) || (cores > 0 && cores <= 2);
  }

  function modeFor(width) {
    if (width < 640) return "mobile";
    if (width < 1024) return "tablet";
    if (width < 1680) return "desktop";
    return "theatre";
  }

  function motionFor() {
    if (reduced.matches || saveData() || lowResource()) return "quiet";
    if (coarse.matches || window.innerWidth < 900) return "balanced";
    return "full";
  }

  function emit(name, detail) {
    try { window.dispatchEvent(new CustomEvent(name, { detail: detail })); }
    catch (_) { return; }
  }

  function update() {
    state.raf = 0;
    var size = viewport();
    var mode = modeFor(size.width);
    var orientation = size.width >= size.height ? "landscape" : "portrait";
    var motion = motionFor();

    root.style.setProperty("--szl-proof-vw", (size.width / 100).toFixed(3) + "px");
    root.style.setProperty("--szl-proof-vh", (size.height / 100).toFixed(3) + "px");
    root.dataset.szlProofAdaptiveV3 = "ready";
    root.dataset.szlProofDisplayMode = mode;
    root.dataset.szlProofOrientation = orientation;
    root.dataset.szlProofMotion = motion;

    if (mode !== state.mode || orientation !== state.orientation || motion !== state.motion) {
      state.mode = mode;
      state.orientation = orientation;
      state.motion = motion;
      emit("szl:proof-displaymode", { mode: mode, orientation: orientation, motion: motion, width: size.width, height: size.height });
    }
  }

  function schedule() {
    if (state.raf) return;
    state.raf = window.requestAnimationFrame(update);
  }

  function visible(element) {
    var style = window.getComputedStyle(element);
    var rect = element.getBoundingClientRect();
    return style.display !== "none" && style.visibility !== "hidden" && rect.width > 0 && rect.height > 0;
  }

  function wrapEvidenceTables() {
    document.querySelectorAll("table").forEach(function (table) {
      if (table.parentElement && table.parentElement.matches(".szl-proof-table-wrap,[data-szl-proof-scrollable='table']")) return;
      var wrapper = document.createElement("div");
      wrapper.className = "szl-proof-table-wrap";
      wrapper.dataset.szlProofScrollable = "table";
      wrapper.tabIndex = 0;
      wrapper.setAttribute("role", "region");
      wrapper.setAttribute("aria-label", table.getAttribute("aria-label") || "Scrollable evidence table");
      table.parentNode.insertBefore(wrapper, table);
      wrapper.appendChild(table);
    });

    document.querySelectorAll("pre").forEach(function (pre) {
      pre.dataset.szlProofScrollable = "code";
      if (!pre.hasAttribute("tabindex")) pre.tabIndex = 0;
      if (!pre.hasAttribute("aria-label")) pre.setAttribute("aria-label", "Scrollable evidence record");
    });
  }

  function installObserver() {
    if (!("IntersectionObserver" in window) || reduced.matches) return;
    var panels = Array.prototype.slice.call(document.querySelectorAll(
      ".szl-proof-card,.szl-proof-panel,.record-card,.diligence-card,[data-szl-proof-panel],main > section"
    )).filter(visible).slice(0, 40);
    if (!panels.length) return;

    state.observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        entry.target.dataset.szlProofInview = entry.isIntersecting ? "true" : "false";
        if (entry.isIntersecting) state.observer.unobserve(entry.target);
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });

    panels.forEach(function (panel) {
      panel.classList.add("szl-proof-adaptive-enter");
      panel.dataset.szlProofInview = "false";
      state.observer.observe(panel);
    });
  }

  function anchorNavigation(event) {
    var anchor = event.target.closest && event.target.closest("a[href^='#']");
    if (!anchor) return;
    var href = anchor.getAttribute("href");
    if (!href || href === "#") return;
    var target;
    try { target = document.querySelector(href); }
    catch (_) { return; }
    if (!target) return;
    event.preventDefault();
    target.scrollIntoView({ behavior: reduced.matches ? "auto" : "smooth", block: "start" });
    if (!target.hasAttribute("tabindex")) target.setAttribute("tabindex", "-1");
    target.focus({ preventScroll: true });
    history.replaceState(null, "", href);
  }

  function maintainFocus() {
    document.addEventListener("focusin", function (event) {
      var target = event.target;
      if (!(target instanceof HTMLElement)) return;
      window.requestAnimationFrame(function () {
        var rect = target.getBoundingClientRect();
        if (rect.top < 16 || rect.bottom > window.innerHeight - 16) {
          target.scrollIntoView({ block: "nearest", inline: "nearest", behavior: "auto" });
        }
      });
    });
  }

  function start() {
    if (!document.body) return;
    update();
    wrapEvidenceTables();
    installObserver();
    maintainFocus();

    window.addEventListener("resize", schedule, { passive: true });
    window.addEventListener("orientationchange", schedule, { passive: true });
    if (window.visualViewport) {
      window.visualViewport.addEventListener("resize", schedule, { passive: true });
      window.visualViewport.addEventListener("scroll", schedule, { passive: true });
    }
    [reduced, coarse].forEach(function (query) {
      if (query.addEventListener) query.addEventListener("change", schedule);
      else if (query.addListener) query.addListener(schedule);
    });
    document.addEventListener("click", anchorNavigation);

    emit("szl:proof-adaptive-ready", { version: "3.0.0", mode: state.mode, orientation: state.orientation, motion: state.motion });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
}());
