# FRONT_DOOR — a11oy.net collapse note

**Repo:** `szl-holdings/a11oy-net`
**Origin:** https://a11oy.net
**Branch this note lands on:** `front-door-collapse-note`
**Audience:** maintainers
**Kind:** collapse note. Not a homepage. Not a rewrite.

This file is the information-architecture lock for the proof origin.
It does **not** rewrite `index.html`. That file is ~80KB and is gated by
`scripts/check_proof_surface.py`. Collapse means IA, not deletion, not a
second flagship, not a palette drive-by.

---

## Status

LOCKED for doctrine. IMPLEMENTED for the first fold and primary nav
(HTML + `check_proof_surface.py` in the same PR). Palette, companion
pages, and remaining gates stay as written.

This note is the IA lock. Collapse of the first fold and nav landed with
gate updates in the same PR. Do not re-expand Atelier, Notes, Evidence
index, or Live reads into primary nav. Do not put atelier back on the
first fold.

Current main (tree observed 2026-08-29):

| Item | Value |
| --- | --- |
| `index.html` | 80245 bytes. Gated. Do not rewrite from this note. |
| Gate | `scripts/check_proof_surface.py` |
| Companion gates | `check_diligence_surface.py`, `check_security_headers.py`, `check_honest_kernel_bind.py`, `check_atlas_policy.mjs`, `check_probe_policy.mjs`, `check_honest_kernel_bind.mjs` |
| Host | GitHub Pages. `CNAME` = `a11oy.net`. Not a product host. |
| `health.json` `probe_contract` | `STATIC_DOCUMENT` |
| `health.json` `signer` | `unavailable` |
| `health.json` `sha` | last published main revision (stamped; a static file cannot contain its own future SHA) |

---

## Doctrine LOCKED

Copy these as written. Do not soften.

| Lock | Value |
| --- | --- |
| Origins | Two only. **Product** https://a-11-oy.com · **Proof** https://a11oy.net |
| Foreign | Never `a11oy.com`. Furniture-shop storefront. Scheme omitted on this origin. |
| Verify | Never clone `/verify` onto `.net`. Interactive tool stays https://a-11-oy.com/verify |
| Factory | A bind. Not a second flagship. `szl-holdings/a11oy-factory`. AO-2026-08-29-001. |
| Warhacker | v1.0.0 (2026-06-03) **ARCHIVED**. Fossil. Not the Command Center. Not this registry. |
| Λ | Conjecture 1 **OPEN**. Unconditional uniqueness is false. Conditional Theorem U is axiom-free. Not a theorem. |
| Gold | `#C9B787` = **OPEN**, never proven. Never green-as-proven. |
| Hugging Face | Artifact registry. Not a front door. Not page canonical. Not `sameAs` for these pages. |
| Trust ceiling | `0.97`. Never 100%. |
| Kernel | `c7c0ba17` |
| Doctrine | v11 **LOCKED** |
| This origin | **RECORD**. Atlas, ROADMAP, diligence copy. Not runtime. Not a receipt database. |
| `health.json` | `STATIC_DOCUMENT`. Receiving it proves only that this exact path was served. |

Lean-8 ≠ genome-144. Catalog `LOCKED-PROVEN=25` is genome catalog, never the
kernel, never green. Kernel chips bind live
`https://a-11-oy.com/api/a11oy/v1/honest` `locked_formula_count` and paint **8**
only when that field is exactly 8; otherwise **N/A** / **UNAVAILABLE**. Never
hardcode 8 on this origin.

Formulas never grant authority. Missing evidence is UNKNOWN or FAIL, never PASS.
A listed URL is location only. Reachability, if observed, is REACHABLE only —
never quality, safety, capability, or uptime. Hub `RUNNING` is transport
metadata, not end-to-end capability.

---

## Two origins. Two jobs. No third.

```
Product  https://a-11-oy.com     Command Center. Runtime. /verify. /api/lake. /honest.
Proof    https://a11oy.net      RECORD. Atlas. ROADMAP. Diligence copy.
Hub      https://huggingface.co/SZLHOLDINGS
                                Artifact registry. Not an origin. Not a front door.
```

