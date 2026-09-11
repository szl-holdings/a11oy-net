# HF tooling: Forge evaluation → A11oy product

**Dated evidence-pointer note, 2026-09-11.** This static proof origin does not
serve the application, rehost receipt bodies, run signatures, or grant authority.
Publication order remains **GitHub → Hugging Face → a-11-oy.com → a11oy.net**.

## Open the application

[Tooling observatory](https://a-11-oy.com/frontier-tooling) ·
[Python API](https://a-11-oy.com/api/a11oy/v1/frontier-tooling) ·
[Original Forge implementation](https://github.com/szl-holdings/szl-forge/pull/216) ·
[Merged product implementation](https://github.com/szl-holdings/a11oy/pull/2095)

A11oy source **`71e056185ec3090ebe633727ec90c3bfbb19bc78`** exposes the four
previously executed Forge reports through a read-only Python router and a responsive
product view. The API verifies a source-defined archive digest and the four original
receipt hashes on each read. Corrupt/missing archives return 503, not cached success.

**Archived evaluation is distinct from current product installation.** The view
separately inspects installed package metadata; it does not import/install agent
packages or start training. A matching version is not exact-source attestation.

## Executed application tests

[Hosted Python/browser run 34595159346](https://github.com/szl-holdings/a11oy/actions/runs/34595159346)
passed **36 Python tests** plus real FastAPI/Uvicorn and Chromium tests at
320×568, 375×812, 768×1024 and 1440×900. Tests cover keyboard controls,
filters, reduced motion, overflow, actual shared navigation assets, removal of
stale success on a failed refresh, and subsequent recovery. These are hosted
application tests, **not a production-browser observation**.

Artifact `10262536180` archive SHA-256:
`f688cf1ebeaa046468f1def042a6ac2b32f5a81b4e62ecc38bdba16da22f951d`.
The artifact was downloaded and checked against GitHub metadata and source-file hashes.
Earlier missing-navigation and 320px-overflow failures were corrected, not exempted.

## Actual public readback

[Read-only Hugging Face Job 6aa3ee4e21047bf1b0375b45](https://huggingface.co/jobs/SZLHOLDINGS/6aa3ee4e21047bf1b0375b45)
observed the two public origins from **2026-09-11T12:04:35.590970Z** through
**2026-09-11T12:04:36.398848Z**. The method used bounded unauthenticated HTTPS
GETs, rejected redirects, and compared JavaScript/CSS and original receipt SHA-256s
with admitted source evidence. No writes or training were performed by the probe.

**18 of 18 HTTP checks passed**, nine per origin:
`szlholdings-a11oy.hf.space` and `a-11-oy.com`. The page markers, exact JS/CSS,
product summary, canonical build-info, and four original receipts were checked.
Both APIs reported product source `71e056185ec3090ebe633727ec90c3bfbb19bc78`.
The Hub reported revision `cabf38a24003b9bedd165632c669a8e8881c746a` and `RUNNING`.
These are dated observations, not a continuous availability or authorization guarantee.

The served HTML includes existing application-wide GRC, Spaces, and operator-widget
additions. It was observed as a page, **not falsely certified byte-identical to the
unaugmented template**. The exact JS/CSS checks and four nested receipt checks are
separate, stronger byte-level observations.

Public readback report SHA-256:
`9fe0bdfc972cd2439221b057621807618fb092e1f23bd52310a092ef3cc5b9ca`.

## Traceable archive

The original [Forge main run 34484379349](https://github.com/szl-holdings/szl-forge/actions/runs/34484379349)
used source `74a8a07ced6c6b8697b31b7d0e482c4241d55880`.
Product archive digest:
`4efd64ffd9c3e1c5a6de5a7d18b206d5464d8906cbb0a51d51abeef80e74c12d`.
Original report bodies stay on the product:
[Hub/Linux](https://a-11-oy.com/api/a11oy/v1/frontier-tooling/receipts/hub-linux),
[Hub/Windows](https://a-11-oy.com/api/a11oy/v1/frontier-tooling/receipts/hub-windows),
[TRL](https://a-11-oy.com/api/a11oy/v1/frontier-tooling/receipts/trl), and
[Tau](https://a-11-oy.com/api/a11oy/v1/frontier-tooling/receipts/tau).

## Independent limits remain visible

[Canonical publication run 34595800228](https://github.com/szl-holdings/a11oy/actions/runs/34595800228)
passed A11oy deployment, source verification, persistent configuration/restart checks,
and terminal relock. Its separate vertical-publication job failed on the Lyte path.
The verified vertical artifact `10262248335` records `lyte_exit_code: 1`,
`complete: false`; it does not justify a whole-estate green claim. This remains
tracked by [lyte-services#18](https://github.com/szl-holdings/lyte-services/issues/18).

The observed A11oy process had Hub 1.29.0 and no installed TRL, Transformers,
Accelerate or tau-ai distribution. That is displayed explicitly; the evaluation
libraries were installed in Forge's separate test environments. This delivery does
not claim a production dependency migration, private-memory integration, trained
model, measured GPU throughput, distributed training, or 1M-token training.

Reports are unsigned. Original evaluation dependency closures are not fully hash-locked.
**Production model admission remains false; evaluation disposition stays HOLD.**
The public proof index remains an index of pointers, not a receipt database.
