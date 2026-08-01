# A11oy Proof Registry

<p align="center">
  <img src="assets/a11oy-net-social.png" alt="A11oy.net — independent proof registry" width="960" />
</p>

[`a11oy.net`](https://a11oy.net) is the independent public evidence surface for
[A11oy](https://a-11-oy.com). It gives investors, operators, developers, and
assurance reviewers a short path to runtime truth, receipt verification,
source, benchmarks, formal evidence, and public artifact metadata without
requiring the product interface.

The product experience and the evidence experience are intentionally separate.
A link proves location. A browser probe proves reachability only. Neither proves
capability, safety, quality, or deployed equivalence.

## Start here

- **Review evidence:** open [a11oy.net](https://a11oy.net).
- **Use the product:** open [a-11-oy.com](https://a-11-oy.com).
- **Verify a receipt:** use the [public verifier](https://a-11-oy.com/verify).
- **Inspect source:** begin with the
  [A11oy repository](https://github.com/szl-holdings/a11oy).
- **Browse public artifacts:** inspect
  [SZLHOLDINGS on Hugging Face](https://huggingface.co/SZLHOLDINGS).

## Architecture

The registry is a dependency-light static site served by GitHub Pages behind
Cloudflare DNS.

```text
visitor browser
  ├─ static evidence and source links
  ├─ opaque reachability probes → a-11-oy.com
  └─ public metadata reads → Hugging Face APIs
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

The repository has no build step. Run both dependency-free contracts from the
repository root:

```bash
python scripts/check_proof_surface.py
node scripts/check_atlas_policy.mjs
```

The checks validate:

- canonical, Open Graph, Twitter, JSON-LD, sitemap, and security discovery;
- local links and social-preview assets;
- keyboard navigation, live-state announcements, and no-script behavior;
- fail-closed atlas admission and honest evidence labels;
- exclusion of interactive Spaces and Killinchu-named resources.

## Repository map

| Path | Responsibility |
| --- | --- |
| `index.html` | Accessible product narrative, live reads, and registry UI. |
| `scripts/atlas_policy.js` | Shared browser/Node artifact-admission policy. |
| `scripts/check_atlas_policy.mjs` | Executable policy regression contract. |
| `scripts/check_proof_surface.py` | Metadata, accessibility, and truth-surface guard. |
| `robots.txt`, `sitemap.xml` | Public search discovery. |
| `.well-known/security.txt` | Canonical security-reporting route. |

## Publishing and security

Changes ship through a protected pull request. The exact reviewed head must
pass the link, asset, proof-surface, admission-policy, and doctrine guards
before normal merge.

Report vulnerabilities through the organization
[security policy](https://github.com/szl-holdings/.github/security/policy).
Do not include secrets or sensitive evidence in a public issue.

Apache-2.0 licensed. Copyright 2026 SZL Holdings.