Header lockup on both origins: **Product | Proof**, those exact words, those
exact URLs.

Do not add:

- a factory origin
- a Hugging Face origin
- a Warhacker origin
- `a11oy.com`
- a cloned `/verify`
- an `/investor` route
- a Ring-1 preview as a public origin
- a third flagship of any name

Factory binds as an A11oy package. Labs are labs. Hugging Face hosts weights,
datasets, Spaces, and listings. This origin lists them. It does not become them.

Product source (`a11oy_canonical_domain.py`) may SUNSET-301 `a11oy.net` →
`a-11-oy.com` only when that Host header is routed into the product app. Do not
assume this origin is a product host. Do not add product routes such as
`/api/lake` here.

---

## What this origin is

RECORD.

Hub atlas and ROADMAP live here, not on `a-11-oy.com`. Diligence copy lives
here. The canonical receipt **index** lives here: pointers, not bodies.

| Surface | Job |
| --- | --- |
| `/` | Proof homepage. First fold names RECORD. Not a product flagship. |
| `/record/` + `/record.json` | Canonical receipt-record index. Pointers only. |
| `/diligence/` | Investor / developer 90-second table. No `/investor`. |
| `/#atlas` + `/atlas.json` | Hub + GitHub inventory. Location, not quality. |
| `/estate/` + `/estate.json` | Dated MEASURED inventory snapshot. Not a live dashboard. |
| `/evidence.json` + `/llms.txt` | Machine contract and automated-reader routing. |
| `/health.json` | Only health document. Static. Not runtime. |
| `/notes/` | Dated notes. Status pointer, not a release feed. |
| Labs under Index | `/atelier/`, `/ayllu/`, `/experiments/`, `/chat/`, `/code/` |

## What this origin is not

- Not runtime.
- Not a receipt database. This repository has no receipt store.
- Not an interactive verifier. `/verify` is not cloned.
- Not a product host. No `/api/lake`. No Khipu. No DSSE signer. No local key.
- Not DSSE-LIVE. `signer` on `health.json` is `unavailable`. `UNSIGNED-LOCAL` is wrong here.
- Not uptime. `health.json` `uptime` is `NOT_MEASURED`.
- Not a Hugging Face Space. Canonical, `og:url`, and `sameAs` stay `https://a11oy.net/...`.
- Not a second Command Center. Frontier cards, atelier, ayllu, experiments, chat, and code are labs or handoffs.
- Not Factory. Factory is a bind on GitHub / a Hub Space, not this front door.
- Not Warhacker. v1.0.0 (2026-06-03) sits in the archive.

Live receipts stay on the product Space:

`Khipu` + `/data SZLHOLDINGS/szl-evidence` + `https://a-11-oy.com/api/lake/v1/receipts`

Empty `receipt_ids` on this origin is **UNAVAILABLE**, not a measured zero.
Do not invent receipt identifiers.

---

## Nav for the proof origin (max 5)

Exactly these, in this order, no more:

1. **Product** — off-origin text link to https://a-11-oy.com. Not a gold button. Not `aria-current`.
2. **Record** — `/record/`. On-origin. Canonical job of this host.
3. **Diligence** — `/diligence/`. On-origin. 90-second table.
4. **Atlas** — `/#atlas` (contract `/atlas.json`). On-origin. Inventory, not quality.
5. **Index** — overflow. Labs, notes, estate, machine contracts, dated walks.

Rules:

- Five items. Not six. Chat, Code, Notes, Atelier, Ayllu, Experiments, Estate,
  Hugging Face, GitHub, DOI, and machine contracts **do not** sit in primary nav.
- Product is a text link, not a competing gold CTA, not a second primary button.
- Proof is the current origin. If an origin-switch remains, it is
  `Product | Proof` with Proof `aria-current="true"`. Product still counts as
  the one off-origin nav item.
- `Chat gateway` and `Code gateway` stay out of top-level nav. They already
  fail `check_proof_surface.py` if promoted. They remain live URLs under Index
  and in the footer as Diligence handoffs.
