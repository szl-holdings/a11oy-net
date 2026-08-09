// SPDX-License-Identifier: Apache-2.0
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const policy = require("./probe_policy.js");

function expectDecision(actual, expected) {
  assert.deepEqual(actual, expected);
  assert.equal(Object.isFrozen(actual), true);
}

expectDecision(policy.classifyHttpResponse({ type: "opaque", status: 0, ok: false }), {
  state: "unverified",
  tone: "warn",
  label: "UNVERIFIED",
  reason: "STATUS_HIDDEN_BY_BROWSER",
  positive: false,
});
expectDecision(policy.classifyHttpResponse({ type: "opaqueredirect", status: 0, ok: false }), {
  state: "unverified",
  tone: "warn",
  label: "UNVERIFIED",
  reason: "STATUS_HIDDEN_BY_BROWSER",
  positive: false,
});
expectDecision(policy.classifyHttpResponse({ type: "basic", status: 204, ok: true }), {
  state: "observed",
  tone: "ok",
  label: "HTTP 204 · OBSERVED",
  reason: "VISIBLE_HTTP_SUCCESS",
  positive: true,
});
expectDecision(policy.classifyHttpResponse({ type: "cors", status: 503, ok: false }), {
  state: "unavailable",
  tone: "down",
  label: "HTTP 503 · UNAVAILABLE",
  reason: "VISIBLE_HTTP_FAILURE",
  positive: false,
});
expectDecision(policy.classifyHttpResponse({ type: "basic", status: true, ok: true }), {
  state: "unavailable",
  tone: "down",
  label: "UNAVAILABLE",
  reason: "MALFORMED_RESPONSE",
  positive: false,
});
expectDecision(policy.classifyHttpResponse(null), {
  state: "unavailable",
  tone: "down",
  label: "UNAVAILABLE",
  reason: "MALFORMED_RESPONSE",
  positive: false,
});

expectDecision(policy.classifySpaceMetadata({ runtime: { stage: "RUNNING" } }), {
  state: "observed",
  tone: "ok",
  label: "RUNNING · REPORTED",
  reason: "SCHEMA_VALID_HUB_STAGE",
  positive: true,
});
expectDecision(policy.classifySpaceMetadata({ runtime: { stage: "paused" } }), {
  state: "unavailable",
  tone: "down",
  label: "PAUSED · REPORTED",
  reason: "HUB_STAGE_UNAVAILABLE",
  positive: false,
});
expectDecision(policy.classifySpaceMetadata({ runtime: { stage: "BUILDING" } }), {
  state: "unverified",
  tone: "warn",
  label: "BUILDING · REPORTED",
  reason: "HUB_STAGE_TRANSITIONAL",
  positive: false,
});
expectDecision(policy.classifySpaceMetadata({ runtime: { stage: "FUTURE_STAGE" } }), {
  state: "unverified",
  tone: "warn",
  label: "FUTURE_STAGE · REPORTED",
  reason: "HUB_STAGE_UNRECOGNIZED",
  positive: false,
});
expectDecision(policy.classifySpaceMetadata({ runtime: { stage: 1 } }), {
  state: "unavailable",
  tone: "down",
  label: "UNAVAILABLE",
  reason: "MALFORMED_SPACE_METADATA",
  positive: false,
});
expectDecision(policy.classifyFailure("timeout"), {
  state: "unavailable",
  tone: "down",
  label: "UNAVAILABLE",
  reason: "TIMEOUT",
  positive: false,
});

assert.equal(
  policy.isExactResponseFor(
    {
      redirected: false,
      url: "https://huggingface.co:443/api/spaces/SZLHOLDINGS/a11oy",
    },
    "https://huggingface.co/api/spaces/SZLHOLDINGS/a11oy",
  ),
  true,
);
for (const response of [
  {
    redirected: true,
    url: "https://huggingface.co/api/spaces/SZLHOLDINGS/a11oy",
  },
  {
    redirected: false,
    url: "https://huggingface.co/api/spaces/SZLHOLDINGS/other",
  },
  {
    redirected: false,
    url: "http://huggingface.co/api/spaces/SZLHOLDINGS/a11oy",
  },
  {
    redirected: false,
    url: "https://user@huggingface.co/api/spaces/SZLHOLDINGS/a11oy",
  },
  {
    redirected: false,
    url: "https://huggingface.co/api/spaces/SZLHOLDINGS/a11oy#fragment",
  },
  { redirected: false },
  null,
]) {
  assert.equal(
    policy.isExactResponseFor(
      response,
      "https://huggingface.co/api/spaces/SZLHOLDINGS/a11oy",
    ),
    false,
  );
}

assert.deepEqual(policy.states, ["observed", "unverified", "unavailable"]);
assert.equal(Object.isFrozen(policy), true);
assert.equal(Object.isFrozen(policy.states), true);

console.log(
  "OK: browser observations fail closed; only visible HTTP successes or " +
    "schema-valid RUNNING metadata receive an observed state.",
);
