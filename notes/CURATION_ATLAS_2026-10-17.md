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

## Original owner-private frontend deployment (2026-10-28 UTC)

- **MEASURED, Sites deployment readback:** The original [Curation Atlas Site](https://curation-atlas-szl.stephenlutar2.chatgpt.site)
  (project `appgprj_6aaf0cfae87481918b98476c17d38392`) is live at that URL with
  saved version 2 from source commit `533a29d9c8d681e167d932661271688c708972ca`.
  Deployment `appgdep_6ae2727cce248191833c5757133aebe9` reported `succeeded` at
  `2026-10-28T22:09:10Z`.
- **MEASURED, Sites access readback:** Access mode is `custom`; the allowlist
  contains only the owner `stephenlutar2@gmail.com`, with
  `external_visitor_count=0`. This is an owner-private Site and has no public
  audience.
- **MEASURED, API CORS/source readback:** With this Site origin, the HF API
  returned HTTP 200 for [`GET /healthz`](https://szlholdings-curation-atlas.hf.space/healthz)
  and [`GET /v1/orgs/szl-holdings/audit?sample_size=4`](https://szlholdings-curation-atlas.hf.space/v1/orgs/szl-holdings/audit?sample_size=4).
  `healthz` reported source revision
  `533a29d9c8d681e167d932661271688c708972ca` with `sourceBinding` **DECLARED**,
  and returned `Access-Control-Allow-Origin` for the Site. These are endpoint
  observations only; they do not provide an independent deployment attestation
  or runtime witness.

## API source refresh and bounded probe (2026-10-28 EDT)

- **MEASURED, source and provider readback:** The verified signed
  [Atlas GitHub main](https://github.com/szl-holdings/curation-atlas/tree/072605abec3c24e969eea1ccd132038508c02b02)
  is `072605abec3c24e969eea1ccd132038508c02b02` after research and API
  Origin-guard PRs [#17](https://github.com/szl-holdings/curation-atlas/pull/17)
  and [#18](https://github.com/szl-holdings/curation-atlas/pull/18). The
  [Space tree](https://huggingface.co/spaces/SZLHOLDINGS/curation-atlas/tree/98602e5276b5000d29d227d857688a1264ab8fb9)
  reported `98602e5276b5000d29d227d857688a1264ab8fb9` and `RUNNING`.
  These six Space file blobs matched the GitHub commit's `backend/` blobs:

| Backend file | Matching Git blob ID |
| --- | --- |
| `.dockerignore` | `89cf65fc63612881e6f836394d967a26efebc78d` |
| `Dockerfile` | `389dbbde1e39f6ece1b8f151552c125a03a2f24a` |
| `README.md` | `d96adba0fb800325709f60f21a16075264639379` |
| `app.py` | `1d23f3e6f752133220f590a3964547b425c0beae` |
| `audit.py` | `7a58617825af864d420c49ed5bdbda312863b9b6` |
| `requirements.txt` | `39a3e3fe34736b91fcd715c97b1199269ff7785b` |

- **MEASURED, live API spot check:** `/healthz` returned HTTP 200,
  `PROCESS_ALIVE`, the above GitHub revision as `sourceRevision`,
  `sourceBinding: DECLARED`, and `upstreamReadiness: UNKNOWN`. A GET audit from
  `https://example.invalid` returned HTTP 403, `ORIGIN_NOT_ALLOWED`, and
  `Cache-Control: no-store`. A GET from the original Site origin returned HTTP
  200 and a **MEASURED** public observation at `2026-10-28T23:54:04Z`:
  130 public repositories inventoried and four deeply sampled. The Space edge
  still reflected the unrelated Origin in `Access-Control-Allow-Origin`; the
  app guard is not authentication or a strict edge CORS policy. The data is
  public, and callers can omit or forge `Origin`.
- **UNAVAILABLE, current Site publication:** The original Site's last
  successful version readback above remains v2 from
  `533a29d9c8d681e167d932661271688c708972ca`. The current
  Sites connection returns `project_not_found` for that exact project ID.
  A local frontend build from `072605abec3c24e969eea1ccd132038508c02b02`
  includes the live API URL in its client bundle. This release attempt did not
  deploy a matching Site version or witness an authenticated browser audit;
  current provider status is **UNAVAILABLE** through this connector. An
  unauthenticated Site GET returned 401, which does not prove browser wiring.
- **MEASURED, separate product pointer:** At `2026-10-29T00:03Z`,
  [`a-11-oy.com`](https://a-11-oy.com) returned HTTP 200 with an Atlas GitHub
  source link. Its `/api/build-info` reported revision
  `6db8b768cade188d5d14ec57efdd710701059e98` from `env:SZL_GIT_SHA`.
  This is a product build observation, not Atlas Site deployment or a policy
  qualification. The ten-Space retention proposal remains open in
  [A11oy PR #3035](https://github.com/szl-holdings/a11oy/pull/3035), while
  [Killinchu PR #562](https://github.com/szl-holdings/killinchu/pull/562)
  merged the matching shared-file source.

## Release boundary

The original Site's v2 deployment, the refreshed API, and the product source
link are separate observations. None establishes an authenticated browser
audit through the original Site, continuous runtime readiness, or a ten-Space
policy release. The initial note merged in
[PR #306](https://github.com/szl-holdings/a11oy-net/pull/306), the separate
Site addendum in [PR #307](https://github.com/szl-holdings/a11oy-net/pull/307),
and the original Site update in
[PR #313](https://github.com/szl-holdings/a11oy-net/pull/313).