- Do not add Factory, Warhacker, Hugging Face, or `/verify` to this nav.
- Do not mint `/investor`. Investor review is `/diligence/#investors`.

Current drift (why this note exists): the live root still reads as a flagship
dossier. CHANGELOG 2026-08-29 records “Nav + hero CTA point at `/atelier/`”.
Atelier is a lab. RECORD is the job. Collapse the nav to the five items above
when the gate is updated in the same PR.

---

## First fold

This origin is RECORD.

One sentence the fold must survive on:

> Hub atlas, ROADMAP, and diligence copy live here. This origin is not runtime
> and not a receipt database.

One CTA. Choose `/record/` or `/diligence/`. Not both as gold peers. Not
atelier. Not chat. Not a product Space. Not Hugging Face.

Product appears as a **text link** to https://a-11-oy.com, never a competing
gold button on the first fold.

Interactive `/verify` may be named in body copy as an off-origin tool. It is
not the first-fold CTA. It is not cloned.

Do not mint a second homepage. `/` remains the proof homepage. `/record/`
remains the canonical RECORD index. They are not two flagships. The fold on
`/` points at RECORD so the host stops competing with `a-11-oy.com`.

---

## Index — labs stay here

Index is the overflow, not a fifth flagship and not a new homepage.

Keep every lab URL live. Move them out of primary nav and off the first fold.
Discover them from Index (section, dropdown, or in-page catalog — implementation
choice, not a new origin).

| Path | Index role | Bound |
| --- | --- | --- |
| `/atelier/` | Forty-model Hub walk | Static. Canonical playable Space is `huggingface.co/spaces/SZLHOLDINGS/szl-atelier`. Not product runtime. |
| `/decision/` | Packet 8 Decision Integrity RECORD | Static. Kernel is not run here. Evaluate on `a-11-oy.com/decision`. Hub Spaces not required. |
| `/ayllu/` | Counsel showcase | Proof-origin showcase. Does not run the council. Lab. |
| `/experiments/` | Experimental split-outs | EXPERIMENTAL. Not locked-8. Not a Λ theorem. |
| `/chat/` | Diligence handoff | One-line gateway. No local execution claim. |
| `/code/` | Diligence handoff | One-line gateway. No local execution claim. |
| `/notes/` | Dated notes | Status pointer, not a capability feed. |
| `/estate/` + `/estate.json` | Inventory snapshot | MEASURED counts are not quality. Not a live dashboard. |
| `/readyz/` | HTML reachability | Not a health URL. Pages may 301 `/readyz` → `/readyz/`. |
| `/api/build-info/` | Static surface scope | No immutable source-revision claim. |
| `/evidence.json` `/llms.txt` `/record.json` `/atlas.json` `/health.json` | Machine contracts | Stay fetchable. Not nav peers. |

Footer may keep Diligence handoffs (`/chat/`, `/code/`) discoverable. Footer
is not a second primary nav.

---

## Do not delete

Collapse means IA, not deletion. The following current a11oy-net paths **must
remain**. Removing any of them is a contract break.

### Primary inventory (do not delete)

| Path | Why it stays |
| --- | --- |
| `index.html` | Proof homepage. ~80KB. Gated by `check_proof_surface.py`. Do not rewrite from this note. Do not delete. |
| `record/` | Canonical RECORD HTML. Pointers, not a receipt store. |
| `diligence/` | Investor / developer diligence copy. No `/investor` substitute. |
| `atlas.json` | Fetchable Hub + GitHub inventory. |
| `health.json` | Only health document. `STATIC_DOCUMENT`. |
| `estate.json` | Dated MEASURED inventory contract. |
| `evidence.json` | Machine-readable evidence boundaries. |
| `atelier/` | Lab walk. Index, not nav. Keep the URL. |
| `decision/` | Packet 8 RECORD. Index, not nav. Keep the URL. Kernel is not run here. |
| `ayllu/` | Lab showcase. Index, not nav. Keep the URL. |
| `experiments/` | Lab. Index, not nav. Keep the URL. |
| `chat/` | Diligence handoff. Keep the URL. |
| `code/` | Diligence handoff. Keep the URL. |
| `notes/` | Dated notes. Keep the URL. |
| `readyz/` | HTML directory reachability. Not a health URL. Keep the URL. |
| `.well-known` | `security.txt`. Canonical security-reporting route. |

