// SPDX-License-Identifier: Apache-2.0
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const policy = require("./atlas_policy.js");

assert.equal(policy.allows("SPACE", "SZLHOLDINGS/killinchu"), false);
assert.equal(policy.allows("DATASET", "SZLHOLDINGS/killinchu-osint-corpus"), false);
assert.equal(policy.allows("SPACE", "SZLHOLDINGS/a11oy"), false);
assert.equal(policy.allows("SPACE", "SZLHOLDINGS/public-precision-action"), false);
assert.equal(policy.allows("MODEL", "SZLHOLDINGS/szl-governed-norm"), true);
assert.equal(policy.allows("DATASET", "SZLHOLDINGS/uds-spans-receipts"), true);
assert.equal(policy.allows("COLLECTION", "SZLHOLDINGS/evidence-collection"), true);
assert.equal(policy.allows("BUCKET", "SZLHOLDINGS/public-bucket"), true);
assert.equal(policy.allows("ACTION", "SZLHOLDINGS/public-action"), false);
assert.equal(policy.allows("SPACE", "another-owner/a11oy"), false);
assert.equal(policy.allows("SPACE", ""), false);
assert.deepEqual(policy.classify("SPACE", "SZLHOLDINGS/killinchu"), {
  allowed: false,
  label: "EXCLUDED",
  reason: "EXCLUDED_PRODUCT_FAMILY",
});
assert.deepEqual(policy.classify("SPACE", "SZLHOLDINGS/public-precision-action"), {
  allowed: false,
  label: "EXCLUDED",
  reason: "INTERACTIVE_RUNTIME_SURFACE",
});
assert.deepEqual(policy.classify("MODEL", "SZLHOLDINGS/szl-governed-norm"), {
  allowed: true,
  label: "REPORTED",
  reason: "PUBLIC_HUB_LISTING",
});
assert.deepEqual(
  policy.classify(
    "COLLECTION",
    "SZLHOLDINGS/evidence-collection",
    "Killinchu renamed collection",
  ),
  {
    allowed: false,
    label: "EXCLUDED",
    reason: "EXCLUDED_PRODUCT_FAMILY",
  },
);

const generatedFixture = [
  {
    type: "SPACE",
    items: [
      { id: "SZLHOLDINGS/killinchu" },
      { id: "SZLHOLDINGS/public-precision-action" },
      { id: "SZLHOLDINGS/a11oy" },
    ],
  },
  {
    type: "DATASET",
    items: [
      { id: "SZLHOLDINGS/killinchu-osint-corpus" },
      { id: "SZLHOLDINGS/uds-spans-receipts" },
    ],
  },
  {
    type: "COLLECTION",
    items: [
      {
        id: "SZLHOLDINGS/evidence-collection",
        title: "Killinchu renamed collection",
      },
      {
        id: "SZLHOLDINGS/governed-artifacts",
        title: "Governed artifacts",
      },
    ],
  },
  {
    type: "MODEL",
    items: [{ id: "SZLHOLDINGS/szl-governed-norm" }],
  },
];

const generatedCards = generatedFixture.flatMap(({ type, items }) =>
  policy.select(type, items).map((item) => {
    const decision = policy.classify(type, item.id, item.title);
    return { type, id: item.id, label: decision.label };
  }),
);

assert.deepEqual(generatedCards, [
  {
    type: "DATASET",
    id: "SZLHOLDINGS/uds-spans-receipts",
    label: "REPORTED",
  },
  {
    type: "COLLECTION",
    id: "SZLHOLDINGS/governed-artifacts",
    label: "REPORTED",
  },
  {
    type: "MODEL",
    id: "SZLHOLDINGS/szl-governed-norm",
    label: "REPORTED",
  },
]);
assert.equal(generatedCards.some(({ type }) => type === "SPACE"), false);
assert.equal(
  generatedCards.some(({ id }) => id.toLowerCase().includes("killinchu")),
  false,
);

console.log(
  "OK: generated atlas cards contain reported public artifacts only; " +
    "Killinchu-named resources and interactive Spaces are excluded.",
);
