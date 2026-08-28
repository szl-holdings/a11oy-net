// SPDX-License-Identifier: Apache-2.0
// Shared fail-closed kernel-chip bind: paint locked-proven only from
// https://a-11-oy.com/api/a11oy/v1/honest locked_formula_count.
// Render the observed integer only when that field is the locked kernel
// count (eight); else N/A. Fetch/parse/binding failure → UNAVAILABLE.
// Never default the painted count.
// Catalog LOCKED-PROVEN=25 is a separately labelled genome catalog count.
// Lean-8 ≠ genome-144. Λ stays Conjecture 1.
(function (root, factory) {
  "use strict";
  var policy = factory(root);
  if (typeof module === "object" && module.exports) {
    module.exports = policy;
  }
  root.A11oyHonestKernelBind = policy;
}(typeof globalThis !== "undefined" ? globalThis : this, function (root) {
  "use strict";

  var HONEST_URL = "https://a-11-oy.com/api/a11oy/v1/honest";
  var HONEST_FIELD = "locked_formula_count";
  var FETCH_MS = 8000;
  var NA = "N/A";
  var UNAVAILABLE = "UNAVAILABLE";

  function lockedFormulaCountFromHonest(payload) {
    if (!payload || typeof payload !== "object") {
      return null;
    }
    var value = payload[HONEST_FIELD];
    var lock = payload.doctrine_lock;
    if (value == null && lock && typeof lock === "object") {
      value = lock[HONEST_FIELD];
    }
    if (typeof value !== "number" || !isFinite(value) || Math.floor(value) !== value) {
      return null;
    }
    return value;
  }

  function lockedFormulaIdsFromHonest(payload) {
    if (!payload || typeof payload !== "object") {
      return [];
    }
    var ids = payload.locked_formula_ids;
    var lock = payload.doctrine_lock;
    if (!Array.isArray(ids) && lock && typeof lock === "object") {
      ids = lock.locked_formula_ids;
    }
    if (!Array.isArray(ids)) {
      return [];
    }
    return ids.filter(function (id) {
      return typeof id === "string" && id.trim() !== "";
    });
  }

  function isExactLockedKernelCount(value) {
    return value === 8;
  }

  function kernelCountLabel(value) {
    return isExactLockedKernelCount(value) ? String(value) : NA;
  }

  function classifyHonestPayload(payload) {
    var count = lockedFormulaCountFromHonest(payload);
    if (isExactLockedKernelCount(count)) {
      return Object.freeze({
        state: "observed",
        label: String(count),
        count: count,
        ids: Object.freeze(lockedFormulaIdsFromHonest(payload)),
        reason: "HONEST_LOCKED_FORMULA_COUNT"
      });
    }
    return Object.freeze({
      state: "unavailable",
      label: NA,
      count: null,
      ids: Object.freeze([]),
      reason: "LOCKED_FORMULA_COUNT_NOT_EXACT"
    });
  }

  function classifyFetchFailure(reason) {
    return Object.freeze({
      state: "unavailable",
      label: UNAVAILABLE,
      count: null,
      ids: Object.freeze([]),
      reason: reason || "HONEST_REQUEST_FAILED"
    });
  }

  function canonicalHttpsUrl(value) {
    if (typeof value !== "string" || value !== value.trim() || value === "") {
      throw new TypeError("URL must be a non-empty canonical string");
    }
    var parsed = new URL(value);
    if (
      parsed.protocol !== "https:" ||
      parsed.username !== "" ||
      parsed.password !== "" ||
      parsed.hash !== ""
    ) {
      throw new TypeError("URL must be credential-free HTTPS without a fragment");
    }
    return parsed.href;
  }

  function isExactResponseFor(response, requestedUrl, probePolicy) {
    if (probePolicy && typeof probePolicy.isExactResponseFor === "function") {
      return probePolicy.isExactResponseFor(response, requestedUrl);
    }
    if (
      !response ||
      typeof response !== "object" ||
      response.redirected !== false ||
      typeof response.url !== "string"
    ) {
      return false;
    }
    try {
      return canonicalHttpsUrl(response.url) === canonicalHttpsUrl(requestedUrl);
    } catch (_error) {
      return false;
    }
  }

  function fetchHonestManifest(options) {
    var opts = options || {};
    var url = opts.url || HONEST_URL;
    var fetchFn = opts.fetch;
    var probePolicy = opts.probePolicy;
    if (typeof fetchFn !== "function") {
      return Promise.resolve(classifyFetchFailure("FETCH_UNAVAILABLE"));
    }
    var controller = typeof AbortController === "function" ? new AbortController() : null;
    var timer = setTimeout(function () {
      if (controller) {
        controller.abort();
      }
    }, FETCH_MS);
    var request = { cache: "no-store", redirect: "error", mode: "cors", credentials: "omit" };
    if (controller) {
      request.signal = controller.signal;
    }
    return fetchFn(url, request)
      .then(function (response) {
        if (!isExactResponseFor(response, url, probePolicy)) {
          throw new Error("SOURCE_BINDING_MISMATCH");
        }
        if (!response || response.ok !== true) {
          throw new Error("HTTP_FAILURE");
        }
        return response.json();
      })
      .then(function (payload) {
        return classifyHonestPayload(payload);
      })
      .catch(function () {
        return classifyFetchFailure("HONEST_REQUEST_FAILED");
      })
      .finally(function () {
        clearTimeout(timer);
      });
  }

  function countNode(chip) {
    if (!chip) {
      return null;
    }
    return chip.querySelector("[data-kernel-count]") || chip.querySelector("b") || chip;
  }

  function idsNode(chip) {
    if (!chip) {
      return null;
    }
    return chip.querySelector("[data-kernel-ids]");
  }

  function paintChip(chip, observation) {
    if (!chip || !observation) {
      return;
    }
    var node = countNode(chip);
    if (node) {
      node.textContent = observation.label;
    }
    chip.dataset.state = observation.state;
    var ids = idsNode(chip);
    if (ids) {
      ids.textContent = observation.state === "observed" && observation.ids && observation.ids.length
        ? " {" + observation.ids.join(", ") + "}"
        : "";
    }
  }

  function collectChips(doc) {
    var found = [];
    function add(el) {
      if (!el || found.indexOf(el) !== -1) {
        return;
      }
      found.push(el);
    }
    if (!doc || typeof doc.querySelectorAll !== "function") {
      return found;
    }
    Array.prototype.forEach.call(doc.querySelectorAll("[data-kernel-chip]"), add);
    ["cnt-locked", "pt-locked", "hs-proven"].forEach(function (id) {
      var el = typeof doc.getElementById === "function" ? doc.getElementById(id) : null;
      if (!el) {
        return;
      }
      add(el.closest ? el.closest("[data-kernel-chip]") || el : el);
    });
    return found;
  }

  function bindDocument(doc, options) {
    var chips = collectChips(doc);
    if (!chips.length) {
      return Promise.resolve(classifyFetchFailure("NO_KERNEL_CHIPS"));
    }
    var opts = options || {};
    if (!opts.url) {
      opts = {
        url: HONEST_URL,
        fetch: opts.fetch,
        probePolicy: opts.probePolicy
      };
    }
    return fetchHonestManifest(opts).then(function (observation) {
      chips.forEach(function (chip) {
        paintChip(chip, observation);
      });
      return observation;
    });
  }

  function autoBind(doc) {
    var globalProbe = root && root.A11oyProbePolicy;
    var fetchFn = typeof fetch === "function" ? fetch : null;
    return bindDocument(doc, {
      url: HONEST_URL,
      fetch: fetchFn,
      probePolicy: globalProbe
    });
  }

  if (typeof document !== "undefined") {
    var start = function () {
      try {
        autoBind(document);
      } catch (_error) {
        // Fail closed: never invent 8 if the binder throws.
      }
    };
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", start);
    } else {
      start();
    }
  }

  return Object.freeze({
    HONEST_URL: HONEST_URL,
    HONEST_FIELD: HONEST_FIELD,
    lockedFormulaCountFromHonest: lockedFormulaCountFromHonest,
    lockedFormulaIdsFromHonest: lockedFormulaIdsFromHonest,
    isExactLockedKernelCount: isExactLockedKernelCount,
    kernelCountLabel: kernelCountLabel,
    classifyHonestPayload: classifyHonestPayload,
    classifyFetchFailure: classifyFetchFailure,
    fetchHonestManifest: fetchHonestManifest,
    paintChip: paintChip,
    collectChips: collectChips,
    bindDocument: bindDocument
  });
}));
