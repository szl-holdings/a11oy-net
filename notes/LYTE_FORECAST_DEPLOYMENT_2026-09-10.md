# Lyte Forecast Loom: observed deployment follow-through

Dated evidence-pointer note. Live observations below are timestamped UTC on
2026-09-10. This origin indexes evidence; it does not host a model, receipt
body store, interactive verifier, or continuous health feed. The earlier
[source and evaluation note](LYTE_FORECAST_2026-09-10.md) remains unchanged as
a historical observation. Later successful evidence supersedes its release
blockers only within the scope stated here.

## Source admitted through normal checks

[Lyte PR 21](https://github.com/szl-holdings/lyte-services/pull/21) merged as
`7cd4305014ee638f773d6e128f345ad6a545be58` after 133 tests and 17 applicable
source gates passed. [A11oy dependency repair 2077](https://github.com/szl-holdings/a11oy/pull/2077)
merged as `2aee6f06152124953acf479f353c65e2cbc7760c` after 93 successful checks
and seven intentional skips. Actual npm clean-install tests and security scans
passed; no scanner suppression or branch-protection bypass was applied.

[A11oy publisher repair 2076](https://github.com/szl-holdings/a11oy/pull/2076)
then merged as `bda66daa67aaa2c7bd9a94bb43537f22bc6c89d7` after 97 successful
checks and seven intentional skips on the combined source. A separate completed
[exact-source integration job](https://huggingface.co/jobs/betterwithage/6aa1fc3421047bf1b0371267)
passed 70 publisher/topology/compatibility tests and the actual source-owned
Lyte FastAPI app integration. Those source tests are distinct from the public
runtime observations below.

## Actual Lyte runtime contract: PASS at 01:21:21 UTC

The completed [public live-contract observation job](https://huggingface.co/jobs/betterwithage/6aa203cb5527934177ebebfb)
loaded the verifier from the immutable admitted A11oy revision and checked its
Git blob `2dc331a09e98fe765b1185797e2c19c7861aa3e7` before execution.
Every live contract condition passed; the failed-check list was empty.

The [canonical Lyte Space](https://huggingface.co/spaces/SZLHOLDINGS/lyte)
reported repository and running-runtime revision
`13ec4f8a4db71885bc2e6eef3a960976607474c9`, stage RUNNING, domain READY,
and unchanged cpu-basic hardware. The actual application reported package
4.0.0 and both source/runtime GitHub revisions exactly
`7cd4305014ee638f773d6e128f345ad6a545be58` on five identity surfaces.
Source bindings agreed; the database was READY and tenant/workspace scoped.

`POST /api/lyte/v2/forecast` returned an actual advisory baseline forecast.
The verifier independently recomputed processed-input, original-input, and
output digests, checked repeatability, preserved distinct fractional quantiles
`q10.1` and `q10.4`, and verified missing-data counts/provenance. Invalid horizon,
entirely missing context, and an oversized quantile request returned 422.
Selecting Granite returned 503 with the explicit disabled-provider policy
message, not an unrelated load failure.

The same live pass covered six observability lenses, source-bound build and
readiness, scoped second-brain evidence, non-causal advisory Ask results,
Hatun REVIEW/DENY without authorization, explicit anonymous mutation denial,
read-only GitHub observation, unchanged persisted receipt count after read and
advisory probes, and current externally served responsive CSS/JavaScript.
CSS markers are not a substitute for a browser accessibility audit.

The runtime remains SAMPLE, with effectors disabled and human approval
required. Its reported SQLite durability is FILE_OR_PROCESS_SCOPED. This
observation does not establish production telemetry, durable enterprise
storage, calibrated confidence, model accuracy, or a service-level objective.
Execution authority remains NONE, and production Granite remains disabled.

## Product and Hugging Face source projection: matched at 01:23:21 UTC

The [product-source readback job](https://huggingface.co/jobs/betterwithage/6aa206845527934177ebec65)
observed HTTP 200 application/json on `/api/a11oy/v1/honest` at both
[a-11-oy.com](https://a-11-oy.com/api/a11oy/v1/honest) and its
[canonical A11oy runtime](https://szlholdings-a11oy.hf.space/api/a11oy/v1/honest).
Both reported `git_sha` exactly
`bda66daa67aaa2c7bd9a94bb43537f22bc6c89d7` and identical response-byte digest
`752da983a9104a3372979670916c831a1e073a9e85bf8d89449595c6a7668b17`.
Both health routes returned JSON status ok. The existing root product page
linked to the canonical Lyte Services Space.

This establishes source projection and navigation, not a newly built
forecast-native graphical interface. The separate product `/lyte` route is the
Lyte Lattice/BIND surface and was not overwritten. An HTTP 200 response without
validated identity fields was not accepted as source proof.

## Current-source canonical readiness and relock passed

[Canonical workflow 34424414138](https://github.com/szl-holdings/a11oy/actions/runs/34424414138)
uses the admitted A11oy revision above and the existing single HF writer.
Its main deployment/source-attestation job, persistent signing/storage and
restart/GDW proof job, current-source readiness job, and relock job completed
successfully. No additional Space writer, allocation, visibility, DNS, or
production-model-enablement mechanism was introduced by this work.

The readiness artifact `10132439246`, generated at 01:25:31.032 UTC, reports
100 endpoint definitions: 95 passed, five deliberately state-changing probes
skipped, zero contract violations, zero unreachable endpoints, and zero
throttled endpoints. Source identity was exactly the admitted revision before
and after probing. The two earlier NVD-backed defense/finance failures no
longer appeared. This is a bounded readiness snapshot, not guaranteed uptime
or an inference/concurrency benchmark.

The downloaded artifact ZIP independently matched GitHub's digest:
`4e4f00d01c1348ee14b14259463d8010d3de794af5dbd08d1b3b0931ea2d6b4f`.
Relock artifact `10132476926`, generated at 01:26:58.143684 UTC, reports PASS,
RUNNING, and identical A11oy HF repository/runtime revision
`8eec9a696e838e6889bd968776d8f0279e188400` bound to GitHub `bda66daa...`.
Its downloaded ZIP independently matched digest
`330ea8af7fdd3769b61c950d7aefff3a376c0ade513164bb7ee9a8dfbc57ab15`.
Artifacts remain in the linked canonical workflow, subject to its retention;
this proof origin does not copy their receipt bodies.

At the 01:31 UTC workflow readback, the broader vertical publication job
`102708311132` was still in progress. Its pending aggregate completion is not
represented as success by this note, even though the new Lyte runtime was
independently observed passing. The entire organization's models, Spaces,
repositories, and open obligations are not certified complete by a Lyte pass.

## Evaluation and authority limits stay explicit

The [admitted source-pinned challenger summary](https://github.com/szl-holdings/a11oy/blob/bda66daa67aaa2c7bd9a94bb43537f22bc6c89d7/docs/evidence/lyte-forecast-walk-forward-2026-09-10.json)
records an actual IBM Granite evaluation through the SZL provider/evaluator,
six synthetic series and three chronological holdouts per series. Each series'
three-fold mean improved against its strongest comparator, but one cloud-cost
fold lost to robust drift. Only 512 context points were used. Model capacity,
synthetic improvement, and sequential GPU timing do not establish production
representativeness, calibration, long-context performance, or deployment SLOs.
IBM remains the checkpoint author; SZL owns its adapter, contract, and evaluator.

This note grants no execution authority or production model admission.
SHA-256 digests bind content; they are not signatures or independent identity
attestations. The proof registry's global PARTIAL state and UNAVAILABLE local
receipt-chain status remain unchanged. Source → runtime → product → proof
ordering is preserved without changing unrelated registry assertions.
