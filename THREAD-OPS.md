# THREAD-OPS — estate closeout thread

**Origin:** proof only — https://a11oy.net/estate/thread-ops/
**Not product.** Do not publish this on https://a-11-oy.com.
**Not a Hugging Face Space.** Operator runbook is not a hologram.

Pinned: 2026-09-04T22:47Z · org github.com/szl-holdings · HF huggingface.co/SZLHOLDINGS

## Placement decision

| Surface | Role | This thread |
|---|---|---|
| github.com/szl-holdings/a11oy-net | source of truth | YES |
| https://a11oy.net | proof origin | YES — live page after merge |
| https://a-11-oy.com | product origin | NO |
| huggingface.co/spaces/SZLHOLDINGS/* | holograms / product runtimes | NO |

## Doctrine

- Λ = Conjecture 1 OPEN. Never a theorem.
- Trust ceiling 0.97. Deny by default.
- Stage RUNNING is not HTTP 200.
- Source-green is not a Hub republish.
- Never write a-11oy.com or a11oy.com.
- Never paste cosign private key or HMAC into chat or this file.

## GitHub lane (measured this sweep)

- a11oy-net open PRs before this landing: 0
- Merge queue on a11oy / .github / platform / immune / killinchu / forge / kernels: empty at last probe
- szl-kernels#30 merged; #29 closed as duplicate
- szl-forge#123 merged

## Live HTTP at last probe

| Surface | Status |
|---|---|
| a-11-oy.com | 200 |
| www.a-11-oy.com | FAIL (edge / cert) |
| a11oy.net + health.json + public-inventory.json | 200 |
| szlholdings-a11oy.hf.space | 200 |
| szlholdings-killinchu.hf.space | 200 |
| szlholdings-immune.hf.space | 200 (regressed earlier; re-probe) |
| static hologram roots listed in atlas.json | 404 |

## Owner-only (do not fake COMPLETE)

1. HF org write token — restore root index.html on 404 static Spaces
2. Cloudflare API — www cert, gdw tunnel
3. Org CodeQL / GitHub App — .github#158 digest NOT VERIFIED
4. HMAC mint and key collapse to 9926bf69 — secret store only

## Tracking

- https://github.com/szl-holdings/.github/issues/523
- Machine contract: /estate/thread-ops.json
- Terminal payload: /SZL-GROK-PAYLOAD.md
