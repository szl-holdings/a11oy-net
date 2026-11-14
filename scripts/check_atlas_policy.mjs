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
const CARD_IDS = [
  "inventory-cards", "invSnapshotState", "invProvenance", "invTotal",
  "invModels", "invKernels", "invDatasets", "invSpaces", "invCollections", "invBuckets",
];
const cardsSource = readFileSync(new URL("inventory_cards.js", import.meta.url), "utf8");

function descendants(node) {
  return [node, ...node.children.flatMap(descendants)];
}

async function renderCards(snapshot, now, models = {}) {
  const ids = new Map(CARD_IDS.map(id => [id, element("div")]));
  const reads = [];
  runInNewContext(cardsSource, {
    document: { getElementById: id => ids.get(id), createElement: element },
    Date: class extends Date { static now() { return Date.parse(now); } },
    fetch: async (url, options) => {
      reads.push(url);
      assert.equal(options.credentials, "omit");
      assert.equal(options.redirect, "error");
      assert.equal(options.cache, "no-store");
      assert.ok(["/public-inventory.json", "/models.json"].includes(url));
      if (url !== "/public-inventory.json") return { ok: true, json: async () => models };
      if (snapshot === null) throw new Error("UNAVAILABLE");
      return { ok: true, json: async () => snapshot };
    },
  }, { timeout: 1000 });
  await new Promise(resolve => setImmediate(resolve));
  return { ids, reads };
}

const ident = "SZLHOLDINGS/shared-name";
const privateIdent = "SZLHOLDINGS/not-disclosed";
const snapshot = {
  schema: "szl.public-hf-inventory/v4",
  observed_at: "2026-10-01T12:00:00Z",
  observation_mode: "UNAUTHENTICATED_PUBLIC_API_SNAPSHOT",
  counts: { public_resources_total: 4, models: 1, datasets: 1, spaces: 1, collections: 0, buckets: 1 },
  resources: {
    models: [{ id: ident }, { id: privateIdent, private: true }],
    datasets: [{ id: ident, source_observation: "PUBLIC_HF_REPOSITORY_OBSERVED" }],
    spaces: [{ id: ident, sdk: "static", runtime: { stage: "RUNNING" } }],
    buckets: [{ id: ident, visibility: "public", observed_object_count: 2 }],
  },
};
const { ids, reads } = await renderCards(snapshot, "2026-10-04T12:00:00Z");
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
assert.equal(JSON.stringify(descendants(ids.get("inventory-cards"))).includes(privateIdent), false);
assert.deepEqual(reads, ["/public-inventory.json", "/models.json"]);
assert.equal(ids.get("invSnapshotState").dataset.state, "partial");
assert.match(ids.get("invSnapshotState").textContent, /^STALE · 2026-10-01/);
assert.equal(ids.get("invTotal").textContent, "4");
assert.equal(ids.get("invKernels").textContent, "—");
assert.equal(ids.get("invBuckets").textContent, "1");
assert.match(ids.get("invProvenance").textContent, /observed 2026-10-01T12:00:00Z/);
assert.match(ids.get("invProvenance").textContent, /kernel scope UNAVAILABLE/);
assert.match(ids.get("invProvenance").textContent, /github alignment UNAVAILABLE/);

const fresh = await renderCards(
  { ...snapshot, observed_at: "2026-10-01T12:00:00Z" },
  "2026-10-02T12:00:00Z",
);
assert.equal(fresh.ids.get("invSnapshotState").dataset.state, "snapshot");
const stale = await renderCards(snapshot, "2026-10-02T12:00:00.001Z");
assert.equal(stale.ids.get("invSnapshotState").dataset.state, "partial");
assert.match(stale.ids.get("invSnapshotState").textContent, /^STALE · /);

const undated = await renderCards({ ...snapshot, observed_at: "2026-02-30T00:00:00Z" }, "2026-10-04T12:00:00Z");
assert.equal(undated.ids.get("invSnapshotState").dataset.state, "unavailable");
assert.match(undated.ids.get("invSnapshotState").textContent, /DATE UNAVAILABLE/);
assert.equal(undated.ids.get("invModels").textContent, "1");
assert.notEqual(undated.ids.get("invModels").textContent, "0");

const future = await renderCards({ ...snapshot, observed_at: "2026-10-05T12:00:00Z" }, "2026-10-04T12:00:00Z");
assert.equal(future.ids.get("invSnapshotState").dataset.state, "unavailable");
assert.match(future.ids.get("invSnapshotState").textContent, /DATE UNAVAILABLE/);

const scoped = await renderCards({
  ...snapshot,
  observed_at: "2026-10-03T12:00:00Z",
  counts: { ...snapshot.counts, kernels: 2 },
  claim_boundaries: {
    kernel_membership: "SEPARATE_NATIVE_NAMESPACE_COUNTED_ONCE_PER_KIND_AND_ID",
    github_alignment: "EXACT_IMMUTABLE_MANIFEST_MEMBERSHIP_ONLY_NOT_RUNTIME_PARITY",
  },
}, "2026-10-04T12:00:00Z");
assert.equal(scoped.ids.get("invKernels").textContent, "2");
assert.equal(scoped.ids.get("invSnapshotState").dataset.state, "snapshot");
assert.match(scoped.ids.get("invProvenance").textContent, /kernel scope SEPARATE_NATIVE_NAMESPACE_COUNTED_ONCE_PER_KIND_AND_ID/);
assert.match(scoped.ids.get("invProvenance").textContent, /github alignment EXACT_IMMUTABLE_MANIFEST_MEMBERSHIP_ONLY_NOT_RUNTIME_PARITY/);
assert.equal(scoped.ids.get("invProvenance").textContent.includes(privateIdent), false);

const unread = await renderCards(null, "2026-10-04T12:00:00Z");
for (const id of ["invTotal", "invModels", "invKernels", "invDatasets", "invSpaces", "invCollections", "invBuckets"]) {
  assert.equal(unread.ids.get(id).textContent, "—", id);
  assert.notEqual(unread.ids.get(id).textContent, "0", id);
}
assert.equal(unread.ids.get("invSnapshotState").dataset.state, "unavailable");
assert.match(unread.ids.get("invSnapshotState").textContent, /UNAVAILABLE/);

console.log(
  "OK: generated atlas cards contain reported public artifacts only; " +
    "Killinchu-named resources and interactive Spaces are excluded. " +
    "Snapshot cards preserve per-kind Hub URLs and dated evidence labels.",
);
