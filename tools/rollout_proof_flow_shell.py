#!/usr/bin/env python3
"""Bind the local monochrome Flow Shell to every published proof document."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STYLE = '<link rel="stylesheet" href="/assets/szl-flow-proof.css" data-szl-proof-flow-asset="style" />'
SCRIPT = '<script src="/scripts/szl-flow-proof.js" defer data-szl-proof-flow-asset="script"></script>'
STATE = ROOT / "frontend-flow-shell-state.json"
EXCLUDE_PARTS = {"node_modules", "vendor", ".git", "fixtures", "archive", "archives"}


def candidates() -> list[Path]:
    paths: set[Path] = set()
    for rel in ("index.html", "404.html"):
        path = ROOT / rel
        if path.is_file():
            paths.add(path)
    for path in ROOT.rglob("index.html"):
        if path.is_file() and not (set(path.relative_to(ROOT).parts) & EXCLUDE_PARTS):
            paths.add(path)
    return sorted(paths)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def inject(path: Path) -> str:
    text = read(path)
    if "data-szl-proof-flow-opt-out" in text:
        return "opt-out"
    if "</head>" not in text.lower() or "</body>" not in text.lower():
        return "not-document"
    if text.count('data-szl-proof-flow-asset="style"') > 1 or text.count('data-szl-proof-flow-asset="script"') > 1:
        raise RuntimeError(f"duplicate proof-flow marker in {path.relative_to(ROOT)}")
    changed = False
    if STYLE not in text:
        index = text.lower().rfind("</head>")
        text = text[:index] + "  " + STYLE + "\n" + text[index:]
        changed = True
    if SCRIPT not in text:
        index = text.lower().rfind("</body>")
        text = text[:index] + "  " + SCRIPT + "\n" + text[index:]
        changed = True
    if changed:
        path.write_text(text, encoding="utf-8", newline="\n")
        return "injected"
    return "present"


def update_state(changed: list[str], examined: int) -> None:
    payload = json.loads(STATE.read_text(encoding="utf-8"))
    payload["state"] = "ROLLED_OUT"
    payload["examined_documents"] = examined
    payload["injected_documents"] = changed
    STATE.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    rows = []
    changed: list[str] = []
    for path in candidates():
        rel = path.relative_to(ROOT).as_posix()
        text = read(path)
        result = (
            "present" if STYLE in text and SCRIPT in text else "missing"
        ) if args.check else inject(path)
        rows.append({"path": rel, "result": result})
        if result == "injected":
            changed.append(rel)
    if not rows:
        raise SystemExit("no proof HTML candidates were found")
    root = next((row for row in rows if row["path"] == "index.html"), None)
    if not root or root["result"] in {"missing", "not-document", "opt-out"}:
        raise SystemExit("the proof front door is not flow-shell bound")
    if args.check and any(row["result"] == "missing" for row in rows):
        raise SystemExit("missing proof flow shell: " + ", ".join(row["path"] for row in rows if row["result"] == "missing"))
    if not args.check:
        update_state(changed, len(rows))
    report = {
        "schema": "szl.proof-flow-shell-rollout/v1",
        "mode": "CHECK" if args.check else "APPLY",
        "examined": len(rows),
        "changed": len(changed),
        "rows": rows,
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
