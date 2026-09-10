# Lyte Forecast Loom: source, evaluation, and deployment boundaries

Dated evidence-pointer note. Observation window: 2026-09-10 00:21–00:47 UTC.
This is not a live status feed, receipt database, signed attestation, or production
admission. This origin indexes evidence; it does not run the forecasting model.

## What is supported by the source record

[Lyte PR 21](https://github.com/szl-holdings/lyte-services/pull/21) merged normally
as `7cd4305014ee638f773d6e128f345ad6a545be58`. The
[source gate run](https://github.com/szl-holdings/lyte-services/actions/runs/34420376101)
passed all 17 applicable gates and the full 133-test suite. The PR-only live
probe was intentionally skipped, so source CI is not deployment evidence.

The [source-owned evaluation contract](https://github.com/szl-holdings/lyte-services/blob/7cd4305014ee638f773d6e128f345ad6a545be58/docs/FORECAST_LOOM_EVALUATION.md)
fixes fractional-quantile key collisions, preserves original missing-data
provenance separately from processed inputs, bounds quantile work, and contains
lazy provider failures. Its chronological evaluator compares actual provider
outputs against robust drift, last-value, and seasonal-naive baselines. Holdout
observations are not imputed, and scale-free comparisons use training-only
seasonal denominators. Zero or missing denominators remain unscorable.

## Actual challenger evaluation, not production accuracy

[HF GPU job 6aa1f7835527934177ebe9d0](https://huggingface.co/jobs/betterwithage/6aa1f7835527934177ebe9d0)
completed on NVIDIA A10G using the merged Lyte source and the immutable upstream
checkpoint [IBM Granite PatchTST FM r2](https://huggingface.co/ibm-granite/granite-timeseries-patchtst-fm-r2/tree/b125275f9204d37cbb81fe47b9cf5e08a521e829).
IBM remains the checkpoint author; SZL owns the adapter, contract, and evaluator.

The run used six synthetic series, three non-overlapping chronological holdouts
per series, a 48-point horizon, and 512 context points. It did not establish
representative production telemetry, pretraining independence, interval
calibration, deployment SLOs, or concurrency capacity. Model capacity of 8,192
points is not evidence of measured 8,192-point inference performance.

[The source-pinned result summary](https://github.com/szl-holdings/a11oy/blob/eb816a91bc47ab2f4b3be37698dbae6bc2bf604f/docs/evidence/lyte-forecast-walk-forward-2026-09-10.json)
is in the A11oy publication candidate, not claimed to be an admitted production
release. Its referenced full-report digest identifies the original report, not
the summary. The candidate improved each series' three-fold mean against its
strongest comparator, but the first cloud-cost fold lost to robust drift.
Historical mixed-unit raw-MAE percentages are not promoted to production claims.

## Source integration and public runtime are distinct observations

[HF CPU integration job 6aa1fc3421047bf1b0371267](https://huggingface.co/jobs/betterwithage/6aa1fc3421047bf1b0371267)
completed with 70 publisher/topology/compatibility tests passing. The new
canonical verifier also passed every condition against the actual source-owned
Lyte FastAPI application at `7cd4305`, including input/raw/output digest
recomputation, fractional quantiles, source binding, and non-authority. This was
an isolated TestClient integration, not a public deployment.

A separate [public runtime observation](https://huggingface.co/jobs/betterwithage/6aa1f80221047bf1b0371210)
at 00:21:27 UTC found the Lyte Space RUNNING on HF revision
`4030523b6e9e266a3330389fc307aa3400e71c06`, serving package 4.0.0 from earlier
GitHub source/runtime `dbe2465223809853981fbdf776552cae37dac665`. Its public
`POST /api/lyte/v2/forecast` returned a repeatable baseline result whose output
digest was independently recomputed. Invalid horizon and entirely missing
context returned 422. Selecting Granite returned the explicit disabled-provider
503. All observations concern the public SAMPLE runtime, not customer telemetry.

The root product page linked to the canonical Lyte Space. Its `/lyte` route was
still a legacy presentation, so a forecast-native product projection was not
verified. A successful homepage response is not proof of forecasting capability.

## Unresolved release dependencies at the observation time

[A11oy PR 2076](https://github.com/szl-holdings/a11oy/pull/2076) repairs the
canonical publisher's retired v3 smoke routes and obsolete build schema, then
pins the tested `7cd4305` Lyte source. At 00:47 UTC it had 96 successful checks,
seven intentional skips, and one failing Grype check for the js-yaml dependency.
The existing [dependency repair PR 2077](https://github.com/szl-holdings/a11oy/pull/2077)
passed its security scan but still failed npm clean-install lockfile validation
at that observation. No gate is waived by this note.

The older [canonical run 34419010772](https://github.com/szl-holdings/a11oy/actions/runs/34419010772)
finished with failure. Independent A11oy readiness also reported two NVD-backed
defense/finance feed contract failures. Neither this note nor passing Lyte
source tests resolves those broader readiness failures.

A current-source deployment-success attestation remains UNAVAILABLE until the
normal merge, canonical publication, and actual live source-bound probes pass.
The new runtime was not declared live merely because its code merged.

## Authority and registry boundaries

The order remains GitHub source → Hugging Face runtime → a-11-oy.com product →
a11oy.net proof pointers. Granite production admission remains false.
Execution authority remains NONE. SHA-256 content digests are not signatures,
identity attestations, or accuracy guarantees. This note adds no model weights,
customer observations, receipt bodies, verifier clone, live effector, secret,
DNS change, or model-admission switch to the proof origin.
