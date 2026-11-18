# Proof-site CDN source-witness cache boundary

**Owner:** `szl-holdings/a11oy-net`; canonical release gate remains
`.github/workflows/edge-security-readback.yml`. This document describes a
**read-only diagnostic**, not a source publisher, cache purge, change in
release authorization, uptime certificate or new background observer.

## The November 17 failure

At 2026-11-17T23:38 UTC the canonical
`https://a11oy.net/.well-known/szl-source.json` returned an older exact
source `d14fe3753a5ef5cfacc75d778aadf22a843939a0` while GitHub protected
main and the successful Pages publisher were at
`12887e34bf5cccdbaa702193b287bb39c3b8fc14`.
The Cloudflare response was `CF-Cache-Status: HIT`, `Age: 13527`.
Four direct GitHub Pages origin IPv4 addresses returned the newer revision;
two query-specific reads through Cloudflare also returned the new revision
(`MISS`, `Age: 0`). This discriminates a stale Cloudflare cached public
object from a failed GitHub Pages deployment. The existing exact-edge-security
check correctly remained FAILED.

These are **dated observations, not continuing claims**. The owner must
re-observe the live state before changing any configuration.

## Reproduce: six bounded GETs, no credentials

Run from this repository with Python 3.12+:

```powershell
python -I -B -m unittest discover -s tests -p test_source_cache_diagnostic.py -v
python -I -B scripts/probe_source_cache_boundary.py `
  --expected-revision 12887e34bf5cccdbaa702193b287bb39c3b8fc14 `
  --output "$env:USERPROFILE\SZL-private-evidence\proof-cache-<UTC>.json"
```

Supply a **new path every time**. Output uses exclusive create and flushes to
disk; it never replaces a prior observation or writes inside the public site.
Keep output private until its identity and content have been reviewed.

The diagnostic retrieves the canonical public HTTPS URL, one cache-key-specific
public GET, and one GET over verified TLS/SNI directly to **each** of GitHub's
four published Pages IPv4 addresses. All request targets are fixed and the
source witness is checked against the existing exact JSON contract. TLS
verification is mandatory; no insecure `--resolve` shortcut or arbitrary
caller-selected URL is permitted. Provider HTTP 401/403/429 ends observation
immediately, without trying a different transport to evade denial.

`CDN_STALE_SOURCE_CONFIRMED_RELEASE_BLOCKED` requires a valid but older
canonical document, all four Pages origins matching the operator-supplied
revision and a fresh key-specific public document also matching. The program
**cannot establish whether the supplied expected SHA is current protected
main**; perform a separate authenticated source-head verification. A matching
canonical and matching four origins is still only a content observation, not
runtime or production qualification. The original exact-source Edge Security
Readback remains the only release check.

All malformed, unavailable, mixed and divergent observations remain
`RELEASE_BLOCKED` or `UNVERIFIED`. The output contains only allowlisted
HTTP response metadata, source-revision and content hashes. No secret, token,
HTTP response body or private path is copied into the public report.

## Canonical repair through the existing Cloudflare owner

The Cloudflare configuration owner is `szl-holdings/szl-estate-os`.
Its baseline (`cloudflare/README.md`) currently does **not** inventory
Cache Rules. A missing ruleset is therefore **UNOBSERVED**, not a finding that
no cache rule exists. Inspect the exact effective ruleset, priority, custom
cache keys, zone ID and current principal's permission **through the
authorized Cloudflare account path**, without changing DNS or orange-cloud
status. Do not create a competing writer.

For this narrow route, the proposed source-owned Cloudflare Cache Rule
expression is:

```text
(http.host eq "a11oy.net" and
 http.request.uri.path eq "/.well-known/szl-source.json")
```

Choose **Bypass cache** for that exact hostname/path. Place the rule such that
no later matching Cache Rule overrides its cache eligibility; Cloudflare rules
are stackable and the *last matching setting* can win. Preserve other paths
and existing x402, Workers, Access, TLS and rate-limit rules. Confirm the
existing owner has approval, scoped authorization and expected-parent source
before applying anything.

After the rule is verified, the owner may perform **a single-file purge of
the exact canonical URL** using the existing Cloudflare account tooling.
Do **not** purge everything, change global cache settings, disable protection
or assume the API response proves eviction. A successful purge response only
establishes request acceptance; independently read back the canonical
unchanged URL across relevant Cloudflare points of presence and verify it
reports the protected-main SHA. Then rerun the established Edge Security
Readback end to end, including TLS, DNSSEC, headers and Pages settings.
No deployment success, paid settlement or production readiness is inferred
from this diagnostic alone.

Sources:
- [GitHub Pages custom-domain address list](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site)
- [Cloudflare Cache Rule match fields and bypass eligibility](https://developers.cloudflare.com/cache/how-to/cache-rules/settings/)
- [Cloudflare Cache Rule ordering](https://developers.cloudflare.com/cache/how-to/cache-rules/order/)
- [Cloudflare selective purge and verification boundary](https://developers.cloudflare.com/cache/how-to/purge-cache/)

## Acceptance tests

The offline regression suite covers duplicate JSON keys, invalid contract,
case-sensitive immutable revision, bounded body and fixed public destinations;
positive canonical/origin parity, stale edge with all origins current, mixed
origins, origin unavailable, authorization-stop at all three probe positions,
header/token non-echo and exclusive append-only receipts.

This is a diagnostic strengthening: not a bypass, not a patch to the old
release gate, not a second publisher. The site remains blocked until the
canonical URL is independently correct and the original gate passes.
