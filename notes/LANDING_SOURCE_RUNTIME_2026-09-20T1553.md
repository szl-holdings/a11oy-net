# Landing source vs runtime — 2026-09-20T15:53Z

RECORD only. a11oy.net does not run the product. Not LIVE.

## SOURCE MEASURED

- PR: https://github.com/szl-holdings/a11oy/pull/2213 MERGED 2026-09-20T15:49:45Z
- main SHA: `4d838ef36dd10e4020193e669516dfc4bcaff2b2`
- `pages/landing.html#liveBadge` = `BIND · CONNECTING`

## RUNTIME MEASURED

- `https://a-11-oy.com/landing` first paint = `LIVE COMMAND PLATFORM`
- `https://a-11-oy.com/healthz` `commit=c7c0ba17` signer ABSENT

## Verdict

CONFLICT OPEN. merge != deploy. HTTP 200 is not LIVE.
Next safe step: publisher redeploy of admitted main + same-window readback.
Continue a11oy#2189. No second publisher. No JS overlay.

complete: false
