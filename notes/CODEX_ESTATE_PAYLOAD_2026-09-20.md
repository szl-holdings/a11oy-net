# SZL Estate Frontier — Codex Upgrade Pack

**Payload:** `ESTATE_FRONTIER_UPGRADE.md` + `szl_estate_frontier_upgrade.py`
**Captured:** 2026-09-20T14:35:00Z (MEASURED public APIs + REPORTED session doctrine)
**Authority:** GitHub `szl-holdings` is source. Hugging Face `SZLHOLDINGS` is distribution.
**Status:** Source drafts may merge after review. Operator HOLD remains on Hub publish / auto-license / `proven_trust`.

> PR context 2026-09-25: human asked to finish/merge existing PRs. This operator still refuses Hub publish, auto-license, hologram unarchive, and proven_trust=true. Observation-only source PRs may merge after review.

This path replaces the 863-byte stub on `docs/codex-estate-payload-20260920`.
Full operator: `tools/estate_codex_payload.py`.
Parent auditor: keep `szl_estate_frontier.py` v1.0.0 as the `--deep` walker.

## HOLD that remains

- no Hugging Face upload from this operator
- never auto-license
- proven_trust hardcoded false
- Λ uniqueness remains OPEN_CONJECTURE
- do not unarchive holograms
- do not warm yarqa
- do not treat HTTP 200 as qualification

## Measured 2026-09-20 / recaptured 2026-09-25

| Surface | Count | Class |
|---|---:|---|
| GitHub public org page | 117 then 119 | MEASURED |
| GitHub auth search | 124 | MEASURED |
| Unarchived | 96 | MEASURED |
| HF Spaces API | 21 | MEASURED |
| HF models | 47 | MEASURED |
| HF datasets | 35 | MEASURED |
| Dated profile 2026-09-10 | 21 / 46 / 35 | REPORTED |
| Live vs dated | models +1 | DRIFT |

Yuyay `one_zero`: geometric 0.0 BLOCK, arithmetic ~0.877 ALLOW, divergent true.

## CTO-8

1. Human-resolve licenses; never infer
2. Authority manifest canonical in `.github`
3. Pin external Actions to 40-char SHA
4. Reconcile profile counts with live inventory
5. Bind each retained HF asset KEEP|FOLD|ARCHIVE|REPLACE REVIEW_REQUIRED
6. Repair non-running Spaces before operational claim
7. One reproducible Λ-vs-arithmetic benchmark on Yuyay-13
8. lake build from existing lutar-lean — no placeholder theorems

## C1-C6

C1 quarantine ReceiptAgent v3
C2 repair/relabel SZL-Khipu-1.5B-abstain
C3 fix kernel CI szl-lambda-gate + szl-governed-norm
C4 remove unsafe joblib: szl-blocked, szl-provctl, szl-formulas, szl-ouroboros, szl-nemo
C5 quarantine chaski / chaski-5050 / A11OY-MINI research-only
C6 unblock admission/provenance: szl-blocked, szl-provctl

## PR merge policy used 2026-09-25

MERGE: small doctrine/test/observation PRs after checks green.
BLOCK: python 3.12→3.14, transformers 5.5→5.10, finance v2 dirty/failing, frontier#187 HOLD watch, Action tag bumps that drop SHA pins, stub payloads.

Run:

```bash
python3 tools/estate_codex_payload.py --out ./szl-estate-audit
```

`winner` stays null. `file_tree_walk` stays NOT_COMPLETE until `--deep` with GH_TOKEN.
