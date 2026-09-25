#!/usr/bin/env python3
"""SZL Estate Frontier Upgrade — Codex payload v1.1.0

Extends attachments/szl_estate_frontier.py v1.0.0.
Does not invent a fifth estate OS.

HOLD is on:
  - no git add / commit / push / tag from this script itself
  - no Hugging Face upload
  - --create-docs-pr refused
  - never auto-license
  - proven_trust hardcoded False
  - Λ uniqueness remains OPEN_CONJECTURE

Run:
  python3 tools/estate_codex_payload.py --out ./szl-estate-audit
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import sys
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

VERSION = "1.1.0"
PARENT_AUDITOR = "szl_estate_frontier.py@1.0.0"
GH_API = "https://api.github.com"
HF_API = "https://huggingface.co/api"
DEFAULT_GH_ORG = "szl-holdings"
DEFAULT_HF_ORG = "SZLHOLDINGS"
DEFAULT_OUT = Path("szl-estate-audit")
HOLD = True
PROVEN_TRUST = False
LAMBDA_UNIQUENESS = "OPEN_CONJECTURE"

DATED_PROFILE = {"captured": "2026-09-10", "spaces": 21, "models": 46, "datasets": 35, "evidence_class": "REPORTED"}
SESSION_SNAPSHOT = {
    "captured": "2026-09-20T14:35:00Z",
    "evidence_class": "MEASURED",
    "github": {"public_org_page": 117, "auth_search": 124, "archived_false_search": 96,
               "private_observed": ["szl-safe-stack"],
               "private_reported": ["pitch-collateral", "szl-estate-os", "szl-org-health"]},
    "huggingface": {"spaces": 21, "models": 47, "datasets": 35, "collections_html": 21},
}
PUBLIC_SEVEN = ["a11oy", "killinchu", "david-leads", "anatomy", "immune", "szl-real-estate", "szl-atelier"]
FOLD_SPACES = ["SZLHOLDINGS/yarqa"]
JOBLIB_QUARANTINE = {"SZLHOLDINGS/szl-blocked", "SZLHOLDINGS/szl-provctl", "SZLHOLDINGS/szl-formulas", "SZLHOLDINGS/szl-ouroboros", "SZLHOLDINGS/szl-nemo"}
YUYAY_AXES = ("moralGrounding", "measurabilityHonesty", "empiricalGrounding", "logicalConsistency", "sourceTransparency", "reproducibility", "licenseHygiene", "scopeDiscipline", "claimCalibration", "evalAwareness", "deceptionKeywords", "conflictingDirectives", "reversalDirective")
YUYAY_FLOORS = (0.95, 0.95) + (0.90,) * 11
CTO_EIGHT = [
    "Human-resolve ambiguous licenses; never auto-apply a license.",
    "Make the machine-readable authority manifest canonical in .github.",
    "Pin every external GitHub Action to a verified full commit SHA.",
    "Reconcile public profile counts with the live measured inventory.",
    "Bind every retained HF asset to a GitHub source commit and explicit disposition.",
    "Repair non-running Spaces before calling them operational.",
    "Publish one reproducible Lambda-vs-arithmetic benchmark using the canonical Yuyay axes.",
    "Run Lean from the existing lutar-lean source; do not generate placeholder theorems.",
]
C1_C6 = [
    {"id": "C1", "asset": "SZLHOLDINGS/szl-receiptagent-qwen35-0.8b-v3", "action": "Quarantine ReceiptAgent v3 as proposal-only."},
    {"id": "C2", "asset": "SZLHOLDINGS/SZL-Khipu-1.5B-abstain", "action": "Repair or relabel abstain card."},
    {"id": "C3", "asset": "szl-lambda-gate + szl-governed-norm", "action": "Fix kernel CI."},
    {"id": "C4", "asset": "joblib family", "action": "Remove unsafe joblib serialization."},
    {"id": "C5", "asset": "chaski / chaski-5050 / A11OY-MINI", "action": "Quarantine research-only."},
    {"id": "C6", "asset": "szl-blocked + szl-provctl", "action": "Unblock admission and provenance path."},
]

@dataclass
class Finding:
    severity: str
    system: str
    asset: str
    code: str
    message: str
    remediation: str
    evidence: dict[str, Any] = field(default_factory=dict)

class HoldError(RuntimeError):
    pass

def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()

def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")

def digest(obj: Any) -> str:
    return hashlib.sha256(canonical(obj)).hexdigest()

def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")

def request_json(url: str, token: str | None = None) -> Any:
    headers = {"Accept": "application/json", "User-Agent": f"szl-estate-frontier-upgrade/{VERSION}"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode("utf-8"))

def hf_license(asset: dict[str, Any]) -> str:
    for tag in asset.get("tags") or []:
        if isinstance(tag, str) and tag.startswith("license:"):
            return tag.split(":", 1)[1]
    card = asset.get("cardData") or {}
    return str(card.get("license") or "NOASSERTION")

def weighted_geometric(values: list[float], weights: list[float]) -> float:
    if (not values or len(values) != len(weights) or any(not math.isfinite(x) or x <= 0 for x in values)
            or any(w < 0 for w in weights) or not math.isclose(sum(weights), 1.0, abs_tol=1e-9)):
        return 0.0
    return math.exp(sum(w * math.log(x) for x, w in zip(values, weights)))

def weighted_arithmetic(values: list[float], weights: list[float]) -> float:
    if not values or len(values) != len(weights):
        return 0.0
    return sum(x * w for x, w in zip(values, weights))

def governance_comparison(threshold: float = 0.7) -> list[dict[str, Any]]:
    n = len(YUYAY_AXES)
    w = [1 / n] * n
    cases = {
        "all_high": [0.95] * n,
        "one_critical_low": [0.95] * (n - 1) + [0.30],
        "one_zero": [0.95] * (n - 1) + [0.0],
        "uniform_threshold": [threshold] * n,
        "polarized": [0.99] * 4 + [0.10] * (n - 4),
    }
    out = []
    for name, xs in cases.items():
        g = weighted_geometric(xs, w)
        a = weighted_arithmetic(xs, w)
        out.append({"scenario": name, "geometric": round(g, 8), "arithmetic": round(a, 8),
                    "threshold": threshold, "geometric_allows": g >= threshold,
                    "arithmetic_allows": a >= threshold,
                    "divergent": (g >= threshold) != (a >= threshold)})
    return out

def refuse_publish(flag: str) -> None:
    raise HoldError(f"{flag} refused while HOLD is on. Local drafts only.")

def hash_receipts(out: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    parent = "0" * 64
    for p in sorted(x for x in out.rglob("*") if x.is_file() and x.name != "receipts.jsonl"):
        payload = {"path": str(p.relative_to(out)).replace("\\", "/"),
                   "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                   "size": p.stat().st_size, "parent": parent,
                   "state": "UNSIGNED_HONEST", "generated_at": now()}
        payload["receipt_digest"] = digest(payload)
        parent = payload["receipt_digest"]
        rows.append(payload)
    with (out / "receipts.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, separators=(",", ":")) + "\n")
    return rows

def main() -> int:
    ap = argparse.ArgumentParser(description="SZL estate upgrade auditor. HOLD-locked.")
    ap.add_argument("--github-org", default=DEFAULT_GH_ORG)
    ap.add_argument("--hf-org", default=DEFAULT_HF_ORG)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--create-docs-pr", action="store_true")
    ap.add_argument("--publish-hf", action="store_true")
    args = ap.parse_args()
    if HOLD and args.create_docs_pr:
        refuse_publish("--create-docs-pr")
    if HOLD and args.publish_hf:
        refuse_publish("--publish-hf")
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    findings: list[Finding] = []
    print("[1/4] Yuyay invariant", file=sys.stderr)
    comp = governance_comparison()
    one = next(r for r in comp if r["scenario"] == "one_zero")
    if one["geometric"] != 0.0 or one["geometric_allows"] or not one["arithmetic_allows"]:
        findings.append(Finding("CRITICAL", "yuyay", "one_zero", "GEOMETRIC_COLLAPSE_BROKEN",
                                f"Got {one}", "Restore conjunctive geometric product."))
    print("[2/4] Live inventories unless --offline", file=sys.stderr)
    hf = {"models": [], "datasets": [], "spaces": []}
    gh: list[dict[str, Any]] = []
    if not args.offline:
        try:
            for kind in ("models", "datasets", "spaces"):
                url = f"{HF_API}/{kind}?author={urllib.parse.quote(args.hf_org)}&limit=200&full=true"
                data = request_json(url)
                hf[kind] = data if isinstance(data, list) else []
        except Exception as e:
            findings.append(Finding("UNKNOWN", "huggingface", "list", "HF_LIST_FAILED", str(e), "Re-run when Hub reachable."))
        try:
            page = 1
            while True:
                batch = request_json(f"{GH_API}/orgs/{args.github_org}/repos?type=all&sort=full_name&per_page=100&page={page}")
                if not isinstance(batch, list) or not batch:
                    break
                for r in batch:
                    lic = (r.get("license") or {}).get("spdx_id") or "NOASSERTION"
                    gh.append({"name": r.get("name"), "private": bool(r.get("private")),
                               "archived": bool(r.get("archived")), "license": lic})
                if len(batch) < 100:
                    break
                page += 1
        except Exception as e:
            findings.append(Finding("UNKNOWN", "github", args.github_org, "GH_LIST_FAILED", str(e), "Re-run with token."))
    measured = {k: len(hf[k]) or SESSION_SNAPSHOT["huggingface"][k] for k in ("spaces", "models", "datasets")}
    declared = {k: DATED_PROFILE[k] for k in ("spaces", "models", "datasets")}
    if measured != declared:
        findings.append(Finding("MEDIUM", "github", ".github/profile", "PUBLIC_INVENTORY_DRIFT",
                                f"Dated {declared} vs measured {measured}.",
                                "Keep 2026-09-10 historical; add a new dated observation."))
    print("[3/4] Write drafts", file=sys.stderr)
    summary = {"generated_at": now(), "version": VERSION, "hold": HOLD, "proven_trust": PROVEN_TRUST,
               "lambda_uniqueness": LAMBDA_UNIQUENESS, "github_visible": len(gh),
               "huggingface": {k: len(v) for k, v in hf.items()}, "measured": measured,
               "declared": declared, "file_tree_walk": "NOT_COMPLETE", "winner": None}
    write_json(out / "summary.json", summary)
    write_json(out / "governance-comparison.json", comp)
    write_json(out / "findings.json", [asdict(f) for f in findings])
    write_json(out / "c1-c6.json", C1_C6)
    write_json(out / "cto-eight.json", CTO_EIGHT)
    (out / "HOLD.txt").write_text("HOLD\nno Hub upload\nno auto-license\nproven_trust=false\n", encoding="utf-8")
    print("[4/4] Hash-chain receipts", file=sys.stderr)
    receipts = hash_receipts(out)
    print(json.dumps({"ok": True, "version": VERSION, "out": str(out), "hold": HOLD,
                      "summary": summary, "receipt_count": len(receipts),
                      "claims": {"lambda_uniqueness": LAMBDA_UNIQUENESS, "proven_trust": PROVEN_TRUST, "winner": None}}, indent=2))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except HoldError as e:
        print(json.dumps({"ok": False, "hold": True, "error": str(e)}), file=sys.stderr)
        raise SystemExit(2)
