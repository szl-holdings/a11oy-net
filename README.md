# A11oy Proof Registry

<p align="center">
  <img src="assets/a11oy-net-social.png" alt="A11oy.net — separately hosted first-party proof registry" width="960" />
</p>

[`a11oy.net`](https://a11oy.net) is the separately hosted first-party **RECORD**
for [A11oy](https://a-11-oy.com). Domain lock: this origin is the proof registry.
Hub atlas and ROADMAP live here, not on `.com`. Interactive `/verify` stays on
[a-11-oy.com/verify](https://a-11-oy.com/verify) and is not cloned. There is no `/investor` route;
investor review is [`/diligence/#investors`](https://a11oy.net/diligence/#investors).

Header on both origins: **Product | Proof**. Product ↗ → `https://a-11-oy.com`.
Proof is the current surface here.

The product experience and the evidence experience are intentionally separate.
A product link proves location and remains `NOT PROBED · UNKNOWN` here. A
schema-valid public Hub runtime stage is only a bounded, point-in-time
`REPORTED` transport observation. Neither proves capability, safety, quality,
uptime, or deployed equivalence.

## Start here

- **Review evidence:** open [a11oy.net](https://a11oy.net).
- **Use the product:** open [a-11-oy.com](https://a-11-oy.com).
- **Verify a receipt:** use the [public verifier](https://a-11-oy.com/verify).
- **Inspect source:** begin with the
  [A11oy repository](https://github.com/szl-holdings/a11oy).
- **Browse public artifacts:** inspect
  [SZLHOLDINGS on Hugging Face](https://huggingface.co/SZLHOLDINGS).

## Audience routes

- **Evidence registry:** [`/`](https://a11oy.net/) is the RECORD: Hub atlas,
  ROADMAP cards, and browser-observed metadata live here.
- **Investor diligence:** [`/diligence/#investors`](https://a11oy.net/diligence/#investors)
  sequences the public thesis, controls, source, boundaries, and estate links.
- **Developer diligence:** [`/diligence/#developers`](https://a11oy.net/diligence/#developers)
  starts from executable validation and machine-readable contracts.
- **Product handoffs:** [`/chat/`](https://a11oy.net/chat/) and
  [`/code/`](https://a11oy.net/code/) remain live URLs as one-line Diligence
  handoffs, not top-level nav peers. They do not claim product readiness.
  Interactive receipt verify stays on [a-11-oy.com/verify](https://a-11-oy.com/verify).
- **Machine readers:** [`/evidence.json`](https://a11oy.net/evidence.json) states
  the evidence contract, while [`/llms.txt`](https://a11oy.net/llms.txt) routes
  automated readers without extending any claim.
- **Static route scope:** [`/readyz/`](https://a11oy.net/readyz/) proves only
  that its static route responded, and
  [`/api/build-info/`](https://a11oy.net/api/build-info/) does not publish or
  claim an immutable source revision or product-runtime readiness.

## Architecture

The registry is a dependency-light static site served by GitHub Pages behind
Cloudflare DNS.

```text
visitor browser
  ├─ static evidence and product links → NOT PROBED · UNKNOWN
  └─ public metadata reads → Hugging Face APIs
       ├─ fail-closed Space-stage policy → bounded REPORTED transport state
       └─ shared admission policy → reported artifact cards
```

No application backend, account, token, model weight, dataset payload, or
private resource is required. The browser reads public Hub listing metadata for
models, datasets, collections, and buckets, plus transport-stage metadata for
two curated public Spaces. Interactive Spaces are not enumerated into generated
registry cards, and Killinchu-named resources remain excluded.

If an upstream read fails, the page preserves the static evidence index and
reports `PARTIAL` or `UNAVAILABLE`; it does not substitute cached capability
claims.

## Evidence contract

| Label | Meaning on this surface |
| --- | --- |
| `MEASURED` | Direct observation with a disclosed source and context. |
| `REPORTED` | Public upstream metadata; not independently measured here. |
| `MODELED` | Simulated or analytically derived. |
| `HEURISTIC` | A bounded rule or score, not a proof. |
| `UNKNOWN` | Evidence is insufficient. |
| `UNAVAILABLE` | The relevant source could not be inspected. |

Operational status is separate from evidence class. Hub `RUNNING` state is
transport metadata and does not establish end-to-end capability.

The formal canon remains explicit: exactly eight formulas are locked-proven;
Lambda uniqueness remains **Conjecture 1**, advisory and not a theorem. The
trust ceiling is `0.97`, never 100%.

## Local verification

The repository has no build step. Run the dependency-free contracts from the
repository root:

```bash
python scripts/check_proof_surface.py
python scripts/check_diligence_surface.py
python scripts/check_security_headers.py
node scripts/check_atlas_policy.mjs
node scripts/check_probe_policy.mjs
```

The checks validate:

- canonical, Open Graph, Twitter, JSON-LD, sitemap, and security discovery;
- local links and social-preview assets;
- keyboard navigation, live-state announcements, and no-script behavior;
- fail-closed atlas admission and honest evidence labels;
- fail-closed Hugging Face runtime-stage classification while product links stay unprobed;
- exclusion of interactive Spaces and Killinchu-named resources;
- the investor/developer diligence room, static machine contract, `llms.txt`,
  branded 404, SVG mark, and no-JavaScript route boundaries;
- the committed edge-security contract without promoting it to deployed state.

## Repository map

| Path | Responsibility |
| --- | --- |
| `index.html` | Accessible product narrative, live reads, and registry UI. |
| `diligence/index.html`, `assets/diligence.css` | Investor/developer diligence paths and print-safe presentation. |
| `evidence.json`, `llms.txt` | Machine-readable evidence boundaries and automated-reader routing. |
| `readyz/index.html` | Static front-door reachability only; never product readiness. |
| `api/build-info/index.html` | Static surface scope without an immutable build-identity claim. |
| `chat/index.html`, `code/index.html` | Truthful cross-domain product gateways with no local execution claim. |
| `404.html`, `assets/a11oy-mark.svg` | Branded recovery route and shared SVG identity mark. |
| `site.webmanifest`, `manifest.webmanifest` | Byte-identical application metadata aliases. |
| `scripts/atlas_policy.js` | Shared browser/Node artifact-admission policy. |
| `scripts/check_atlas_policy.mjs` | Executable policy regression contract. |
| `scripts/probe_policy.js` | Shared browser/Node runtime-metadata observation policy. |
| `scripts/check_probe_policy.mjs` | Malformed, transitional, terminal, and `RUNNING` stage regressions. |
| `scripts/check_proof_surface.py` | Metadata, accessibility, and truth-surface guard. |
| `scripts/check_diligence_surface.py` | Diligence, machine-contract, no-script, and recovery-route guard. |
| `_headers`, `scripts/check_security_headers.py` | Versioned edge policy and fail-closed static/live validator. |
| `robots.txt`, `sitemap.xml` | Public search discovery. |
| `.well-known/security.txt` | Canonical security-reporting route. |

## Publishing and security

Changes ship through a protected pull request. The exact reviewed head must
pass the link, asset, proof-surface, admission-policy, and doctrine guards
before normal merge.

`_headers` is a versioned edge-security contract, not a live-header receipt. Its
live deployment state remains **UNKNOWN** on this candidate:
`live_edge_security_headers_deployment_proven=false` records only that no proof
has been attached; it is not an observation that deployment is absent. No
source-bound readback URI, UTC
observation time, or source revision is attached. CI recomputes every inline
script hash and rejects a weakened or incomplete contract, but GitHub Pages does not
apply this file. Its presence is therefore not deployment evidence. The domain
must be cut over to a compatible edge host or proxy before those response
headers are live. After cutover, run **Edge Security Readback**; it compares the
root and web-manifest responses with the exact committed contract and fails
closed on missing or changed headers. Update the deployment-state evidence only
after that exact live readback succeeds.

Report vulnerabilities through the organization
[security policy](https://github.com/szl-holdings/.github/security/policy).
Do not include secrets or sensitive evidence in a public issue.

Apache-2.0 licensed. Copyright 2026 SZL Holdings.
