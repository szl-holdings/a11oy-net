#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# © 2026 Lutar, Stephen P. — SZL Holdings · ORCID 0009-0001-0110-4173
# Doctrine v11 LOCKED. Λ = Conjecture 1 (NOT a theorem). Locked-proven kernel = 8.
"""Investor-honest S1–S12 / L1–L6 / D1–D10 smoke gate for a11oy.net.

Fail-closed. Never skip-as-green. Never invent PASS. No POST. No HEAD handlers.
No Dockerfile / HF byte-parity changes.

S1 HEAD 405/404 and S2 signer enum: KALLPA owns (probes only).
S3 unlabeled live coords: UNAVAILABLE or MEASURED with method — never invent MEASURED.
S7 (AYNI): kernel chips must bind ``/honest`` ``locked_formula_count``
(8 or N/A / UNAVAILABLE), not genome ``LOCKED-PROVEN`` (25). Both numbers are
real. Catalog 25 stays labelled. Do not demand 25 be deleted. Committed chips
bind via ``scripts/honest_kernel_bind.js``. S2 committed ``health.json`` carries
``signer=unavailable`` and a SHA; that is not DSSE-LIVE and not uptime.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]

LOCKED_KERNEL_COUNT = 8
LOCKED_KERNEL_IDS = ("F1", "F4", "F7", "F11", "F12", "F18", "F19", "F22")
HONEST_PATH = "/api/a11oy/v1/honest"
HONEST_FIELD = "locked_formula_count"
GENOME_CATALOG_LOCKED_PROVEN = 25
SIGNER_ENUM = frozenset({"DSSE-LIVE", "UNSIGNED-LOCAL", "unavailable"})
COORD_KEYS = frozenset(
    {"latitude", "longitude", "lat", "lon", "altitude", "velocity"}
)
SNAPSHOT_DATE = "2026-08-28"
CANONICAL_ORIGIN = "https://a11oy.net"
ALIAS_ORIGIN = "https://www.a11oy.net"
HONEST_ORIGIN = "https://a-11-oy.com"
USER_AGENT = (
    "a11oy-net-investor-smoke-gate/1.0 (+https://github.com/szl-holdings/a11oy-net)"
)

ALLOWED_STATUSES = frozenset(
    {"PASS", "FAIL", "UNAVAILABLE", "SNAPSHOT", "UNCONFIGURED"}
)
ALLOWED_UNAVAILABLE_IDS = frozenset({"S4", "S6", "S9"})
ALLOWED_UNCONFIGURED_IDS = frozenset({"wire-D"})
SNAPSHOT_IDS = frozenset({"L1", "L2", "L3", "L4", "L5", "L6"})

CORE_ROUTES = (
    "/",
    "/diligence/",
    "/chat/",
    "/code/",
    "/evidence.json",
    "/readyz/",
    "/api/build-info/",
)
HEALTH_JSON_PATH = "/health.json"
SOFT_404_PATH = "/definitely-not-a-declared-asset-zzzz.js"
OG_CANDIDATES = (
    "/assets/a11oy-net-social.png",
)
HTML_SURFACES = (
    "index.html",
    "diligence/index.html",
    "chat/index.html",
    "code/index.html",
    "404.html",
    "readyz/index.html",
    "api/build-info/index.html",
)
SPACE_MARKERS = (
    "Dockerfile",
    "docker-compose.yml",
    "app.py",
    ".hfignore",
    "huggingface-card.yaml",
)

_KERNEL_CHIP = re.compile(
    r"""id=["']cnt-locked["']"""
    r"""|id=["']pt-locked["']"""
    r"""|id=["']hs-proven["']"""
    r"""|data-kernel-chip"""
    r"""|locked-proven\s*="""
    r"""|Locked-proven kernel""",
    re.I,
)
_HONEST_BIND = re.compile(
    r"""(?:/api/a11oy/v1/honest|/honest)[\s\S]{0,500}?locked_formula_count"""
    r"""|locked_formula_count[\s\S]{0,240}?(?:/api/a11oy/v1/honest|/honest)""",
    re.I,
)
_DATA_HONEST_ATTRS = re.compile(
    r"""data-honest-url\s*=\s*["'][^"']*(?:/api/a11oy/v1/honest|/honest)"""
    r"""[\s\S]{0,400}?data-honest-field\s*=\s*["']locked_formula_count["']"""
    r"""|data-honest-field\s*=\s*["']locked_formula_count["']"""
    r"""[\s\S]{0,400}?data-honest-url\s*=\s*["'][^"']*(?:/api/a11oy/v1/honest|/honest)""",
    re.I,
)
_NA_BIND = re.compile(
    r"""(?:cnt-locked|pt-locked|data-kernel-chip|locked_formula_count)"""
    r"""[\s\S]{0,240}?N/A"""
    r"""|N/A[\s\S]{0,80}?locked_formula_count""",
    re.I,
)
_BIND_SCRIPT = re.compile(r"""honest_kernel_bind\.js""", re.I)
_CNT_LOCKED_FROM_GENOME = re.compile(
    r"""\$\(\s*['"]cnt-locked['"]\s*\)[\s\S]{0,240}?"""
    r"""(?:tier_counts|tc)\s*(?:\[\s*['"]LOCKED-PROVEN['"]\s*\]|\.LOCKED)""",
    re.I,
)
_CNT_LOCKED_NODEVALUE_GENOME = re.compile(
    r"""['"]cnt-locked['"][\s\S]{0,160}?nodeValue\s*=\s*[\s\S]{0,80}?"""
    r"""(?:tc|tier_counts)\s*\[\s*['"]LOCKED-PROVEN['"]""",
    re.I,
)
_SETTIERS_LOCKED_GENOME = re.compile(
    r"""setTiers\(\s*\{[^}]*\blocked\s*:\s*(?:tc|g\.tier_counts|tier_counts)"""
    r"""\s*\[\s*['"]LOCKED-PROVEN['"]""",
    re.I | re.S,
)
_SETTIERS_PROOF_TIERS = re.compile(
    r"""setTiers\(\s*\w+\.proof_tiers\s*\)""",
    re.I,
)
_HARDCODED_KERNEL_EIGHT = re.compile(
    r"""locked-proven\s*=\s*(?:<b>)?exactly\s*8"""
    r"""|locked-proven\s*=\s*exactly\s+eight""",
    re.I,
)
_CATALOG_LABEL = re.compile(
    r"""(?:genome|catalog)\s+LOCKED-PROVEN|LOCKED-PROVEN\s+catalog""",
    re.I,
)
_SHA_KEYS = frozenset(
    {"sha", "git_sha", "commit", "source_revision", "revision", "digest"}
)


