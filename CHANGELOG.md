# Changelog

## 2026-10-06 - adopt the estate's KANCHAY 1.3.0 tokens and type

- Vendor the KANCHAY 1.3.0 tokens-only stylesheet (`assets/szl/szl-tokens.css`, pinned by
  `assets/szl/SOURCE.json`), so this origin shares the estate's one design system. It is linked
  first on every page that links a stylesheet. Tokens only: this origin keeps its own component
  CSS, because `.card`, `.chip`, `.hero` and `.nav` collide with KANCHAY's components.
- Re-point the proof token layers (`kanchay-base.css`, `kanchay.css`, `diligence.css`, the Flow
  Shell and the homepage) at KANCHAY palette tokens:
  - graphite neutrals (canvas `#080B12`);
  - teal `--color-yuyay-200` for the former `#3af4c8` proof accent;
  - silver for lattice;
  - the same hatun gold.
- Typography moves to KANCHAY's device font stacks. The Fraunces, Instrument Serif and Inter
  webfonts are removed. The homepage heading sets the product name `a11oy` in the shared sans, so
  its digits no longer read as "alloy" in the italic serif.
- The wordmark glyph is the SZL Orbit v2 icon (`assets/szl/logos/szl-icon-32.svg`) instead of the
  retired lambda-only glyph.
- Gates `check_proof_surface.py` and `check_diligence_surface.py` resolve the proof tokens through
  the vendored palette. They pin the vendored bytes and keep the ghost-text 4.5:1 floor.
- Dated snapshot pages (`estate/*-2026-*`) and the hash-pinned confirmation record are
  byte-unchanged.

## 2026-10-05 - preserve content-addressed Atelier bytes on Windows

- Mark only atelier/app.js as byte-preserved in .gitattributes. Its source bytes, module URL and existing exact SHA-256 check remain unchanged; no global Git setting is changed.
- Add a temporary-repository checkout regression under core.autocrlf true, input and false. The true case reproduced LF-to-CRLF drift before this policy change. Existing signed source and publication gates remain required.

## 2026-10-05 - keep Atelier navigation independent of inventory counts

- Replace the undated forty-model navigation description with a versioned Hub artifact explorer description. Generated inventory counts and dated records are unchanged.
- Add three offline HTML-parser contracts for the description, canonical Space identity, and explicit non-product-runtime boundary. No model, kernel, dataset, runtime or provider setting is changed.

## 2026-10-05 — repair the static Atelier JavaScript parser contract

- Replace the Python-style `or` token in `atelier/app.js` with JavaScript `||`, restoring parseability while retaining the existing missing-or-empty model-base fallback; demote the selected model heading to `h2` so the walk view keeps one document-level `h1`.
- Add offline Node and Python-collected regression tests covering parse success, direct model-base values, empty/missing fallback, HTML escaping, and unchanged signed/energy labels. The proof origin remains a static lab handoff; no model is loaded, retrained, promoted, or newly measured by this repair.
- Qualify the `/atelier/` reader path and local verification commands without changing its canonical source (`szl-holdings/szl-atelier`), public Space, navigation tier, runtime claim, or evidence vocabulary.

## 2026-10-03 — close visible Hub label drift and update the Pages runbook

- After protected merge #263, align the Estate OS public-Hub count card and three dated unauthenticated Space-status notes with the `SNAPSHOT` machine contracts. Retain the separate authenticated `REPORTED` status and the limits of an HTTP 401. Counts, observation times, Hub visibility, and provider resources are unchanged.
- Replace the obsolete Pages `legacy` migration instructions with the observed Actions deployment state. Protected main `68ec09e303d215eebdc5c6268519406820025f9d` passed its merge-triggered Pages run and the public static health readback carried that SHA.
- Record the distinct Pages origin-certificate renewal risk observed October 2–3 UTC: GitHub reports `bad_authz`, HTTPS enforcement off, and an October 14 origin expiry while the Cloudflare public edge still serves HTTPS. Provider diagnostics and renewal verification remain open.

## 2026-09-30 — current estate pointer and explicit deployment limits

