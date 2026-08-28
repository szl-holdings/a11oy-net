<!--
SPDX-License-Identifier: Apache-2.0
© 2026 Lutar, Stephen P. — SZL Holdings · ORCID 0009-0001-0110-4173 · Doctrine v11 LOCKED
-->

# Branch protection (a11oy.net)

This document **proposes** required check-run names. It cannot flip GitHub
protection on its own. The introducing pull request **cannot self-certify**
these contexts as control-plane-required.

Existing protected contexts on this repository (do not rename):

| Guard | Workflow | Exact check-run name |
|---|---|---|
| Link, asset, proof, diligence, atlas, probe, edge contract | `link-check.yml` | `Link & Asset Check` |
| Pages artifact inspect (PR only) | `link-check.yml` | `pages build and deployment` |
| Doctrine overclaim | `overclaim-guard.yml` | (reusable job name from `szl-holdings/.github`) |

Proposed investor-smoke contexts. Use these exact reported check-run names
if they are later required:

| Guard | Workflow | Exact check-run name |
|---|---|---|
| Investor smoke contract | `investor-smoke-gate.yml` | `Investor smoke contract (S1-S12 static)` |
| Investor smoke S7 bind | `investor-smoke-gate.yml` | `Investor smoke bind (S7 kernel chips bind /honest)` |
| Investor smoke live probes | `investor-smoke-gate.yml` | `Investor smoke live probes` |

The three investor-smoke contexts are **proposed** required checks. See
[`docs/INVESTOR_SMOKE_GATE.md`](../docs/INVESTOR_SMOKE_GATE.md).

S7 asserts every a11oy.net kernel chip binds `/honest`
`locked_formula_count` (8 or N/A / UNAVAILABLE). Committed chips bind via
`scripts/honest_kernel_bind.js` (#24). Catalog genome `LOCKED-PROVEN` (25) is a
real labelled catalog count. Do not demand 25 be deleted. Do not rewrite
chips to fake a `/honest` bind. Hardcoded 8 is still FAIL.

S1 HEAD 405/404 (where GET is 200) stays KALLPA-owned. S2 committed
`health.json` (#25) carries `signer=unavailable` and `sha` of last published
main; that is not DSSE-LIVE and not an uptime claim. This repository does
not add HEAD handlers.

Verify a context before requiring it: the name must match the job `name:`
field exactly as GitHub reports it on the check run.