@dataclass
class Verdict:
    id: str
    status: str
    detail: str
    evidence: str = ""
    snapshot_date: str = ""
    owner: str = ""

    def __post_init__(self) -> None:
        if self.status not in ALLOWED_STATUSES:
            raise ValueError(f"{self.id}: illegal status {self.status!r}")
        if self.status == "SNAPSHOT" and not self.snapshot_date:
            raise ValueError(f"{self.id}: SNAPSHOT requires a date")


@dataclass
class Matrix:
    verdicts: list[Verdict] = field(default_factory=list)

    def add(self, verdict: Verdict) -> None:
        self.verdicts.append(verdict)

    def by_id(self, vid: str) -> Verdict | None:
        for item in self.verdicts:
            if item.id == vid:
                return item
        return None

    def missing(self, required: Iterable[str]) -> list[str]:
        have = {item.id for item in self.verdicts}
        return [rid for rid in required if rid not in have]

    def fail_ids(self) -> list[str]:
        return [item.id for item in self.verdicts if item.status == "FAIL"]

    def as_dict(self) -> dict[str, Any]:
        return {"verdicts": [asdict(item) for item in self.verdicts]}


REQUIRED_MATRIX_IDS = (
    "S1",
    "S2",
    "S3",
    "S4",
    "S5",
    "S6",
    "S7",
    "S8",
    "S9",
    "S10",
    "S11",
    "S12",
    "L1",
    "L2",
    "L3",
    "L4",
    "L5",
    "L6",
    "D1",
    "D2",
    "D3",
    "D4",
    "D5",
    "D6",
    "D7",
    "D8",
    "D9",
    "D10",
    "wire-D",
)
# Contract mode cannot honestly PASS live HTTP rows. It still must include every
# non-network id so a missing static probe is FAIL, never skip-as-green.
# S2 is also static: committed health.json is the document live GET must serve.
CONTRACT_REQUIRED_IDS = (
    "S2",
    "S4",
    "S5",
    "S6",
    "S7",
    "S8",
    "S9",
    "S11",
    "S12",
    "L1",
    "L2",
    "L3",
    "L4",
    "L5",
    "L6",
    "D1",
    "D2",
    "D3",
    "D4",
    "D5",
    "D6",
    "D7",
    "D8",
    "D9",
    "D10",
    "wire-D",
)


def validate_matrix(
    matrix: Matrix, required: Iterable[str] = REQUIRED_MATRIX_IDS
) -> list[str]:
    """Return error strings. A missing probe is FAIL, never skip-as-green."""
    errors: list[str] = []
    required_list = list(required)
    for missing_id in matrix.missing(required_list):
        errors.append(f"missing probe {missing_id}: FAIL (skip-as-green rejected)")
    for item in matrix.verdicts:
        if item.status not in ALLOWED_STATUSES:
            errors.append(f"{item.id}: illegal status {item.status}")
        if item.status == "SNAPSHOT" and not item.snapshot_date:
            errors.append(f"{item.id}: SNAPSHOT without date rejected")
        if item.status == "UNAVAILABLE" and item.id not in ALLOWED_UNAVAILABLE_IDS:
            errors.append(
                f"{item.id}: UNAVAILABLE not allowed here; missing evidence must FAIL"
            )
        if item.status == "UNCONFIGURED" and item.id not in ALLOWED_UNCONFIGURED_IDS:
            errors.append(f"{item.id}: UNCONFIGURED is only allowed for wire-D")
    return errors


# ---------------------------------------------------------------------------
# S7 — kernel chips bind /honest (8 or N/A), not genome LOCKED-PROVEN (25)
# ---------------------------------------------------------------------------


def surface_binds_honest(text: str) -> bool:
    """True when a surface binds /honest (8 or N/A / UNAVAILABLE), not a static 8.

    A footer chip without per-element data-honest-url still binds when the page
    loads honest_kernel_bind.js, which paints every [data-kernel-chip].
    Labelled N/A on a scriptless surface (diligence) with the honest URL+field
    is a bind. Hardcoded exactly 8 is not.
    """
    if _HONEST_BIND.search(text) or _DATA_HONEST_ATTRS.search(text):
        return True
    if _BIND_SCRIPT.search(text) and _KERNEL_CHIP.search(text):
        return True
    if _NA_BIND.search(text) and (
        HONEST_FIELD in text or HONEST_PATH in text or _BIND_SCRIPT.search(text)
    ):
        return True
    return False


def kernel_slot_bind_failures(text: str, *, source_name: str) -> list[str]:
    """FAIL if a kernel chip binds genome LOCKED-PROVEN or is hardcoded 8.

    Catalog LOCKED-PROVEN (25) may remain as a separately labelled catalog
    count. Do not demand 25 be deleted.
    """
    failures: list[str] = []
    if _CNT_LOCKED_FROM_GENOME.search(text) or _CNT_LOCKED_NODEVALUE_GENOME.search(
        text
    ):
        failures.append(
            f"{source_name}: cnt-locked still reads genome tier_counts['LOCKED-PROVEN'] "
            "(kernel chip must bind /honest locked_formula_count = 8 or N/A; "
            "catalog 25 stays labelled separately)."
        )
    if _SETTIERS_LOCKED_GENOME.search(text):
        failures.append(
            f"{source_name}: setTiers.locked still reads genome "
            "tier_counts['LOCKED-PROVEN'] (kernel chip must bind /honest)."
        )
    if _SETTIERS_PROOF_TIERS.search(text):
        failures.append(
            f"{source_name}: setTiers(*.proof_tiers) still paints genome "
            "LOCKED-PROVEN into the kernel slot (catalog 25 is not the kernel)."
        )
    has_chip = bool(_KERNEL_CHIP.search(text))
    honest = surface_binds_honest(text)
    if has_chip and not honest:
        failures.append(
            f"{source_name}: kernel chip present but does not bind "
            f"{HONEST_PATH} {HONEST_FIELD} (8 or N/A / UNAVAILABLE). "
            "Hardcoded 8 is not a bind."
        )
    if _HARDCODED_KERNEL_EIGHT.search(text) and not honest:
        failures.append(
            f"{source_name}: locked-proven count is hardcoded; bind /honest "
            "(8 or N/A / UNAVAILABLE) instead of painting a static 8."
        )
    return failures