- Add the immutable `/estate-observed-2026-09-30.json` public-only observation and move `/estate-current.json` to its exact SHA-256. The record separates the 120-repository GitHub public listing, the generated 49-model / 34-dataset / 26-author-API-Space plus one profile-row Hub view, and the exact `a11oy` source/runtime match.
- Preserve the proof-origin gaps in the current record instead of promoting reachability: legacy Pages source-to-deployment equivalence is `UNAVAILABLE`, the static health SHA did not match current source, live security headers were absent, and GitHub reported the custom-domain certificate as `bad_authz` with HTTPS enforcement disabled. Cloudflare's HTTP-to-HTTPS redirect was observed separately and is not treated as a GitHub certificate repair.
- Keep all earlier estate observations immutable and linked as historical evidence. No model, dataset, Space, kernel, DNS, certificate, runtime, or provider setting was changed by this pointer refresh.

## 2026-09-29

- `/experiments/` adds a TypeSafe Triage software-lab RECORD with canonical GitHub source, Hub source, demo location, the current `/readyz` version/source binding, and the product lab manifest. The source contract declares Python deterministic triage and `model_loaded=false`; promotion remains HOLD, production admission false, and runtime NOT_PROBED on this origin. It is source evidence only.
- Start the browser-local Alloy experiment independently of the dated inventory read, with a five-second header/body deadline and visible invalid-snapshot failures. Mark unprobed remote systems NOT_PROBED and retain independent signer uncertainty. Report proof completion only after admission, reuse, adapter denial, a fault, verified restoration, and ledger replay. Product readiness and authorization are not established by this local experiment.


## 2026-09-29

- Hub counts on this origin are generated, not typed. `scripts/generate_hf_inventory.py` reads the unauthenticated Hub API (models, datasets, Spaces with runtime stage, kernels, collections, buckets, and the README profile Space) and writes `/public-inventory.json` (schema v4), `/estate/hf-current.json`, `/live-align/hf_live_inventory.json`, the hub block and file-presence classification of `/models.json`, the `hub_presence` block of `/spaces.json`, and the marked count fields on `/`, `/estate/`, `/estate/os/`, `/atelier/` and `/notes/`. Output is sorted and deterministic; unchanged Hub content keeps its first `observed_at`. Private assets are NOT_OBSERVED, never zero. `.github/workflows/hf-inventory-refresh.yml` reruns it daily and on dispatch and proposes a reviewed pull request only when the output changes; it holds no Hugging Face token and cannot write to the Hub.
- The 2026-08-31 capture is kept byte-identical at `/public-inventory-2026-08-31.json`; the regenerated `/public-inventory.json` no longer lists the 32 Space rows the public listing stopped returning. `/estate.json` stays the dated 2026-08-31 snapshot (`evidence_class` `MEASURED (historical)`, reader guide points at `/estate/hf-current.json`).
- The home page no longer probes the absent Spaces `szl-estate-live` and `receipt-chain-live`. Its Hugging Face rows and their probe bindings are generated from `/estate/hf-current.json`: the `/spaces.json` KEEP Spaces the public listing still returns, Killinchu withheld. The `/estate/os/` bake keeps its rows and records nine retired Hub links in `linkRetirements`.
- The refresh workflow creates its commit through GraphQL `createCommitOnBranch` (`scripts/verified_commit_payload.py`), which GitHub signs. Its first run committed locally, and main's required-signature rule blocked that unsigned refresh PR (#238).
- `scripts/check_proof_surface.py` no longer asserts typed Hub counts or the 48-id Space list. It checks that every count equals the length of its own id list, that derived files and pages equal what the generator derives, that no page or bake links a Hub asset absent from the listing, and that `observed_at` is a real, non-future UTC second.

## 2026-09-26

