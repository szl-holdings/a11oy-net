# Frontier operator runbook · 2026-09-11

Do these four on owner metal. Proof origin cannot close them.

## 1. Close INC-05 (first)

Cloudflare → domain `a-11-oy.com`:

1. DNS: `www` CNAME to the same target as apex (Space custom domain or the apex itself). No separate broken host.
2. SSL/TLS: Full (strict). Universal cert must cover `a-11-oy.com` and `www.a-11-oy.com`.
3. Hugging Face Space `SZLHOLDINGS/a11oy` → Settings → Custom domains: both apex and `www` READY.
4. Pass: `curl -I https://www.a-11-oy.com/` returns HTTP 200 and the same `x-szl-space: a11oy` as apex.

Fail: TLS `access denied` or HTTP 404. Frontiers stay BLOCKED.

## 2. Persistent signer

On the product Space, persist a P-256 / DSSE key the process can use across restarts.

Pass: `GET https://a-11-oy.com/healthz` shows `signer.status` other than `ABSENT` and `signing_available: true`. Then a lake receipt verifies at `https://a-11-oy.com/verify`.

Do not claim SIGNED from this proof origin. This origin has no signer.

## 3. Exact-SHA publish

Deploy the Space from a known `szl-holdings/a11oy` commit. Then:

```
curl -s https://a-11-oy.com/api/a11oy/v1/honest | jq .git_sha
git -C a11oy rev-parse HEAD
```

Pass: the two strings match. Until they match, publisher pickup stays UNAVAILABLE.

Observed this recapture: live `git_sha` = `9dc70869694f72ba3fb4e632f86f96118ccb39ae`. Do not treat that as GitHub HEAD without a separate `rev-parse`.

## 4. One joule

Attach one real meter (NVML on the Space GPU host, or RAPL `energy_uj` on the box you actually run).

Pass: an energy field on `/honest` or the energy ledger is a number with method + timestamp, not `UNAVAILABLE`.

A prior T4 wrap is not a live meter.

## After the four pass

Only then reopen `/frontiers.json` promotion. Not before.

Public name stays **a11oy**. Product stays `a-11-oy.com`. Proof stays `a11oy.net`. Local kernel RECORD stays `https://a11oy.net/estate/alloy-os/`.