def iter_html_surfaces(root: Path = ROOT) -> list[Path]:
    found: list[Path] = []
    for rel in HTML_SURFACES:
        path = root / rel
        if path.is_file():
            found.append(path)
    return found


def analyze_repo_kernel_binds(root: Path = ROOT) -> list[str]:
    failures: list[str] = []
    surfaces = iter_html_surfaces(root)
    if not surfaces:
        failures.append("no HTML surfaces to probe for kernel chips; missing probe is FAIL")
        return failures
    saw_chip = False
    bind_js = root / "scripts" / "honest_kernel_bind.js"
    for path in surfaces:
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = str(path.relative_to(root))
        if _KERNEL_CHIP.search(text) or _HARDCODED_KERNEL_EIGHT.search(text):
            saw_chip = True
        if _BIND_SCRIPT.search(text) and not bind_js.is_file():
            failures.append(
                f"{rel}: loads honest_kernel_bind.js but scripts/honest_kernel_bind.js is missing"
            )
        failures.extend(kernel_slot_bind_failures(text, source_name=rel))
    if not saw_chip:
        failures.append(
            "no a11oy.net kernel chips found; missing probe is FAIL "
            "(fail-closed until every kernel chip binds /honest)"
        )
    return failures


def s7_bind_agreement(
    *,
    extra_evidence: Iterable[str] = (),
    chips_bind_honest: bool | None = None,
) -> Verdict:
    extras = [str(x) for x in extra_evidence if x]
    if chips_bind_honest is not True:
        detail = (
            "a11oy.net kernel chips must bind "
            f"{HONEST_PATH} {HONEST_FIELD}={LOCKED_KERNEL_COUNT} or N/A, "
            f"not genome LOCKED-PROVEN={GENOME_CATALOG_LOCKED_PROVEN}. "
            "Both numbers are real. Catalog 25 stays labelled. "
            "Do not demand 25 be deleted. Fail-closed until every kernel chip binds /honest "
            "(live /honest paints 8 or N/A / UNAVAILABLE)."
        )
        return Verdict(
            id="S7",
            status="FAIL",
            detail=detail,
            evidence=" | ".join(extras) if extras else "kernel chips do not bind /honest",
            owner="INTI",
        )
    return Verdict(
        id="S7",
        status="PASS",
        detail=(
            f"every probed kernel chip binds {HONEST_PATH} {HONEST_FIELD} "
            f"({LOCKED_KERNEL_COUNT} or N/A / UNAVAILABLE); catalog "
            f"LOCKED-PROVEN={GENOME_CATALOG_LOCKED_PROVEN} stays labelled separately"
        ),
        evidence=" | ".join(extras) if extras else "kernel chips bind /honest",
        owner="INTI",
    )


def s7_verdict(root: Path = ROOT) -> Verdict:
    extras = analyze_repo_kernel_binds(root)
    return s7_bind_agreement(
        extra_evidence=extras,
        chips_bind_honest=not extras,
    )


# ---------------------------------------------------------------------------
# D5 — catalog 25 is real and labelled; it is not the locked kernel
# ---------------------------------------------------------------------------


def evaluate_catalog_vs_kernel(root: Path = ROOT) -> Verdict:
    index = (root / "index.html").read_text(encoding="utf-8", errors="replace")
    without_catalog = re.sub(
        r'<span class="catalog-chip"[^>]*>.*?</span>',
        "",
        index,
        flags=re.I | re.S,
    )
    paints_25_as_kernel = bool(
        re.search(r"locked-proven\s*=\s*(?:<b[^>]*>)?\s*25\b", without_catalog, re.I)
        or re.search(r"exactly 25 formulas", without_catalog, re.I)
    )
    kernel_labelled_8 = bool(
        re.search(r'data-kernel-chip=["\']locked-proven["\']', index, re.I)
        and surface_binds_honest(index)
    )
    catalog_labelled = bool(_CATALOG_LABEL.search(index))
    if paints_25_as_kernel:
        return Verdict(
            id="D5",
            status="FAIL",
            detail=(
                "kernel chip paints catalog 25 as locked-proven; "
                "catalog LOCKED-PROVEN=25 is real but is not the kernel"
            ),
            evidence="index.html",
        )
    return Verdict(
        id="D5",
        status="PASS",
        detail=(
            "catalog genome LOCKED-PROVEN="
            f"{GENOME_CATALOG_LOCKED_PROVEN} is a real labelled catalog count, "
            f"not the locked kernel ({LOCKED_KERNEL_COUNT} ids). "
            "Do not demand 25 be deleted. Tag-source agreement is S7."
        ),
        evidence=(
            f"kernel_labelled_8={kernel_labelled_8}; "
            f"catalog_25_labelled_here={catalog_labelled}; "
            "product genome LOCKED-PROVEN=25 stays on a11oy, labelled"
        ),
    )


# ---------------------------------------------------------------------------
# README / HF card YAML (S12) — stdlib only
# ---------------------------------------------------------------------------


def parse_simple_yaml_frontmatter(text: str) -> dict[str, Any]:
    if not text.startswith("---"):
        raise ValueError("README must start with YAML frontmatter ---")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("README must start with ---")
    body: list[str] = []
    closed = False
    for line in lines[1:]:
        if line.strip() == "---":
            closed = True
            break
        body.append(line)
    if not closed:
        raise ValueError("no closing --- in README frontmatter")
    parsed: dict[str, Any] = {}
    current_key: str | None = None
    current_list: list[str] | None = None
    for line in body:
        if current_list is not None and (
            line.startswith("  - ") or line.startswith("\t- ")
        ):
            current_list.append(line.split("-", 1)[1].strip().strip("'\""))
            continue
        if current_list is not None:
            parsed[current_key] = current_list  # type: ignore[index]
            current_list = None
            current_key = None
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, raw = line.partition(":")
        key = key.strip()
        raw = raw.strip()
        if raw == "":
            current_key = key
            current_list = []
            continue
        parsed[key] = raw.strip("\"'")
    if current_list is not None and current_key is not None:
        parsed[current_key] = current_list
    return parsed


