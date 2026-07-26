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

  var EXCLUDED = Object.freeze({
    "SPACE:SZLHOLDINGS/killinchu": true
  });

  function allows(type, id) {
    var normalizedType = String(type || "").toUpperCase();
    var normalizedId = String(id || "");
    return normalizedId.indexOf("SZLHOLDINGS/") === 0
      && EXCLUDED[normalizedType + ":" + normalizedId] !== true;
  }

  return Object.freeze({
    allows: allows,
    excluded: Object.freeze(Object.keys(EXCLUDED))
  });
}));
