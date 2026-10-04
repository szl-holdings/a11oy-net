// SPDX-License-Identifier: Apache-2.0
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { runInNewContext } from "node:vm";

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

// Exercise the shipped snapshot-card renderer, including its distinct Space
// inventory scope. Identical repository IDs in different Hub kinds must still
// open the right public namespace; a bucket is not a model repository.
function element(tagName) {
  return {
    tagName,
    children: [],
    dataset: {},
    textContent: "",
    appendChild(child) { this.children.push(child); return child; },
    setAttribute() {},
    addEventListener() {},
  };
}
const ids = new Map([
  "inventory-cards", "invSnapshotState", "invProvenance", "invTotal",
  "invModels", "invDatasets", "invSpaces", "invCollections", "invBuckets",
].map(id => [id, element("div")]));
const ident = "SZLHOLDINGS/shared-name";
const snapshot = {
  schema: "szl.public-hf-inventory/v4",
  observed_at: "2026-10-01T12:00:00Z",
  observation_mode: "UNAUTHENTICATED_PUBLIC_API_SNAPSHOT",
  counts: { public_resources_total: 4, models: 1, datasets: 1, spaces: 1, collections: 0, buckets: 1 },
  resources: {
    models: [{ id: ident }],
    datasets: [{ id: ident, source_observation: "PUBLIC_HF_REPOSITORY_OBSERVED" }],
    spaces: [{ id: ident, sdk: "static", runtime: { stage: "RUNNING" } }],
    buckets: [{ id: ident, visibility: "public", observed_object_count: 2 }],
  },
};
const reads = [];
runInNewContext(
  readFileSync(new URL("inventory_cards.js", import.meta.url), "utf8"),
  {
    document: { getElementById: id => ids.get(id), createElement: element },
    Date: class extends Date { static now() { return Date.parse("2026-10-04T12:00:00Z"); } },
    fetch: async (url, options) => {
      reads.push(url);
      assert.equal(options.credentials, "omit");
      assert.equal(options.redirect, "error");
      assert.equal(options.cache, "no-store");
      assert.ok(["/public-inventory.json", "/models.json"].includes(url));
      return { ok: true, json: async () => url === "/public-inventory.json" ? snapshot : {} };
    },
  },
  { timeout: 1000 },
);
await new Promise(resolve => setImmediate(resolve));
function descendants(node) {
  return [node, ...node.children.flatMap(descendants)];
}
const rendered = descendants(ids.get("inventory-cards"))
  .filter(node => node.className === "inv-card");
assert.deepEqual(rendered.map(node => ({
  kind: node.children[0].textContent.split(" · ")[0],
  href: node.href,
})), [
  { kind: "MODEL", href: `https://huggingface.co/${ident}` },
  { kind: "DATASET", href: `https://huggingface.co/datasets/${ident}` },
  { kind: "SPACE", href: `https://huggingface.co/spaces/${ident}` },
  { kind: "BUCKET", href: `https://huggingface.co/buckets/${ident}` },
]);
assert.deepEqual(reads, ["/public-inventory.json", "/models.json"]);
assert.equal(ids.get("invSnapshotState").dataset.state, "partial");
assert.match(ids.get("invSnapshotState").textContent, /^STALE · 2026-10-01/);
assert.equal(ids.get("invTotal").textContent, "4");
assert.equal(ids.get("invBuckets").textContent, "1");
assert.match(ids.get("invProvenance").textContent, /observed 2026-10-01T12:00:00Z/);

console.log(
  "OK: generated atlas cards contain reported public artifacts only; " +
    "Killinchu-named resources and interactive Spaces are excluded. " +
    "Snapshot cards preserve per-kind Hub URLs and dated evidence labels.",
);
