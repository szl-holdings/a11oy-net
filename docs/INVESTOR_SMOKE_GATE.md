<!--
SPDX-License-Identifier: Apache-2.0
© 2026 Lutar, Stephen P. — SZL Holdings · ORCID 0009-0001-0110-4173 · Doctrine v11 LOCKED
-->

# Investor smoke gate (S1–S12) — a11oy.net

QHAPAQ cut. Fail-closed HTTP + static contract against the proof-registry
origin `https://a11oy.net`. **Do not merge.** Encodes assertions only. Does
not weaken Immutable HF byte parity (this repo has no Dockerfile / hf-sync
admission inputs), does not POST, does not add HEAD handlers (KALLPA owns
those on a11oy), and does not touch a11oy PR 1363 or PR 1366.

Workflow: `.github/workflows/investor-smoke-gate.yml`

| Job (exact check-run name) | What it proves |
|---|---|
| `Investor smoke contract (S1-S12 static)` | Fixtures, skip-as-green rejection, D-rows, committed `health.json` S2 |
| `Investor smoke bind (S7 kernel chips bind /honest)` | Every a11oy.net kernel chip binds `/honest` `locked_formula_count` (8 or N/A / UNAVAILABLE), not genome `LOCKED-PROVEN` (25) |
| `Investor smoke live probes` | GET/HEAD against `https://a11oy.net` and `https://www.a11oy.net` only |

This pull request cannot certify those names as control-plane-required. See
`.github/BRANCH_PROTECTION.md`.

## Owners

| Defect | Owner | This PR |
|---|---|---|
| S7 kernel chips bind `/honest` | **INTI** | Fail-closed assertion. Committed chips bind live `/honest` via #24 (`scripts/honest_kernel_bind.js`; 8 or N/A / UNAVAILABLE). Catalog 25 stays labelled. Do not demand 25 be deleted. |
| S1 HEAD 405/404 vs GET 200 | **KALLPA** | Probes only. No HEAD handlers. |
| S2 health JSON SHA + signer enum | **KALLPA** | Committed `health.json` (#25) has `signer=unavailable` and `sha` of last published main. That is not DSSE-LIVE and not an uptime claim. `dsse_live` stays `NOT_CLAIMED`. |
| S3 unlabeled live coords | this gate | Fail-closed: UNAVAILABLE or MEASURED **with method**. Do not invent MEASURED. |
| PR 1366 memory covenant PG18 | out of scope | **RED**. Not this gate. Lives on a11oy. |

## S7 — BIND (AYNI correction)

Fail-closed assertion:

Every **kernel chip** on a11oy.net **must bind** `/api/a11oy/v1/honest`
`locked_formula_count` (**8** or **N/A** / **UNAVAILABLE**), not genome
`LOCKED-PROVEN` (**25**).

Both numbers are real:

- locked kernel is exactly 8 `{F1,F4,F7,F11,F12,F18,F19,F22}`
- genome catalog `LOCKED-PROVEN` is 25 and **stays labelled as catalog**

Do not demand 25 be deleted. Do not rewrite chips to fake agreement. A
hardcoded `exactly 8` that does not read `/honest` is still **FAIL**.

Committed surfaces (#24): hero chip carries `data-honest-url` +
`data-honest-field="locked_formula_count"` with first paint **N/A**. Footer
chip has no per-element URL; `scripts/honest_kernel_bind.js` paints every
`[data-kernel-chip]`. Diligence is scriptless N/A with the honest URL+field
labelled. Formula ids are painted from `/honest` `locked_formula_ids`, not
hardcoded in HTML.

## Dual-origin inclusion

`site ⊆ a11oy.net ⊆ git tag ⊆ HF card`, **or labelled gap**. This gate does
not invent agreement. A missing git tag or missing HF card is a labelled
gap, not PASS-by-skip.

## Matrix

Verdicts: `PASS` · `FAIL` · `UNAVAILABLE` · `SNAPSHOT <date>` · `UNCONFIGURED`.
A missing probe is **FAIL**. `SNAPSHOT` without a date is rejected.
`UNAVAILABLE` is allowed only for S4 / S6 / S9. `UNCONFIGURED` is allowed only
for wire-D. L1–L6 are `SNAPSHOT 2026-08-28`. Never claim production-scale with
no N. Do not invent DSSE-LIVE. Do not claim LIVE uptime.

| ID | Check | Honest result this PR encodes |
|---|---|---|
| S1 | Both origins 200 on core routes; HEAD must not 405/404 where GET is 200 | Live probe (KALLPA owns 405/404 product fixes) |
| S2 | Health JSON SHA + signer enum `{DSSE-LIVE, UNSIGNED-LOCAL, unavailable}` | Committed document: `signer=unavailable` + `sha` of last published main. Not DSSE-LIVE. Not uptime. Live GET must 200 the same contract. |
| S3 | Live-fetch coords UNAVAILABLE or MEASURED with method; no raw unlabeled latitude in first viewport | Viewport probe; do not invent MEASURED |
| S4 | Staging receipt-write | **UNAVAILABLE** (no POST) |
| S5 | Read-only does not mint | Static + live GET |
| S6 | Refuse / abstain | **UNAVAILABLE** (no POST) |
| S7 | Kernel chips bind `/honest` 8 or N/A / UNAVAILABLE, not genome 25 | Committed chips bind via #24. Live Pages must serve that bind. Catalog 25 labelled. |
| S8 | Designed 404 | Live undeclared `*.js` must not be HTML 200 |
| S9 | Authz empty-state | **UNAVAILABLE** |
| S10 | OG image 200 | Live `/assets/a11oy-net-social.png` |
| S11 | Space boot if this repo has one | **FAIL** — this repo has no Space; missing boot target is not skip-as-green |
| S12 | Card YAML parses | **FAIL** — README has no HF card YAML; missing probe is not skip-as-green |
| L1–L6 | Stress | **SNAPSHOT 2026-08-28** (not executed; no N) |
| D10 | Screenshots | **SNAPSHOT 2026-08-28** |
| wire-D | SLSA L2 | **UNCONFIGURED** (roadmap / not claimed) |
| PR 1366 | Memory covenant | **RED out of scope** |

## Out of scope (standing)

- Never merge a11oy PR 1363 (HOLD). This is a11oy-net.
- PR 1366: **RED**, out of scope (a11oy).
- No Dockerfile / hf-sync admission-input changes (none in this repo).
- No POST.
- No HEAD handlers.
- Do not demand genome catalog 25 be deleted.
- Do not run stress. L1–L6 stay SNAPSHOT 2026-08-28.
- Do not invent DSSE-LIVE.
- Do not claim LIVE uptime.

## Measured live (re-probe after rebase)

Canonical origin `https://a11oy.net`. Alias `https://www.a11oy.net`.
Contract S2/S7 follow committed #24/#25. Live GET/HEAD may still FAIL if
GitHub Pages has not published those revisions. Missing live probe is FAIL,
never skip-as-green.

See the pull-request body for the live matrix recorded at ship time.

## Run locally

```bash
python3 -m pytest -q tests/test_investor_smoke_gate.py
python3 -m pytest -q tests/test_investor_smoke_bind.py
python3 scripts/investor_smoke_gate.py --mode live \
  --origin https://a11oy.net --origin https://www.a11oy.net
```
