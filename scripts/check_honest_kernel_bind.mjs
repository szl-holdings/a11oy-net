// SPDX-License-Identifier: Apache-2.0
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const policy = require("./honest_kernel_bind.js");

assert.equal(policy.HONEST_URL, "https://a-11-oy.com/api/a11oy/v1/honest");
assert.equal(policy.HONEST_FIELD, "locked_formula_count");

assert.equal(policy.lockedFormulaCountFromHonest({ locked_formula_count: 8 }), 8);
assert.equal(
  policy.lockedFormulaCountFromHonest({
    doctrine_lock: { locked_formula_count: 8 },
  }),
  8,
);
assert.equal(policy.lockedFormulaCountFromHonest({ kernel_commit: "c7c0ba17" }), null);
assert.equal(policy.lockedFormulaCountFromHonest({ locked_formula_count: 25 }), 25);
assert.equal(policy.lockedFormulaCountFromHonest({ locked_formula_count: "8" }), null);
assert.equal(policy.lockedFormulaCountFromHonest(null), null);

assert.equal(policy.isExactLockedKernelCount(8), true);
assert.equal(policy.isExactLockedKernelCount(7), false);
assert.equal(policy.isExactLockedKernelCount(25), false);
assert.equal(policy.isExactLockedKernelCount(null), false);

assert.equal(policy.kernelCountLabel(8), "8");
assert.equal(policy.kernelCountLabel(7), "N/A");
assert.equal(policy.kernelCountLabel(25), "N/A");
assert.equal(policy.kernelCountLabel(144), "N/A");
assert.equal(policy.kernelCountLabel(null), "N/A");

const observed = policy.classifyHonestPayload({
  doctrine_lock: {
    locked_formula_count: 8,
    locked_formula_ids: ["F1", "F4", "F7", "F11", "F12", "F18", "F19", "F22"],
  },
});
assert.equal(observed.state, "observed");
assert.equal(observed.label, "8");
assert.equal(observed.count, 8);
assert.deepEqual(observed.ids, [
  "F1",
  "F4",
  "F7",
  "F11",
  "F12",
  "F18",
  "F19",
  "F22",
]);

const genome = policy.classifyHonestPayload({ locked_formula_count: 25 });
assert.equal(genome.state, "unavailable");
assert.equal(genome.label, "N/A");
assert.equal(genome.count, null);

const missing = policy.classifyHonestPayload({ footer: "Doctrine v11" });
assert.equal(missing.label, "N/A");

const failed = policy.classifyFetchFailure("HONEST_REQUEST_FAILED");
assert.equal(failed.label, "UNAVAILABLE");
assert.equal(failed.state, "unavailable");
assert.equal(failed.count, null);

function jsonResponse(payload, url) {
  return {
    ok: true,
    redirected: false,
    url: url || policy.HONEST_URL,
    json: async () => payload,
  };
}

const liveEight = await policy.fetchHonestManifest({
  url: policy.HONEST_URL,
  fetch: async (url) => {
    assert.equal(url, policy.HONEST_URL);
    return jsonResponse({ locked_formula_count: 8 });
  },
});
assert.equal(liveEight.label, "8");
assert.equal(liveEight.count, 8);

const liveWrong = await policy.fetchHonestManifest({
  fetch: async () => jsonResponse({ locked_formula_count: 25 }),
});
assert.equal(liveWrong.label, "N/A");

const liveFail = await policy.fetchHonestManifest({
  fetch: async () => {
    throw new Error("network");
  },
});
assert.equal(liveFail.label, "UNAVAILABLE");

const httpFail = await policy.fetchHonestManifest({
  fetch: async () => ({
    ok: false,
    redirected: false,
    url: policy.HONEST_URL,
    json: async () => ({ locked_formula_count: 8 }),
  }),
});
assert.equal(httpFail.label, "UNAVAILABLE");

const redirectFail = await policy.fetchHonestManifest({
  fetch: async () => ({
    ok: true,
    redirected: true,
    url: policy.HONEST_URL,
    json: async () => ({ locked_formula_count: 8 }),
  }),
});
assert.equal(redirectFail.label, "UNAVAILABLE");

const noFetch = await policy.fetchHonestManifest({});
assert.equal(noFetch.label, "UNAVAILABLE");

function chip(id) {
  const count = { textContent: "N/A", nodeType: 1 };
  const ids = { textContent: "", nodeType: 1 };
  const el = {
    id,
    dataset: { kernelChip: "locked-proven", state: "unavailable" },
    querySelector(selector) {
      if (selector === "[data-kernel-count]" || selector === "b") return count;
      if (selector === "[data-kernel-ids]") return ids;
      return null;
    },
    closest() {
      return el;
    },
    _count: count,
    _ids: ids,
  };
  return el;
}

const hero = chip("cnt-locked");
policy.paintChip(hero, observed);
assert.equal(hero._count.textContent, "8");
assert.equal(hero.dataset.state, "observed");
assert.equal(hero._ids.textContent, " {F1, F4, F7, F11, F12, F18, F19, F22}");

policy.paintChip(hero, genome);
assert.equal(hero._count.textContent, "N/A");
assert.equal(hero.dataset.state, "unavailable");
assert.equal(hero._ids.textContent, "");

policy.paintChip(hero, failed);
assert.equal(hero._count.textContent, "UNAVAILABLE");

const source = require("node:fs").readFileSync(
  new URL("./honest_kernel_bind.js", import.meta.url),
  "utf8",
);
assert.doesNotMatch(source, /\?\?\s*8\b/);
assert.doesNotMatch(source, /\|\|\s*8\b/);
assert.doesNotMatch(source, /exactly\s+8/i);
assert.match(source, /\/api\/a11oy\/v1\/honest/);
assert.match(source, /locked_formula_count/);
assert.match(source, /value === 8/);
assert.match(source, /N\/A/);
assert.match(source, /factory\(root\)/);
assert.match(source, /function \(root\)/);
assert.match(source, /mode:\s*["']cors["']/);
assert.doesNotMatch(source, /var policy = factory\(\)/);

import vm from "node:vm";
const autoCount = { textContent: "N/A" };
const autoChip = {
  dataset: { state: "unavailable" },
  querySelector(selector) {
    if (selector === "[data-kernel-count]" || selector === "b") return autoCount;
    if (selector === "[data-kernel-ids]") return { textContent: "" };
    return null;
  },
};
const sandbox = {
  document: {
    readyState: "complete",
    addEventListener() {},
    querySelectorAll(selector) {
      return selector === "[data-kernel-chip]" ? [autoChip] : [];
    },
    getElementById() {
      return autoChip;
    },
  },
  fetch: async (url) => {
    assert.equal(url, policy.HONEST_URL);
    return {
      ok: true,
      redirected: false,
      url,
      json: async () => ({ doctrine_lock: { locked_formula_count: 8 } }),
    };
  },
  setTimeout,
  clearTimeout,
  AbortController,
  URL,
  Promise,
  Object,
  Array,
  TypeError,
  Error,
  Math,
  isFinite,
  console,
};
sandbox.globalThis = sandbox;
vm.runInNewContext(source, sandbox);
await new Promise((resolve) => setTimeout(resolve, 50));
assert.equal(sandbox.A11oyHonestKernelBind.HONEST_FIELD, "locked_formula_count");
assert.equal(autoCount.textContent, "8");
assert.equal(autoChip.dataset.state, "observed");

console.log(
  "OK: kernel chips bind /honest locked_formula_count === 8 or N/A; fetch failure is UNAVAILABLE.",
);
