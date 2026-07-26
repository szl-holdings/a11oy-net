// SPDX-License-Identifier: Apache-2.0
// Shared public-atlas admission policy for the browser and the Node contract.
(function (root, factory) {
  "use strict";
  var policy = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = policy;
  }
  root.A11oyAtlasPolicy = policy;
}(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  var OWNER_PREFIX = "SZLHOLDINGS/";
  var PUBLIC_ARTIFACT_TYPES = Object.freeze({
    "MODEL": true,
    "DATASET": true,
    "COLLECTION": true,
    "BUCKET": true
  });

  var DECISIONS = Object.freeze({
    REPORTED: Object.freeze({
      allowed: true,
      label: "REPORTED",
      reason: "PUBLIC_HUB_LISTING"
    }),
    EXCLUDED_FAMILY: Object.freeze({
      allowed: false,
      label: "EXCLUDED",
      reason: "EXCLUDED_PRODUCT_FAMILY"
    }),
    INTERACTIVE_RUNTIME: Object.freeze({
      allowed: false,
      label: "EXCLUDED",
      reason: "INTERACTIVE_RUNTIME_SURFACE"
    }),
    OUT_OF_SCOPE: Object.freeze({
      allowed: false,
      label: "EXCLUDED",
      reason: "OUT_OF_SCOPE_OWNER"
    }),
    UNSUPPORTED: Object.freeze({
      allowed: false,
      label: "EXCLUDED",
      reason: "UNSUPPORTED_RESOURCE_TYPE"
    })
  });

  function classify(type, id) {
    var normalizedType = String(type || "").toUpperCase();
    var normalizedId = String(id || "");
    var ownerMatches = normalizedId.toUpperCase().indexOf(OWNER_PREFIX) === 0;
    if (!ownerMatches) return DECISIONS.OUT_OF_SCOPE;

    var resourceName = normalizedId.slice(OWNER_PREFIX.length).toLowerCase();
    if (resourceName.indexOf("killinchu") !== -1) {
      return DECISIONS.EXCLUDED_FAMILY;
    }
    if (normalizedType === "SPACE") return DECISIONS.INTERACTIVE_RUNTIME;
    if (PUBLIC_ARTIFACT_TYPES[normalizedType] !== true) return DECISIONS.UNSUPPORTED;
    return DECISIONS.REPORTED;
  }

  function allows(type, id) {
    return classify(type, id).allowed;
  }

  function select(type, items) {
    if (!Array.isArray(items)) return [];
    return items.filter(function (item) {
      var id = String((item && (item.id || item.slug)) || "");
      return allows(type, id);
    });
  }

  return Object.freeze({
    classify: classify,
    allows: allows,
    select: select,
    artifactTypes: Object.freeze(Object.keys(PUBLIC_ARTIFACT_TYPES)),
    excludedTypes: Object.freeze(["SPACE"]),
    excludedNameFragments: Object.freeze(["killinchu"])
  });
}));
