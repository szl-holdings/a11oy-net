# Curation Atlas — dated source and runtime pointer

**2026-10-17 EDT; public readbacks on 2026-10-18 UTC.** This note is a
dated, scoped evidence record for the proof registry. It is not a release
receipt, independent attestation, continuous health feed, or authorization to
use the audit output for policy enforcement.

## Published source and backend

- **MEASURED, source readback:** GitHub commit
  [`f680e5baf5d4109013ab92c72b16940307abce89`](https://github.com/szl-holdings/curation-atlas/tree/f680e5baf5d4109013ab92c72b16940307abce89)
  contains the Python backend under `backend/`.
- **MEASURED, provider readback:** The public [SZLHOLDINGS Curation Atlas
  Space](https://huggingface.co/spaces/SZLHOLDINGS/curation-atlas/tree/e09116c1e587f72fc3916ccdcd17cd0bd19011ba)
  reported revision `e09116c1e587f72fc3916ccdcd17cd0bd19011ba`, Docker SDK,
  CPU Basic, and `RUNNING` at readback. `RUNNING` is a provider stage, not an
  application-readiness or availability guarantee.
- **MEASURED, source-to-Space byte identity:** Git blob IDs for these six files
  in the GitHub commit's `backend/` directory matched the public Space tree at
  the pinned revision. The Space also has its own `.gitattributes` file; this
  comparison does not establish image-byte identity, a signed deployment
  attestation, or independence.

| Backend file | Matching Git blob ID |
| --- | --- |
| `.dockerignore` | `89cf65fc63612881e6f836394d967a26efebc78d` |
| `Dockerfile` | `389dbbde1e39f6ece1b8f151552c125a03a2f24a` |
| `README.md` | `7cc8bc81a64eabc1858a7ad279fbc09527dac8db` |
| `app.py` | `378beb90e44820aca71f63cd097aff16a723a602` |
| `audit.py` | `7a58617825af864d420c49ed5bdbda312863b9b6` |
| `requirements.txt` | `39a3e3fe34736b91fcd715c97b1199269ff7785b` |

## Bounded live observation

The hosted [`GET /healthz`](https://szlholdings-curation-atlas.hf.space/healthz)
returned HTTP 200 and `PROCESS_ALIVE`. Its `sourceRevision` matched the GitHub
commit above, but the service itself labels `sourceBinding` **DECLARED** and
`upstreamReadiness` **UNKNOWN**. The process response is not a verified build
binding or a GitHub upstream-readiness check.

The hosted [`GET /v1/orgs/szl-holdings/audit?sample_size=4`](https://szlholdings-curation-atlas.hf.space/v1/orgs/szl-holdings/audit?sample_size=4)
returned a **MEASURED** public-API observation with `observedAt` of
`2026-10-18T03:10:42Z`: 129 public repositories inventoried, four sampled,
four full heads captured, zero blocked history checks in that sample, and a
reported GitHub rate-limit remainder of 28. These values are a dated bounded
observation, not a complete organization audit, a private-repository inventory,
or a policy-consistency certificate. Reopening the endpoint may produce a
different result or a rate-limit/partial-state response.

## Subsequent owner-private frontend deployment (2026-10-18 UTC)

- **MEASURED, Sites control-plane readback:** A separate [Curation Atlas Site](https://curation-atlas-szl.stephen388352.chatgpt.site)
  (project `appgprj_6ac0a7c9c66481918ff2cd21419bf5be`) saved version 3
  from source commit `fc267770ac304666962bec9698240245aaa03105`.
  Deployment `appgdep_6ad43d4e0de88191a87d97dfeaf9f933` reported
  `succeeded` at `2026-10-18T03:31:13Z`. Its access policy was `custom`,
  allowing the owner only. The URL is not a public Atlas release.
- **MEASURED, API configuration and response readback:** Site environment
  revision 1 set `NEXT_PUBLIC_ATLAS_API_BASE` to
  `https://szlholdings-curation-atlas.hf.space`. The hosted `/healthz` returned
  HTTP 200, `PROCESS_ALIVE`, and an `Access-Control-Allow-Origin` header for
  this Site's origin. The service still declares its source binding and marks
  upstream readiness **UNKNOWN**; these responses do not attest the exact
  browser bundle or continuous end-to-end readiness.
- **MEASURED, session-limited browser observation:** At about 03:31 UTC, an
  authenticated owner browser used **Run live audit** and displayed a bounded
  four-repository result that included the Atlas head
  `93f7ff88f1c412d8f21b5eb97be07fb4c69d57f1`. No durable signed capture
  or independent witness accompanies that spot check; it is not an
  organization-wide audit or a public-access test.

## Release boundary

The linked frontend Site project `appgprj_6aaf0cfae87481918b98476c17d38392`
was inaccessible to the current publication connector. Its current deployed
frontend, its Python API wiring, and any release through that Site remain
**UNKNOWN**. This note does not claim that `a-11-oy.com` serves Atlas.
The initial note merged in [PR #306](https://github.com/szl-holdings/a11oy-net/pull/306);
this addendum still requires its own protected merge and public proof-route
readback. No independent runtime witness was run.
