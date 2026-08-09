// SPDX-License-Identifier: Apache-2.0
// Shared fail-closed browser-observation policy for the proof surface and Node tests.
(function (root, factory) {
  "use strict";
  var policy = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = policy;
  }
  root.A11oyProbePolicy = policy;
}(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  var TERMINAL_UNAVAILABLE_STAGES = Object.freeze({
    BUILD_ERROR: true,
    CONFIG_ERROR: true,
    ERROR: true,
    PAUSED: true,
    RUNTIME_ERROR: true,
    STOPPED: true
  });
  var TRANSITIONAL_STAGES = Object.freeze({
    BUILDING: true,
    RESTARTING: true,
    SLEEPING: true,
    STARTING: true,
    STOPPING: true
  });

  function result(state, tone, label, reason) {
    return Object.freeze({
      state: state,
      tone: tone,
      label: label,
      reason: reason,
      positive: state === "observed"
    });
  }

  function unavailable(reason, label) {
    return result(
      "unavailable",
      "down",
      label || "UNAVAILABLE",
      reason || "SOURCE_UNAVAILABLE"
    );
  }

  function unverified(reason, label) {
    return result(
      "unverified",
      "warn",
      label || "UNVERIFIED",
      reason || "EVIDENCE_INSUFFICIENT"
    );
  }

  function classifyHttpResponse(response) {
    if (!response || typeof response !== "object") {
      return unavailable("MALFORMED_RESPONSE");
    }
    var type = typeof response.type === "string"
      ? response.type.toLowerCase()
      : "";
    if (type === "opaque" || type === "opaqueredirect") {
      return unverified("STATUS_HIDDEN_BY_BROWSER");
    }
    if (
      typeof response.status !== "number" ||
      !Number.isInteger(response.status) ||
      typeof response.ok !== "boolean"
    ) {
      return unavailable("MALFORMED_RESPONSE");
    }
    if (response.status === 0) {
      return unverified("STATUS_HIDDEN_BY_BROWSER");
    }
    if (response.ok && response.status >= 200 && response.status < 300) {
      return result(
        "observed",
        "ok",
        "HTTP " + response.status + " · OBSERVED",
        "VISIBLE_HTTP_SUCCESS"
      );
    }
    return unavailable(
      "VISIBLE_HTTP_FAILURE",
      "HTTP " + response.status + " · UNAVAILABLE"
    );
  }

  function classifySpaceMetadata(metadata) {
    if (
      !metadata ||
      typeof metadata !== "object" ||
      !metadata.runtime ||
      typeof metadata.runtime !== "object" ||
      typeof metadata.runtime.stage !== "string" ||
      metadata.runtime.stage.trim() === ""
    ) {
      return unavailable("MALFORMED_SPACE_METADATA");
    }

    var stage = metadata.runtime.stage.trim().toUpperCase();
    if (stage === "RUNNING") {
      return result(
        "observed",
        "ok",
        "RUNNING · REPORTED",
        "SCHEMA_VALID_HUB_STAGE"
      );
    }
    if (TERMINAL_UNAVAILABLE_STAGES[stage] === true) {
      return unavailable("HUB_STAGE_UNAVAILABLE", stage + " · REPORTED");
    }
    if (TRANSITIONAL_STAGES[stage] === true) {
      return unverified("HUB_STAGE_TRANSITIONAL", stage + " · REPORTED");
    }
    return unverified("HUB_STAGE_UNRECOGNIZED", stage + " · REPORTED");
  }

  function classifyFailure(kind) {
    var normalized = typeof kind === "string" && kind.trim()
      ? kind.trim().toUpperCase()
      : "SOURCE_UNAVAILABLE";
    return unavailable(normalized);
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

  function isExactResponseFor(response, requestedUrl) {
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

  return Object.freeze({
    classifyHttpResponse: classifyHttpResponse,
    classifySpaceMetadata: classifySpaceMetadata,
    classifyFailure: classifyFailure,
    isExactResponseFor: isExactResponseFor,
    states: Object.freeze(["observed", "unverified", "unavailable"])
  });
}));