### Supporting contracts the gate also requires (do not delete)

These are not optional just because they are not in the primary list.

| Path | Why it stays |
| --- | --- |
| `record.json` | RECORD machine contract. |
| `estate/` | Estate snapshot HTML. Sitemap + llms.txt already admit it. |
| `CNAME` | Must remain `a11oy.net`. |
| `.nojekyll` | Required to publish `.well-known/security.txt` on GitHub Pages. |
| `404.html` | Branded recovery. |
| `assets/` | Mark, social preview, `diligence.css`, `kanchay.css`. |
| `llms.txt` | Automated-reader routing. |
| `robots.txt` `sitemap.xml` | Public discovery. |
| `site.webmanifest` `manifest.webmanifest` | Byte-identical aliases. |
| `_headers` | Versioned edge-security **policy**. GitHub Pages does not apply it. `live_edge_security_headers_deployment_proven=false`. |
| `api/build-info/` | Static build-info surface. |
| `scripts/` | Proof, diligence, atlas, probe, kernel, health-stamp, header checks. |
| `.github/workflows/` | Link & asset check, overclaim guard, edge-security readback. |
| `README.md` `CHANGELOG.md` `LICENSE` | Source-of-truth copy and Apache-2.0. |

Do not add, as deletions-in-disguise:

- `/verify` or `/verify/`
- `/investor`
- `/healthz` or `healthz.html`
- `/api/lake`
- `/receipts` or `record/receipts`
- `*.dsse.json`
- a Hugging Face Space as `rel=canonical` or JSON-LD `sameAs`
- the furniture-shop host with a scheme (this origin names `a11oy.com` without `https://` and never stamps that URL)

---

## `health.json` is STATIC_DOCUMENT

`/health.json` is a committed static JSON file on GitHub Pages.

Receiving it proves only that this exact path was served.

It is not:

- runtime health
- product readiness
- DSSE-LIVE
- an uptime claim
- a process ping (GitHub Pages has no process to ping)

`signer` is `unavailable`: this origin has no DSSE signer and no local key.
`UNSIGNED-LOCAL` would be wrong here. `sha` is the last published main
revision; a static file cannot contain its own future commit SHA. ÑAWI owns
the locked-proven formula count; this document does not.

`/readyz/` is an HTML directory route. GitHub Pages may 301 `/readyz` to
`/readyz/`. That 301 lands on HTML, not JSON. Do not treat `/readyz` as a
health URL.

`/healthz` is not published. GitHub Pages returns 404 HTML for that path.
That 404 is not a health probe. Do not register `/healthz` as a health URL.

---

## Hugging Face is not a front door

https://huggingface.co/SZLHOLDINGS is the public artifact registry.

- List it from Atlas.
- Do not make it canonical for pages on this origin.
- Do not use a Space URL as `og:url`.
- Do not treat Hub `RUNNING` as capability.
- Interactive Spaces stay out of generated atlas cards.
- Killinchu-named resources stay excluded from this proof front door.
- Pin/unpin is Hub admin work, not a Pages edit.

The product Space (`SZLHOLDINGS/a11oy`) is runtime. This origin links to it
as location. It is not this origin.

---

## Factory is a bind. Warhacker is archive.

**Factory** (`szl-holdings/a11oy-factory`, Hub `SZLHOLDINGS/a11oy-factory`):
bind, not a second flagship. Do not put Factory on this nav. Do not mint a
factory homepage on `a11oy.net`. Hub visibility is not mutated from this
repository without `HF_TOKEN`.

**Warhacker** v1.0.0 (2026-06-03):
ARCHIVED. Keep the GitHub release record so the ledger stays honest. Do not
pin Warhacker on this front door. Do not treat the tag as production-certified.
Do not confuse it with `szl-formulas` or kernel `c7c0ba17`.