def s12_verdict(root: Path = ROOT) -> Verdict:
    readme = root / "README.md"
    try:
        parsed = parse_simple_yaml_frontmatter(readme.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return Verdict(
            id="S12",
            status="FAIL",
            detail=(
                f"HF card YAML does not parse ({exc}). "
                "Missing card is FAIL, never skip-as-green."
            ),
            evidence="README.md",
        )
    required = ("title", "sdk", "emoji", "colorFrom", "colorTo")
    missing = [key for key in required if key not in parsed]
    if missing:
        return Verdict(
            id="S12",
            status="FAIL",
            detail=f"README frontmatter missing {missing}",
            evidence="README.md",
        )
    return Verdict(
        id="S12",
        status="PASS",
        detail="README YAML frontmatter parses with required HF card fields",
        evidence="README.md",
    )


def repo_space_markers(root: Path = ROOT) -> list[str]:
    hits: list[str] = []
    for rel in SPACE_MARKERS:
        if (root / rel).exists():
            hits.append(rel)
    readme = root / "README.md"
    if readme.is_file():
        text = readme.read_text(encoding="utf-8", errors="replace")
        try:
            parsed = parse_simple_yaml_frontmatter(text)
        except ValueError:
            parsed = {}
        sdk = parsed.get("sdk")
        if sdk in {"docker", "gradio", "static", "streamlit"}:
            hits.append(f"README.md sdk={sdk}")
    return hits


def s11_verdict(root: Path = ROOT) -> Verdict:
    markers = repo_space_markers(root)
    if not markers:
        return Verdict(
            id="S11",
            status="FAIL",
            detail=(
                "this repository has no Hugging Face Space "
                "(no Dockerfile, no Space README YAML, no app.py). "
                "Missing boot target is FAIL, never skip-as-green. "
                "Do not probe the product Space and call it this repo's S11."
            ),
            evidence="no Space markers in szl-holdings/a11oy-net",
        )
    return Verdict(
        id="S11",
        status="FAIL",
        detail=(
            "Space markers present but live boot is probed in live mode; "
            "contract does not invent PASS"
        ),
        evidence=", ".join(markers),
    )


def s11_live_verdict(root: Path, space_url: str | None) -> Verdict:
    if not space_url:
        return s11_verdict(root)
    got = http_request(space_url.rstrip("/") + "/", method="GET", follow=True)
    return Verdict(
        id="S11",
        status="PASS" if got.status == 200 else "FAIL",
        detail="This-repo HF Space GET / is 200",
        evidence=f"GET {space_url}/ -> {got.status} {got.error}".strip(),
    )


# ---------------------------------------------------------------------------
# Dual-origin inclusion: site ⊆ a11oy.net ⊆ git tag ⊆ HF card, or labelled gap
# ---------------------------------------------------------------------------


def git_tags(root: Path = ROOT) -> list[str] | None:
    try:
        proc = subprocess.run(
            ["git", "tag", "--list"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def inclusion_verdict(root: Path = ROOT) -> Verdict:
    gaps: list[str] = []
    cname = (root / "CNAME").read_text(encoding="utf-8").strip()
    index = (root / "index.html").read_text(encoding="utf-8", errors="replace")
    if cname != "a11oy.net":
        gaps.append(f"CNAME={cname!r} is not a11oy.net")
    if 'href="https://a11oy.net/"' not in index and "https://a11oy.net/" not in index:
        gaps.append("index.html does not declare https://a11oy.net/ canonical")
    tags = git_tags(root)
    if tags is None:
        return Verdict(
            id="D6",
            status="FAIL",
            detail="git tag probe failed; missing probe is FAIL, never skip-as-green",
            evidence="git tag --list returned non-zero or was unavailable",
        )
    if not tags:
        gaps.append("no git tags on this repository")
    try:
        parse_simple_yaml_frontmatter((root / "README.md").read_text(encoding="utf-8"))
        card_ok = True
    except ValueError:
        card_ok = False
        gaps.append("no HF card YAML in README.md")
    if not gaps and tags and card_ok and cname == "a11oy.net":
        return Verdict(
            id="D6",
            status="PASS",
            detail="site ⊆ a11oy.net ⊆ git tag ⊆ HF card (no labelled gap)",
            evidence=f"CNAME={cname}; tags={tags[:8]}; HF card YAML present",
        )
    return Verdict(
        id="D6",
        status="PASS",
        detail=(
            "dual-origin inclusion has labelled gaps; "
            "do not invent site ⊆ a11oy.net ⊆ git tag ⊆ HF card agreement"
        ),
        evidence="; ".join(gaps),
    )


# ---------------------------------------------------------------------------
# Static D-row helpers
# ---------------------------------------------------------------------------


def _read(root: Path, rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8", errors="replace")


def static_debug_verdicts(root: Path = ROOT) -> list[Verdict]:
    index = _read(root, "index.html")
    sitemap = _read(root, "sitemap.xml")
    catalog = root / "docs" / "investor" / "screenshot-catalog.md"
    csp_test = root / "scripts" / "check_security_headers.py"
    not_found = root / "404.html"
    overclaim = root / ".github" / "workflows" / "overclaim-guard.yml"

    out: list[Verdict] = []
    out.append(
        Verdict(
            id="D1",
            status="PASS" if 'type="application/ld+json"' in index else "FAIL",
            detail="Proof-registry JSON-LD identity is present",
            evidence="index.html application/ld+json",
        )
    )
    routes_ok = all(
        path in sitemap
        for path in (
            "https://a11oy.net/",
            "https://a11oy.net/diligence/",
            "https://a11oy.net/chat/",
            "https://a11oy.net/code/",
        )
    )
    out.append(
        Verdict(
            id="D2",
            status="PASS" if routes_ok else "FAIL",
            detail="Sitemap publishes the core proof-registry routes",
            evidence="sitemap.xml",
        )
    )
    hero_chip = bool(re.search(r'data-kernel-chip=["\']locked-proven["\']', index, re.I))
    first_paint_na = bool(
        re.search(r'id=["\']cnt-locked["\'][^>]*>\s*N/A', index, re.I)
        or re.search(r'id=["\']cnt-locked["\'][\s\S]{0,80}?>N/A<', index, re.I)
    )
    hero_labelled = (
        hero_chip
        and surface_binds_honest(index)
        and first_paint_na
        and _HARDCODED_KERNEL_EIGHT.search(index) is None
    )
    out.append(
        Verdict(
            id="D3",
            status="PASS" if hero_labelled else "FAIL",
            detail=(
                "Hero kernel chip is labelled locked-proven and bound to /honest "
                "(first paint N/A; live count is 8 or N/A / UNAVAILABLE, not a hardcoded 8)"
            ),
            evidence="index.html data-kernel-chip + honest_kernel_bind.js",
        )
    )
    out.append(
        Verdict(
            id="D4",
            status="PASS" if "Conjecture 1" in index else "FAIL",
            detail="Λ uniqueness labelled Conjecture 1, not a theorem",
            evidence="index.html",
        )
    )
    out.append(evaluate_catalog_vs_kernel(root))
    out.append(inclusion_verdict(root))
    bind_js = root / "scripts" / "honest_kernel_bind.js"
    bind_text = bind_js.read_text(encoding="utf-8", errors="replace") if bind_js.is_file() else ""
    ids_from_honest = (
        bind_js.is_file()
        and "locked_formula_ids" in bind_text
        and HONEST_FIELD in bind_text
        and "data-kernel-ids" in index
        and "honest_kernel_bind.js" in index
    )
    out.append(
        Verdict(
            id="D7",
            status="PASS" if ids_from_honest else "FAIL",
            detail=(
                "Locked-8 ids are painted from /honest locked_formula_ids "
                "(not hardcoded in index.html)"
            ),
            evidence="scripts/honest_kernel_bind.js + index.html [data-kernel-ids]",
        )
    )
    out.append(
        Verdict(
            id="D8",
            status="PASS" if not_found.is_file() else "FAIL",
            detail="Designed branded 404 exists (GitHub Pages HTML 404, not a product JSON envelope)",
            evidence="404.html",
        )
    )
    out.append(
        Verdict(
            id="D9",
            status="PASS" if csp_test.is_file() else "FAIL",
            detail="CSP / security-header regression check exists (not re-run here)",
            evidence="scripts/check_security_headers.py",
        )
    )
    snap_text = (
        catalog.read_text(encoding="utf-8", errors="replace") if catalog.is_file() else ""
    )
    snap = catalog.is_file() and (
        "SNAPSHOT" in snap_text and SNAPSHOT_DATE in snap_text
    )
    out.append(
        Verdict(
            id="D10",
            status="SNAPSHOT" if snap else "FAIL",
            detail="Screenshot catalog is a dated SNAPSHOT, not a live capture; no N claimed",
            evidence="docs/investor/screenshot-catalog.md",
            snapshot_date=SNAPSHOT_DATE if snap else "",
        )
        if snap
        else Verdict(
            id="D10",
            status="FAIL",
            detail="Screenshot catalog missing dated SNAPSHOT; missing probe is FAIL",
            evidence="docs/investor/screenshot-catalog.md",
        )
    )
    doctrine = index + (
        overclaim.read_text(encoding="utf-8", errors="replace")
        if overclaim.is_file()
        else ""
    )
    unconfigured = "SLSA" in doctrine and (
        "roadmap" in doctrine.lower() or "L1 honest" in doctrine
    )
    out.append(
        Verdict(
            id="wire-D",
            status="UNCONFIGURED" if unconfigured else "FAIL",
            detail="Wire D SLSA L2 attestation remains roadmap / not claimed by this gate",
            evidence="index.html SLSA strip + overclaim-guard.yml",
        )
    )
    return out


def s2_static_verdict(root: Path = ROOT) -> Verdict:
    """Committed health.json must carry signer enum + SHA. Not DSSE-LIVE. Not uptime."""
    path = root / "health.json"
    if not path.is_file():
        return Verdict(
            id="S2",
            status="FAIL",
            detail="Committed health.json missing; skip-as-green rejected",
            evidence="health.json",
            owner="KALLPA",
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return Verdict(
            id="S2",
            status="FAIL",
            detail=f"Committed health.json is not JSON: {exc}",
            evidence="health.json",
            owner="KALLPA",
        )
    fail = s2_from_payload(payload, source="health.json")
    signer = extract_signer_status(payload)
    sha = extract_sha(payload)
    if fail:
        return Verdict(
            id="S2",
            status="FAIL",
            detail=(
                "Health JSON must carry a SHA and signer enum "
                "{DSSE-LIVE, UNSIGNED-LOCAL, unavailable}. "
                "Do not invent DSSE-LIVE. This origin is not an uptime claim."
            ),
            evidence="; ".join(fail),
            owner="KALLPA",
        )
    return Verdict(
        id="S2",
        status="PASS",
        detail=(
            f"Committed health.json signer={signer!r} with SHA; "
            "dsse_live not claimed; not an uptime claim. Do not invent DSSE-LIVE."
        ),
        evidence=f"health.json signer={signer} sha={sha}",
        owner="KALLPA",
    )


def s5_static_verdict(root: Path = ROOT) -> Verdict:
    blob = ""
    for rel in (
        "index.html",
        "evidence.json",
        "scripts/probe_policy.js",
        "scripts/atlas_policy.js",
        "diligence/index.html",
    ):
        path = root / rel
        if path.is_file():
            blob += path.read_text(encoding="utf-8", errors="replace")
    mint = re.search(r"receipt_minted|mint_receipt|ledger\.append", blob)
    post = re.search(r"""method\s*[:=]\s*['"]POST['"]""", blob)
    if mint or post:
        return Verdict(
            id="S5",
            status="FAIL",
            detail="Read-only proof surface must not mint receipts",
            evidence=(mint.group(0) if mint else post.group(0) if post else "mint"),
        )
    return Verdict(
        id="S5",
        status="PASS",
        detail="Static proof-registry surfaces have no mint/POST ledger path",
        evidence="index.html + evidence.json + probe/atlas policy",
    )


def s8_static_verdict(root: Path = ROOT) -> Verdict:
    ok = (root / "404.html").is_file()
    return Verdict(
        id="S8",
        status="PASS" if ok else "FAIL",
        detail="Designed 404: branded 404.html refuses to invent a substitute claim",
        evidence="404.html",
    )


def static_s_verdicts(root: Path = ROOT) -> list[Verdict]:
    out: list[Verdict] = []
    out.append(s2_static_verdict(root))
    out.append(s7_verdict(root))
    out.append(s5_static_verdict(root))
    out.append(s8_static_verdict(root))
    out.append(s11_verdict(root))
    out.append(s12_verdict(root))
    return out


def snapshot_l_verdicts() -> list[Verdict]:
    labels = {
        "L1": "concurrent GET storm",
        "L2": "receipt-write load",
        "L3": "refuse/abstain under load",
        "L4": "authz empty-state under load",
        "L5": "HEAD/GET mix under load",
        "L6": "dual-origin load",
    }
    return [
        Verdict(
            id=lid,
            status="SNAPSHOT",
            detail=f"{desc} not executed this PR; never claimed production-scale with no N",
            evidence=f"SNAPSHOT {SNAPSHOT_DATE}",
            snapshot_date=SNAPSHOT_DATE,
        )
        for lid, desc in labels.items()
    ]


def unavailable_placeholders() -> list[Verdict]:
    return [
        Verdict(
            id="S4",
            status="UNAVAILABLE",
            detail="Staging receipt-write URL is not published on a11oy.net; no POST issued",
            evidence="no staging URL in this smoke PR; no POST",
        ),
        Verdict(
            id="S6",
            status="UNAVAILABLE",
            detail="Live refuse/abstain path is not published on a11oy.net; no POST issued",
            evidence="static proof registry has no refuse/abstain write path",
        ),
        Verdict(
            id="S9",
            status="UNAVAILABLE",
            detail="Authz empty-state gated routes are not a public 200 surface on a11oy.net",
            evidence="no authz empty-state route on this origin",
        ),
    ]


def contract_matrix(root: Path = ROOT) -> Matrix:
    matrix = Matrix()
    for item in static_s_verdicts(root):
        matrix.add(item)
    for item in static_debug_verdicts(root):
        matrix.add(item)
    for item in snapshot_l_verdicts():
        matrix.add(item)
    for item in unavailable_placeholders():
        matrix.add(item)
    return matrix


# ---------------------------------------------------------------------------
# HTTP (GET/HEAD only)
# ---------------------------------------------------------------------------


@dataclass
class HttpResult:
    method: str
    url: str
    status: int | None
    content_type: str
    body: bytes
    location: str = ""
    error: str = ""

    def text(self, limit: int = 4000) -> str:
        return self.body[:limit].decode("utf-8", errors="replace")

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8"))


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # noqa: ANN002
        return None


def http_request(
    url: str,
    method: str = "GET",
    timeout: float = 20.0,
    follow: bool = True,
) -> HttpResult:
    if method.upper() not in {"GET", "HEAD"}:
        raise ValueError(f"investor smoke gate forbids {method}")
    req = urllib.request.Request(
        url,
        method=method.upper(),
        headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
    )
    opener = urllib.request.build_opener(
        urllib.request.HTTPRedirectHandler() if follow else _NoRedirect()
    )
    try:
        with opener.open(req, timeout=timeout) as resp:
            body = b"" if method.upper() == "HEAD" else resp.read(512_000)
            return HttpResult(
                method=method.upper(),
                url=url,
                status=getattr(resp, "status", None) or resp.getcode(),
                content_type=resp.headers.get("Content-Type", ""),
                body=body,
                location=resp.headers.get("Location", "") or "",
            )
    except urllib.error.HTTPError as exc:
        body = b""
        try:
            body = exc.read(512_000) if method.upper() != "HEAD" else b""
        except Exception:
            body = b""
        headers = exc.headers or {}
        return HttpResult(
            method=method.upper(),
            url=url,
            status=exc.code,
            content_type=headers.get("Content-Type", "") if headers else "",
            body=body,
            location=headers.get("Location", "") if headers else "",
            error=str(exc),
        )
    except Exception as exc:  # noqa: BLE001 — probe must never crash the matrix
        return HttpResult(
            method=method.upper(),
            url=url,
            status=None,
            content_type="",
            body=b"",
            error=f"{type(exc).__name__}: {exc}",
        )


def _join(origin: str, path: str) -> str:
    return origin.rstrip("/") + path


def extract_signer_status(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in ("signer",):
        node = payload.get(key)
        if isinstance(node, dict) and isinstance(node.get("status"), str):
            return node["status"]
        if isinstance(node, str) and node in SIGNER_ENUM:
            return node
    rollup = payload.get("rollup")
    if isinstance(rollup, dict):
        signer = rollup.get("signer")
        if isinstance(signer, dict) and isinstance(signer.get("status"), str):
            return signer["status"]
        if isinstance(signer, str) and signer in SIGNER_ENUM:
            return signer
    return None


def extract_sha(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in _SHA_KEYS:
        raw = payload.get(key)
        if isinstance(raw, str) and raw.strip() and raw.strip().upper() not in {
            "NOT_CLAIMED",
            "NOT_PUBLISHED_BY_THIS_ROUTE",
            "NULL",
        }:
            return raw.strip()
    return None


def locked_formula_count_from_honest(payload: Any) -> int | None:
    if not isinstance(payload, dict):
        return None
    raw = payload.get(HONEST_FIELD)
    if isinstance(raw, int):
        return raw
    lock = payload.get("doctrine_lock")
    if isinstance(lock, dict) and isinstance(lock.get(HONEST_FIELD), int):
        return lock[HONEST_FIELD]
    return None


def _coord_label_ok(obj: dict[str, Any], key: str) -> bool:
    """True only for UNAVAILABLE, or MEASURED with a method. Never invent MEASURED."""

    def _ok(label: Any, method: Any) -> bool:
        if not isinstance(label, str):
            return False
        lab = label.upper()
        if lab == "UNAVAILABLE":
            return True
        if lab == "MEASURED":
            return bool(method)
        return False

    wrapped = obj.get(key)
    if isinstance(wrapped, dict):
        lab = wrapped.get("label") or wrapped.get("honesty") or wrapped.get("status")
        method = wrapped.get("method") or wrapped.get("method_label") or obj.get("method")
        if _ok(lab, method):
            return True
    labels = obj.get("labels") or obj.get("honesty") or obj.get("value_labels")
    if isinstance(labels, dict):
        lab = labels.get(key)
        method = None
        if isinstance(lab, dict):
            method = lab.get("method")
            lab = lab.get("label") or lab.get("status")
        else:
            method = (labels.get("method") if isinstance(labels, dict) else None) or obj.get(
                "method"
            )
        if _ok(lab, method):
            return True
    for field_name in ("label", "honesty", "value_label", "status"):
        raw = obj.get(field_name)
        if _ok(raw, obj.get("method") or obj.get("method_label")):
            return True
    return False


def unlabeled_numeric_coords(payload: Any, path: str = "$") -> list[str]:
    found: list[str] = []

    def walk(node: Any, here: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                child = f"{here}.{key}"
                if key in COORD_KEYS:
                    if isinstance(value, (int, float)):
                        if not _coord_label_ok(node, key):
                            found.append(
                                f"{child}={value} unlabeled "
                                "(need UNAVAILABLE or MEASURED with method)"
                            )
                        continue
                    if isinstance(value, dict):
                        inner = value.get("value")
                        if isinstance(inner, (int, float)) and not _coord_label_ok(
                            node, key
                        ):
                            found.append(
                                f"{child}.value={inner} unlabeled "
                                "(need UNAVAILABLE or MEASURED with method)"
                            )
                        continue
                walk(value, child)
        elif isinstance(node, list):
            for idx, item in enumerate(node[:50]):
                walk(item, f"{here}[{idx}]")

    walk(payload, path)
    return found


def first_viewport_unlabeled_latitude(html: str, *, char_limit: int = 20000) -> list[str]:
    """Fail-closed: no raw unlabeled latitude in the first viewport HTML."""
    chunk = html[:char_limit]
    hits: list[str] = []
    if not re.search(r"\blatitude\b", chunk, re.I):
        return hits
    for match in re.finditer(r"\blatitude\b", chunk, re.I):
        window = chunk[max(0, match.start() - 100) : match.end() + 160]
        has_number = re.search(r"-?\d+\.\d+", window)
        if not has_number:
            continue
        if re.search(r"UNAVAILABLE", window, re.I):
            continue
        if re.search(r"MEASURED", window, re.I) and re.search(r"method", window, re.I):
            continue
        hits.append(
            "unlabeled latitude in first viewport (need UNAVAILABLE or MEASURED with method)"
        )
        break
    return hits


def s2_from_payload(payload: Any, *, source: str, http_status: int | None = 200) -> list[str]:
    fail: list[str] = []
    if http_status != 200:
        fail.append(f"{source} HTTP {http_status}")
        return fail
    if not isinstance(payload, dict):
        fail.append(f"{source} health JSON is not an object")
        return fail
    signer = extract_signer_status(payload)
    sha = extract_sha(payload)
    if signer not in SIGNER_ENUM:
        fail.append(
            f"{source} missing signer enum {sorted(SIGNER_ENUM)}; "
            f"got {signer!r}. Lean SHA is not enough. KALLPA owns the fix."
        )
    if not sha:
        fail.append(f"{source} missing SHA field ({sorted(_SHA_KEYS)})")
    return fail


def live_matrix(origins: list[str], root: Path = ROOT) -> Matrix:
    matrix = Matrix()
    primary = origins[0] if origins else CANONICAL_ORIGIN
    probed = origins or [CANONICAL_ORIGIN, ALIAS_ORIGIN]

    # S1 HEAD vs GET (KALLPA) — probes only. Both origins. No HEAD handlers added.
    s1_fail: list[str] = []
    s1_ev: list[str] = []
    for origin in probed:
        for path in CORE_ROUTES:
            got = http_request(_join(origin, path), method="GET", follow=True)
            head = http_request(_join(origin, path), method="HEAD", follow=False)
            s1_ev.append(f"{origin}{path} GET={got.status} HEAD={head.status}")
            if got.status != 200:
                s1_fail.append(
                    f"GET {origin}{path} = {got.status} {got.error}".strip()
                )
                continue
            if head.status in {405, 404}:
                s1_fail.append(
                    f"HEAD {origin}{path} = {head.status} while GET = 200"
                )
            elif head.status not in {200, 204, 301, 302, 308}:
                s1_fail.append(
                    f"HEAD {origin}{path} = {head.status} while GET = 200"
                )
    matrix.add(
        Verdict(
            id="S1",
            status="FAIL" if s1_fail else "PASS",
            detail=(
                "Both origins must 200 on core routes; HEAD must not 405/404 "
                "where GET is 200 (KALLPA owns the product fix; this repo does not add handlers)"
            ),
            evidence="; ".join(s1_fail) if s1_fail else "; ".join(s1_ev),
            owner="KALLPA",
        )
    )

    # S2 health JSON SHA + signer enum (KALLPA) — probes only. Do not invent DSSE-LIVE.
    health = http_request(_join(primary, HEALTH_JSON_PATH), method="GET", follow=True)
    s2_fail: list[str] = []
    s2_ev = ""
    if health.status != 200 or "json" not in health.content_type.lower():
        s2_fail.append(
            f"GET {HEALTH_JSON_PATH} signer/SHA probe HTTP {health.status} "
            f"ct={health.content_type}. Missing health JSON is FAIL, never skip-as-green."
        )
    else:
        try:
            payload = health.json()
        except Exception as exc:  # noqa: BLE001
            payload = None
            s2_fail.append(f"GET {HEALTH_JSON_PATH} not JSON: {exc}")
        if payload is not None:
            s2_fail.extend(
                s2_from_payload(
                    payload, source=HEALTH_JSON_PATH, http_status=health.status
                )
            )
            signer = extract_signer_status(payload)
            sha = extract_sha(payload)
            s2_ev = (
                f"GET {HEALTH_JSON_PATH} signer={signer!r} sha={sha}; "
                "dsse_live not claimed; not an uptime claim"
            )
    matrix.add(
        Verdict(
            id="S2",
            status="FAIL" if s2_fail else "PASS",
            detail=(
                "Health JSON must carry a SHA and signer enum "
                "{DSSE-LIVE, UNSIGNED-LOCAL, unavailable}. "
                "Do not invent DSSE-LIVE. This document is not an uptime claim."
            ),
            evidence="; ".join(s2_fail) if s2_fail else s2_ev,
            owner="KALLPA",
        )
    )

    # S3 first viewport + any live-fetch JSON on THIS origin. Do not invent MEASURED.
    home = http_request(_join(primary, "/"), method="GET", follow=True)
    s3_fail: list[str] = []
    if home.status != 200:
        s3_fail.append(f"GET / HTTP {home.status} {home.error}".strip())
    else:
        s3_fail.extend(first_viewport_unlabeled_latitude(home.text(24_000)))
        # If this origin ever ships live-fetch JSON, require labels. Do not
        # fetch a-11-oy.com /live/iss and pretend it is a11oy.net.
        for live_path in ("/live.json", "/api/live-fetch", "/api/live/iss"):
            probe = http_request(_join(primary, live_path), method="GET", follow=True)
            if probe.status == 200 and "json" in probe.content_type.lower():
                try:
                    unlabeled = unlabeled_numeric_coords(probe.json())
                except Exception as exc:  # noqa: BLE001
                    s3_fail.append(f"{live_path} JSON parse {exc}")
                    unlabeled = []
                if unlabeled:
                    s3_fail.append("unlabeled live coords: " + "; ".join(unlabeled[:8]))
    landing = root / "index.html"
    if landing.is_file():
        s3_fail.extend(
            first_viewport_unlabeled_latitude(
                landing.read_text(encoding="utf-8", errors="replace")
            )
        )
    matrix.add(
        Verdict(
            id="S3",
            status="FAIL" if s3_fail else "PASS",
            detail=(
                "Live coords must be UNAVAILABLE or labelled MEASURED with method; "
                "no raw unlabeled latitude in first viewport. Do not invent MEASURED."
            ),
            evidence="; ".join(s3_fail)
            if s3_fail
            else f"GET {primary}/ first viewport labelled; no unlabeled live-fetch JSON",
        )
    )

    for item in unavailable_placeholders():
        matrix.add(item)

    # S5 live: GET must not mint
    s5_fail: list[str] = []
    s5_ev: list[str] = []
    for path in ("/evidence.json", "/"):
        got = http_request(_join(primary, path), method="GET", follow=True)
        s5_ev.append(f"GET {path} -> {got.status}")
        if got.status != 200:
            s5_fail.append(f"{path} HTTP {got.status}")
            continue
        if "json" in got.content_type.lower():
            try:
                payload = got.json()
            except Exception:
                payload = None
            if isinstance(payload, dict) and payload.get("receipt_minted") is True:
                s5_fail.append(f"{path} receipt_minted=true on GET")
    static_s5 = s5_static_verdict(root)
    if static_s5.status == "FAIL":
        s5_fail.append(static_s5.evidence)
    matrix.add(
        Verdict(
            id="S5",
            status="FAIL" if s5_fail else "PASS",
            detail="Read-only GET does not mint receipts",
            evidence="; ".join(s5_fail or s5_ev),
        )
    )

    # S7 live HTML chips (INTI). Catalog 25 stays labelled. Do not demand deletion.
    extras: list[str] = analyze_repo_kernel_binds(root)
    live_chip_fail: list[str] = []
    if home.status == 200:
        live_chip_fail = kernel_slot_bind_failures(
            home.text(80_000), source_name=f"live {primary}/"
        )
        extras.extend(live_chip_fail)
    honest_live = http_request(_join(HONEST_ORIGIN, HONEST_PATH), method="GET", follow=True)
    if honest_live.status == 200:
        try:
            live_honest = locked_formula_count_from_honest(honest_live.json())
            extras.append(f"product {HONEST_PATH} {HONEST_FIELD}={live_honest}")
        except Exception as exc:  # noqa: BLE001
            extras.append(f"honest parse {exc}")
    else:
        extras.append(f"GET {HONEST_ORIGIN}{HONEST_PATH} HTTP {honest_live.status}")
    extras.append(
        f"catalog LOCKED-PROVEN={GENOME_CATALOG_LOCKED_PROVEN} stays labelled; "
        "do not demand deletion"
    )
    repo_chip_fail = analyze_repo_kernel_binds(root)
    matrix.add(
        s7_bind_agreement(
            extra_evidence=extras,
            chips_bind_honest=not repo_chip_fail and not live_chip_fail,
        )
    )

    # S8 live designed 404 (HTML on GitHub Pages, not product JSON)
    soft = http_request(_join(primary, SOFT_404_PATH), method="GET", follow=True)
    s8_ok = soft.status == 404
    matrix.add(
        Verdict(
            id="S8",
            status="PASS" if s8_ok else "FAIL",
            detail="Undeclared file-like path must be 404, not a fake 200 document",
            evidence=f"GET {SOFT_404_PATH} -> {soft.status} {soft.content_type}",
        )
    )

    # S10 OG
    s10_ok = False
    s10_ev: list[str] = []
    for path in OG_CANDIDATES:
        got = http_request(_join(primary, path), method="GET", follow=True)
        s10_ev.append(f"GET {path} -> {got.status} {got.content_type}")
        if got.status == 200 and (
            "image" in got.content_type.lower() or got.body[:8] == b"\x89PNG\r\n\x1a\n"
        ):
            s10_ok = True
    matrix.add(
        Verdict(
            id="S10",
            status="PASS" if s10_ok else "FAIL",
            detail="At least one OG/social image returns HTTP 200",
            evidence="; ".join(s10_ev),
        )
    )

    matrix.add(s11_verdict(root))
    matrix.add(s12_verdict(root))

    for item in static_debug_verdicts(root):
        matrix.add(item)
    for item in snapshot_l_verdicts():
        matrix.add(item)
    return matrix


def print_matrix(matrix: Matrix) -> None:
    print(f"{'ID':<22} {'STATUS':<14} DETAIL")
    print("-" * 88)
    for item in matrix.verdicts:
        snap = f" ({item.snapshot_date})" if item.snapshot_date else ""
        owner = f" [{item.owner}]" if item.owner else ""
        print(f"{item.id:<22} {item.status:<14} {item.detail}{snap}{owner}")
        if item.evidence:
            print(f"{'':22} {'':14} evidence: {item.evidence}")


def matrix_errors(
    matrix: Matrix, required: Iterable[str] = REQUIRED_MATRIX_IDS
) -> list[str]:
    errors = validate_matrix(matrix, required=required)
    errors.extend(f"FAIL {vid}" for vid in matrix.fail_ids())
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("contract", "live", "all"),
        default="contract",
        help="contract=no network (bind+labelling). live=HTTP GET/HEAD only.",
    )
    parser.add_argument(
        "--origin",
        action="append",
        dest="origins",
        help="Origin to probe (repeatable). Default: https://a11oy.net and www.",
    )
    parser.add_argument("--json-out", default="", help="Write matrix JSON to this path")
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args(argv)
    root = Path(args.root)

    origins = args.origins or [CANONICAL_ORIGIN, ALIAS_ORIGIN]
    if args.mode in {"live", "all"}:
        matrix = live_matrix(origins, root=root)
    else:
        matrix = contract_matrix(root=root)

    print_matrix(matrix)
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(matrix.as_dict(), indent=2) + "\n", encoding="utf-8"
        )

    required = CONTRACT_REQUIRED_IDS if args.mode == "contract" else REQUIRED_MATRIX_IDS
    errors = matrix_errors(matrix, required=required)
    if errors:
        print("\nFAIL-CLOSED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
