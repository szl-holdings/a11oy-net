# INC-05 recapture · 2026-09-11T19:04Z

RECORD on a11oy.net. Not DNS control. Not a Cloudflare API. Not product runtime. Not a fourth origin.

## Verdict

**INC-05 remains OPEN.** Named frontiers N1–N27 stay holograms. Do not stamp production LIVE from this note.

## MEASURED this session

| Host | Observation | Class |
| --- | --- | --- |
| `https://www.a-11-oy.com/` | TLS handshake failed: `tlsv1 alert access denied` | MEASURED |
| `https://a-11-oy.com/` | Intermittent: HTTP 200 on `/api/a11oy/v1/honest`; apex HTML and `/healthz` timed out this probe | MEASURED |
| `https://a-11-oy.com/api/a11oy/v1/honest` | 200. Doctrine v11 LOCKED 749/14/163. Kernel `c7c0ba17`. Live `git_sha` `9dc70869694f72ba3fb4e632f86f96118ccb39ae`. Λ = Conjecture 1 | MEASURED |
| `https://a11oy.net/estate/alloy-os/` | 200 including `kernel.js` and `live.json` | MEASURED |
| Product signer | Not re-read this probe (`/healthz` timeout). Last successful read 2026-09-11 12:24 EDT: `signer.status=ABSENT`, `signing_available=false`, `scheme=UNAVAILABLE` | REPORTED (prior MEASURED) |
| Energy / joule | No RAPL/NVML meter observed from this origin | UNAVAILABLE |
| Hugging Face Space create / custom-domain write | No Hub connector in this session | UNAVAILABLE |

Prior origin.json bake (`observed_at_utc` 2026-08-29T18:53:21Z) recorded `www` as Cloudflare HTTP 404. This recapture is worse on the wire: the TLS session is denied before an HTTP status exists. Do not close INC-05 on the 2026-08-29 row.

## What this session cannot do

- Change Cloudflare DNS, SSL mode, or the `www` certificate.
- Inject a persistent DSSE / P-256 signer into Space `SZLHOLDINGS/a11oy`.
- Attach NVML or RAPL to the product runtime.
- Deploy exact `main` SHA onto the Space so `/honest` `git_sha` is guaranteed to match GitHub `szl-holdings/a11oy` HEAD.

Those four are owner-metal. This repository can only record the probe.

## Promotion lock

Until `https://www.a-11-oy.com/` presents a valid certificate and serves the same product Space as the apex:

- `/frontiers.json` promotion stays BLOCKED.
- Do not relabel N1–N27 OPERATIONAL.
- Do not mint a third public origin.
- Never `a11oy.com`.

Λ remains Conjecture 1. Unhackable is not claimed. SLSA L3 is not claimed.