---

## Gold is OPEN. Λ stays a conjecture.

`#C9B787` means OPEN, never proven.

Λ = Conjecture 1 remains OPEN. Do not paint it as LOCKED, MEASURED-proven, or
green. Do not say theorem. Trust ceiling stays 0.97.

Maintainer hazard: the current gated `index.html` uses `--gold:#d7b96b`, and
`scripts/check_proof_surface.py` currently asserts `#c9b787` is absent from
that file. Doctrine gold and the gated palette are **not** the same lock.
Do not stamp `#C9B787` into `index.html` from this note. Palette migration,
if it happens, is a coordinated HTML + gate change in a later PR. Until then,
the semantic lock still holds: gold means OPEN, never proven, on every surface
that speaks doctrine.

---

## What “collapse” is allowed to change later

When a follow-up PR is ready to implement this note, it may:

1. Collapse primary nav to the five items above.
2. Collapse the first fold to RECORD + one CTA (`/record/` or `/diligence/`)
   + Product as a text link.
3. Move atelier / ayllu / experiments / chat / code / notes / estate off the
   first fold and out of primary nav, into Index.
4. Stop competing with `a-11-oy.com` as a second product homepage.
5. Update `scripts/check_proof_surface.py` (and diligence / sitemap / JSON-LD
   / README assertions) **in the same PR** so the new IA is what the gate
   checks.

It may not:

- Delete any path in the inventory above.
- Rewrite `index.html` from *this* note’s landing commit.
- Clone `/verify`.
- Host receipts, lake, or a DSSE signer.
- Add `a11oy.com`.
- Promote Factory, Warhacker, or Hugging Face to origin or primary nav.
- Mint `/investor` or a second homepage.
- Register `/readyz` or `/healthz` as health.
- Claim Λ proven, trust 1.0, or gold-as-proven.
- Hardcode kernel 8.

`check_proof_surface.py` currently requires, among other things:

- `Product ↗` in the root nav and a single `origin-switch`
- Proof as the current origin
- `RECORD` in nav
- Chat / Code absent from top-level nav, present in the footer
- a root link to `/atelier/`
- `Hub atlas and ROADMAP live here`
- no `/verify` or `/investor` routes
- `--gold:#d7b96b` and `#c9b787` absent
- `health.json` `probe_contract == STATIC_DOCUMENT`
- sitemap locs for `/`, `/ayllu/`, `/experiments/`, `/diligence/`, `/record/`,
  `/estate/`, `/notes/`, `/chat/`, `/code/`, `/atelier/`, `/decision/`

Those assertions are why this note exists as a note. Implement collapse by
changing the gate and the HTML together. Do not fight the gate.

---

## Evidence labels (unchanged)

| Label | Meaning on this surface |
| --- | --- |
| `MEASURED` | Direct observation with a disclosed source and context. |
| `REPORTED` | Public upstream metadata; not independently measured here. |
| `MODELED` | Simulated or analytically derived. |
| `HEURISTIC` | A bounded rule or score, not a proof. |
| `UNKNOWN` | Evidence is insufficient. |
| `UNAVAILABLE` | The relevant source could not be inspected. |
| `ROADMAP` | Not OPERATIONAL. Fall 2026 cuts and KERNEL originals stay here. |
| `OPEN` | Gold. Never proven. Λ lives here. |
| `ARCHIVED` | Warhacker v1.0.0 (2026-06-03). Put aside. |

Operational status is separate from evidence class.

---

## Local verification (unchanged)

No build step. From the repository root:

```bash
python scripts/check_proof_surface.py
python scripts/check_diligence_surface.py
python scripts/check_security_headers.py
python scripts/check_honest_kernel_bind.py
node scripts/check_atlas_policy.mjs
node scripts/check_probe_policy.mjs
node scripts/check_honest_kernel_bind.mjs
```

This note does not weaken those checks.

---

## One-line lock

**Product is a-11-oy.com. Proof is a11oy.net. This origin is RECORD.
Collapse the door. Do not delete the house.**