- Key pointers: `/`, `/record/` and `/record.json` now point readers at `https://a-11-oy.com/cosign.pub`, the key served by the signing product origin, instead of szl-holdings/.github `cosign.pub`. `estate.json` records that the 2026-08-29 closeout matched the a11oy Space `/cosign.pub` and gives that key as `keyid_reported` 9926bf69, with no PEM hash, so `record.json` restates that match and key identity as `REPORTED`. The key identity is `MEASURED` for the 2026-09-26T02:37:38Z fetch, when both URLs served keyid 9926bf69. As of 2026-09-26 that key is not published in szl-holdings/.github. The product repository `szl-holdings/a11oy` committed a copy at `ayllu/keys/council-runtime-2026-07-21.pub` in `0d3a2d4c` (2026-07-21), wrapped at 76 columns; its README says the copy was recovered from the product's own signatures by ECDSA public-key recovery. `record.json` `trust_bound` also names the product's ephemeral-key fallback. `/record/` and `record.json` give the fingerprints with their hashing methods: SPKI DER SHA-256 `8e2d106c…`, keyid `9926bf69…` (SHA-256 of the PEM text without leading and trailing whitespace, the product's `dsse_keyid`) and plain `sha256sum` of the served file `c8b73461…`. `record.json` lists both szl-holdings/.github org keys as not matching and keeps the evidence apart in its fields. The `keys/cosign.pub` mismatch is `REPORTED` from `estate.json` (which org PEM the closeout verify loaded was not recorded); the file itself measured 2026-09-26 as keyid 421a1422, while `estate.json` labels the entry `d3028f8a`. The root `cosign.pub` (d3028f8a) was not recorded as fetched at the closeout, so its mismatch is `MODELED`: derived from the reported closeout keyid, not measured. As of 2026-09-26, publishing one org key that verifies product receipts is a pending owner key ceremony. "signed RECORD index" becomes "RECORD index": `record.json` has no signature. `check_proof_surface.py` now rejects "signed RECORD" on `/`, `/record/` and `/record.json`, and rejects `record.json` `public_key` evidence classes outside the SZL evidence vocabulary. `/estate/` key table corrected: `keys/cosign.pub` measured 2026-09-26 as keyid 421a1422, where `estate.json` labels it d3028f8a, the root key; `/khipu/pubkey.pem` served the root org key when fetched 2026-09-26T02:37Z; the Space `/cosign.pub` keyid is marked as `estate.json`'s `keyid_reported`. `estate.json` is not edited.

## 2026-09-25

- `/pricing/` no longer publishes a price list. It is a noindex pointer to the product origin's pricing, linked as `https://a-11-oy.com/pricing` without a trailing slash (`/pricing/` returned 404 there when checked on 2026-09-25/26 UTC). The 2026-08-30 hypothesis list (Verify / Control / Assurance-Sovereign tiers, with the "80% conversion target" and "Signed receipt per consequential action" bullets) is withdrawn. The page labels it as history and links to `64c1c9a`. `/contact/` no longer calls those tiers "the actual SKUs" or advertises six-month pilots; its pilot and pricing cards link to the product site. The `/contact/` and `/spec/GovernedAction/v1/` navs, and the `/contact/` footer, drop their Pricing item instead of gaining an off-origin link (`FRONT_DOOR.md` nav rules). This origin creates no financial claim, matching `/diligence/`. It does not set or confirm any price, and it does not change the product site. Never a11oy.com.

## 2026-09-19

- Add a public-only, dated estate observation and SHA-256-bound `/estate-current.json` pointer. `/status/` separates that observation from the preserved September 4 table, marks observations older than 24 hours STALE, and fails closed to UNAVAILABLE on fetch, scope, date, or digest errors. This is byte consistency, not a signature, live runtime health, or release authorization. The evidence index points to dated origin records without repeating a closed historical www incident as a current outage. CI checks the binding and failure paths.

## 2026-09-12

- Repair the local Alloy desk's boot rendering, draft retention, adapter denial controls, strict watchdog verification, and mobile window sizing. Browser contract now opens the Kernel app, verifies the encrypted submitted payload, exercises Command proof, and measures all eight windows. Local verification uses disposable loopback storage; energy remains MODELED.

- `/models.json` recapture MEASURED 2026-09-12T01:25:04Z: unauthenticated author-list 46 models / 35 datasets / 21 Spaces. Two new cards (`oac-system-health-v1`, `oac-clinical-transport-health-v1`) are CODE_OR_SCRIPTS (Python + JSON, no safetensors). `operational` stays false. Energy stays UNAVAILABLE. Atlas keep-7 not rewritten. `/public-inventory.json` 44/30/48 stays STALE. Does not stamp LIVE or READY. Never a11oy.com.

## 2026-09-11

- `/stalled.json` recapture under named predicate `szl.inventory.surfaces/v1` (MEASURED 2026-09-12T00:19:31Z). Author-list 46 models / 35 datasets / 21 Spaces stays separate from org-card 22 Spaces. KEEP-6 / fold-38 remains `/spaces.json` contract 1.2.0 policy, not Hub live count. `/public-inventory.json` 44/30/48 stays STALE. index.html not rewritten. Not a second flock. `certified=false`. Never a11oy.com.
- `/notes/LYTE_PUBLICATION_DRIFT_2026-09-11.md` admitted as a dated Lyte publication RECORD. 22:34Z recapture: GitHub producer tip, a11oy publisher pin, and Hugging Face Space runtime all `dd17d9f`. A same-day 22:23Z Space healthz of `9af99c9` is superseded, not current. Canonical Forecast Loom hashes ALIGNED. Hash alignment is not a source-revision match. INC-05 remains OPEN (`www.a-11-oy.com` TLS access denied). Product `/lyte` stays STRUCTURAL-ONLY. Proof `www.a11oy.net` 301s to `a11oy.net`, never onto the product host. Does not republish Hugging Face. Does not mint DNS. Never a11oy.com.

## 2026-09-04

- `/estate/plane/` admitted as the on-origin Estate OS control-plane hologram (hash router). PUBLIC_PARTIAL bake 2026-08-29T16:49:00Z. PROPOSE_ONLY minting. Λ remains Conjecture 1 and cannot be promoted. Not a live dashboard. Not product runtime. Not a fourth origin. Catalog hologram stays `/estate/os/`. Later keep-7 recapture stays `/estate.json` and is not overwritten. Linked from `/estate/`. Index, not nav, not the first fold. Does not clone `/verify`. Never a11oy.com.
- `/immune-desk.json` admitted as SOFTWARE operational-rails RECORD for IMMUNE. SENTRA / YAWAR / HUKLLA / locked-8 / NEXUS organ are OPERATIONAL as in-process kernels. Frontier remains MODELED. Energy UNAVAILABLE. Actuation SIMULATED. Does not stamp `/models.json` operational true. Does not rewrite atlas keep-7. pause+private never delete. Never a11oy.com.

## 2026-08-31

- Hub snapshot refresh MEASURED 2026-08-31: unauthenticated author-list reports 44 models, 30 datasets, 47 public Spaces (README profile card is a 48th public Space outside the list API), 21 collections, 1 bucket. Org-authenticated view REPORTED 44 models, 38 datasets (8 private), 49 Spaces (1 private; 47 list rows plus the README profile card are public). GitHub MEASURED 95 public repositories unauthenticated, 103 authenticated (8 private). Public Space count moved 6 → 47 since the 2026-08-30 KEEP-6 cut; the unprivatizing happened off this runtime. Nothing deleted.
- `/estate.json`, `/atlas.json`, `/estate/os/` recaptured to the same observation. `/models.json` admits the 44th card (SZLHOLDINGS/szl-energy-attest, CODE_OR_SCRIPTS). `/notes/` 2026-08-28 hub line marked superseded, not rewritten. Counts are listing metadata only — not quality, safety, or readiness. Λ remains Conjecture 1. Never a11oy.com.


## 2026-08-30

- `/spaces.json` KEEP recut to the MEASURED unauthenticated application six (a11oy, killinchu, immune, szl-khipu, szl-atelier, governed-receipt-verifier). david-leads, anatomy, and szl-real-estate fold onto product paths and stay PAUSED+PRIVATE. nexus dest is `a-11-oy.com/nexus`. Atlas keep-7 at 18:05Z is not rewritten. pause+private, never delete. This runtime has no Hub write token and does not unprivate the 38.
- `/models.json` admitted as the models-and-kernels honesty RECORD. 43 public Hub cards classified TRAINED_WEIGHTS / NANO_SYNTHETIC / KERNEL_SOFTWARE / ROADMAP_EMPTY / CODE_OR_SCRIPTS. operational:false. trained_all:false. Energy UNAVAILABLE. GPU train UNAVAILABLE. P0-JOBLIB remains open. Does not stamp LIVE.
- `/estate.json` recapture 2026-08-30T16:15Z records the KEEP-6 cut and models RECORD pointer. Authenticated public_spaces seven including README is unchanged. Atlas keep-7 is not rewritten. Never a11oy.com.


## 2026-08-29

- `/frontiers.json` compiler SNAPSHOT: Lyte ADMIT STRUCTURAL-ONLY; N1–N25 BLOCKED STARTED; N13/N26 joule UNAVAILABLE; N27 NEVER_DISPATCH. Energy UNAVAILABLE. Not LIVE. Does not rewrite `/factory/`. INC-05 remains operator-only ([a11oy#1497](https://github.com/szl-holdings/a11oy/issues/1497)).
- `/frontiers/` admitted as named-theatres SNAPSHOT (Lyte STRUCTURAL-ONLY; N1–N25 holograms; N26 REPORTED; N27 UNAVAILABLE). Promotion BLOCKED while INC-05 www Cloudflare 404. Does not rewrite `/factory/`. Does not run organs. Does not stamp LIVE. Index, not nav, not the first fold. Never a furniture-shop canonical.
- `/origin/` admitted as INC-05 Origin lock RECORD. MEASURED 2026-08-29T18:53:21Z: product apex Cloudflare HTTP 200; www Cloudflare HTTP 404; proof DNS GitHub Pages; HF custom domain PENDING. Does not mint DNS. Does not stamp LIVE. Does not clone `/verify`. A Grok working copy is not a fourth public origin. Index, not nav, not the first fold. Never a furniture-shop canonical.
- `/estate/` closeout recapture: live a11oy organ signed a DSSE at 18:00Z (MATCH vs Space /cosign.pub keyid 9926bf69; org GitHub key mismatch; HMAC PLACEHOLDER). Envelope is not stored here. Closeout stays BLOCKED_EXTERNAL_AUTHORITY. Unauth Hub author-list MEASURED 6 at 18:37Z is not a rewrite of atlas keep-7. A Grok working copy is not a fourth public origin.
- `/khipu/` admitted as KHIPU RECORD. Original cuts only (PrefixWitness, RouteWitness, TileReceipt, ScoreMod, BlockWitness, YARQA). Duals Ari=GreenLight, Kay Pacha=Anatomy. Kernel is not run here. Evaluate on `a-11-oy.com/khipu`. Holdings hologram at `holdings.a-11-oy.com/khipu/`. CUDA UNAVAILABLE. Energy UNAVAILABLE. Conjecture 1 OPEN. FIFO kernel Hub cards stay 401. Index, not nav, not the first fold.
- `/estate/os/` admitted: static on-origin estate catalog hologram (hash router). PUBLIC_PARTIAL bake 2026-08-29T17:35:39Z from the public GitHub + Hub catalog. READ-ONLY. Not a live dashboard. Not product runtime. Not a fourth origin. Later keep-7 recapture stays `/estate.json` and is not overwritten. Linked from `/estate/`. Index, not nav, not the first fold. Does not clone `/verify`. Λ remains Conjecture 1.
- `/five-space/` admitted as a RECORD stub of the five-space BIND hologram (Command · Loop · Queue · Memory · Ledger). Kernel is not run here. Evaluate on `a-11-oy.com/five-space`. Does not replace `/console`. Does not clone `/verify`. Formula authority NONE. Energy UNAVAILABLE. Λ stays Conjecture 1. Index, not nav, not the first fold.
- `/estate/` recapture 2026-08-29T18:23Z: GitHub 98 / 93 public / 4 open PRs 0 merge-qualified. Hub unauth 43 models / 28 datasets / 6 public Spaces. GPU train UNAVAILABLE (command-lab#12 fail-closed; factory#22 N27; Hub runtimes private). Energy UNAVAILABLE (live NVML not recapturable). Product honesty UNAVAILABLE (a-11-oy.com custom domain PENDING; Space HTTP timeout). Λ stays Conjecture 1. Atlas keep-7 snapshot at 18:05Z is not rewritten. /verify is not cloned. Never a11oy.com.
- `/terra/`, `/aegis/`, `/puriq-markets/`, `/counsel/` admitted as Packet 8 RECORD stubs. Kernel is not run here. Evaluate on `a-11-oy.com/terra` (and the matching vanity paths). Hub Spaces are not required. Same kernel, four desks, not four Spaces. Index, not nav, not the first fold.
- `/decision/` admitted: Packet 8 Decision Integrity RECORD. Terra, Aegis, Puriq Markets, Counsel frozen cases. Formula authority NONE. Kernel is not run here. Evaluate on `a-11-oy.com/decision`. Hub Spaces are not required. Index, not nav, not the first fold.
- Primary nav collapsed to Product | RECORD | Diligence | Atlas | Index. First-fold CTA is RECORD. Product remains a text link. Atelier, Ayllu, experiments, chat, code, notes, and estate live under Index. Nothing deleted.
- `/atelier/` admitted: static forty-model walk of SZLHOLDINGS Hub ids. Canonical playable Space is `https://huggingface.co/spaces/SZLHOLDINGS/szl-atelier`. Source `szl-holdings/szl-atelier`. Nano silhouettes MEASURED in-browser. 1.5B numbers SIGNED, not retrained here. Energy UNAVAILABLE. Not a product runtime. Does not clone `/verify`. Index, not nav, not the first fold.

Dated notes for the a11oy.net proof registry. This is a status pointer, not a product-release feed and not a capability claim.

Public HTML: [https://a11oy.net/notes/](https://a11oy.net/notes/).

## 2026-08-28

- `/estate/` admitted into sitemap, llms.txt, and evidence.json as a dated MEASURED inventory snapshot. Not a live dashboard. Not product runtime. Does not clone `/verify`. Does not depend on #23.
- Live Lean-8 kernel chip on Frontier and hero: GET `/api/a11oy/v1/honest` `locked_formula_count`. Paint **8** only when that field is exactly 8; fetch failure is **UNAVAILABLE**, never a hardcoded 8. Not ROADMAP.
- Kernel chips bind live `https://a-11-oy.com/api/a11oy/v1/honest` `locked_formula_count` and paint **8** only when that field is exactly 8; otherwise **N/A** / **UNAVAILABLE**. Catalog `LOCKED-PROVEN=25` stays labelled as genome catalog, never the kernel, never green. Lean-8 ≠ genome-144. Λ stays Conjecture 1.
- Proof-registry job split: bidirectional **Product | Proof** header (`https://a-11-oy.com` | `https://a11oy.net`), canonical **RECORD** on this origin, 90-second diligence table, GitHub atlas inventory, and these dated notes.
- RECORD is a static, fetchable receipt-record **index** (pointers, not a receipt database). This repository has no receipt store. Live receipts stay on the product Space (Khipu + `/data SZLHOLDINGS/szl-evidence` + `/api/lake/v1/receipts`). Interactive `/verify` remains `https://a-11-oy.com/verify` and is not cloned here. Empty receipt-id listing is `UNAVAILABLE`, never invented IDs.
- CNAME is `a11oy.net`. Live DNS is GitHub Pages. Product `a11oy_canonical_domain.py` may SUNSET-301 `.net` → `.com` only when that Host is routed into the product app. This origin is not a product host. `_headers` remains policy intent; GitHub Pages does not apply it.
- `/health.json` is the only health document: a committed static JSON file. It is not runtime health, not DSSE-LIVE, and not uptime. `signer` is `unavailable` (no DSSE signer and no local key on this origin). `sha` is the last published main revision (`82ad0481753ddd0043e3b55352704e187be14a08`); a static file cannot contain its own future commit SHA. `/readyz` is an HTML directory (Pages may 301 `/readyz` → `/readyz/`) and is not a health URL. `/healthz` is not published (404 HTML) and is not a probe.
- Hub snapshot remains the 2026-08-28 listing (57 public artifacts: 17 models, 27 datasets, 12 collections, 1 bucket). Browser refresh may replace counts when Hub metadata is available; failure stays `UNAVAILABLE` or `PARTIAL`.
- Fall 2026 original cuts and KERNEL originals remain **ROADMAP**, never OPERATIONAL.
- Λ remains Conjecture 1. No SOC 2, FedRAMP, or invented eval figures are published here.

## 2026-08-28 (prior, #19 / #18)

- KERNEL originals listed as ROADMAP with GitHub as canonical source.
- Hub snapshot refreshed from 2026-08-11 counts to 2026-08-28 counts; Fall 2026 cutting cards added as ROADMAP.

## 2026-08-28 (prior, #16)

- Responsive accessibility: small-screen reflow, safe-area geometry, touch/focus sizing, short-screen navigation stacking.
