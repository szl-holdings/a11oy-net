// SPDX-License-Identifier: Apache-2.0
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const policy = require("./atlas_policy.js");

assert.equal(policy.allows("SPACE", "SZLHOLDINGS/killinchu"), false);
assert.equal(policy.allows("SPACE", "SZLHOLDINGS/a11oy"), true);
assert.equal(policy.allows("MODEL", "SZLHOLDINGS/killinchu"), true);
assert.equal(policy.allows("SPACE", "another-owner/a11oy"), false);
assert.equal(policy.allows("SPACE", ""), false);
assert.deepEqual(policy.excluded, ["SPACE:SZLHOLDINGS/killinchu"]);

console.log("OK: generated atlas admission excludes only the access-gated Killinchu Space.");
