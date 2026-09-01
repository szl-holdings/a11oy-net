#!/usr/bin/env python3
"""Bind the local monochrome Flow Shell to every published proof document.

Interactive records receive the local JavaScript controller. Evidence documents
whose contracts require zero JavaScript receive an equivalent static HTML/CSS
journey rail. Both paths are idempotent and share the same five journeys.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STYLE = '<link rel="stylesheet" href="/assets/szl-flow-proof.css" data-szl-proof-flow-asset="style" />'
STATIC_STYLE = '<link rel="stylesheet" href="/assets/szl-flow-proof-static.css" data-szl-proof-flow-asset="static-style" />'
SCRIPT = '<script src="/scripts/szl-flow-proof.js" defer data-szl-proof-flow-asset="script"></script>'
STATIC_MARKER = 'data-szl-proof-flow-asset="static"'
STATE = ROOT / "frontend-flow-shell-state.json"
EXCLUDE_PARTS = {"node_modules", "vendor", ".git", "fixtures", "archive", "archives"}
NO_SCRIPT_DOCUMENTS = {
    "404.html",
    "chat/index.html",
    "code/index.html",
    "diligence/index.html",
    "notes/index.html",
    "record/index.html",
}
STATIC_THEMES = {
    "404.html": "ledger",
    "chat/index.html": "decision-mono",
    "code/index.html": "weave-mono",
    "diligence/index.html": "dossier",
    "notes/index.html": "notebook",
    "record/index.html": "forensic",
}
STATIC_CURRENT = {
    "404.html": "start",
    "chat/index.html": "products",
    "code/index.html": "products",
    "diligence/index.html": "proofs",
    "notes/index.html": "proofs",
    "record/index.html": "proofs",
}
JOURNEYS = (
    ("start", "Start Here", "https://a11oy.net/"),
    ("products", "Products & Demos", "https://a-11-oy.com/"),
    ("models", "Models & Data", "https://a11oy.net/estate/"),
    ("kernels", "Kernels & SDKs", "https://a11oy.net/khipu/"),
    ("proofs", "Proofs & Research", "https://a11oy.net/record/"),
)


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


def remove_fragment(text: str, fragment: str) -> tuple[str, bool]:
    original = text
    for candidate in (f"  {fragment}\n", f"    {fragment}\n", fragment + "\n", fragment):
        text = text.replace(candidate, "")
    return text, text != original


def bind_static_body(text: str, theme: str) -> tuple[str, bool]:
    pattern = re.compile(r"<body(?P<attrs>[^>]*)>", re.IGNORECASE)
    match = pattern.search(text)
    if match is None:
        raise RuntimeError("proof document has no body element")
    attrs = match.group("attrs")
    wanted = f'data-szl-proof-flow="record" data-szl-proof-theme="{theme}"'
    if 'data-szl-proof-flow="record"' in attrs and f'data-szl-proof-theme="{theme}"' in attrs:
        return text, False
    attrs = re.sub(r"\s+data-szl-proof-flow=([\"']).*?\1", "", attrs, flags=re.IGNORECASE)
    attrs = re.sub(r"\s+data-szl-proof-theme=([\"']).*?\1", "", attrs, flags=re.IGNORECASE)
    replacement = f"<body{attrs} {wanted}>"
    return text[: match.start()] + replacement + text[match.end() :], True


def static_rail(rel: str) -> str:
    current = STATIC_CURRENT[rel]
    links = []
    for journey_id, label, href in JOURNEYS:
        current_attr = ' aria-current="page"' if journey_id == current else ""
        links.append(
            f'      <a class="szl-proof-link" href="{html.escape(href, quote=True)}"'
            f' data-journey="{journey_id}"{current_attr}>{html.escape(label)}</a>'
        )
    return "\n".join(
        (
            f'  <nav class="szl-proof-rail szl-proof-static-rail" aria-label="SZL public-estate journeys" {STATIC_MARKER}>',
            '    <div class="szl-proof-origin" title="a11oy.net independent proof origin"><span>Record</span></div>',
            '    <div class="szl-proof-links">',
            *links,
            "    </div>",
            '    <div class="szl-proof-actions">',
            '      <a class="szl-proof-switch" href="https://a-11-oy.com/" title="Open the product command origin"><span>Open</span><strong>Product</strong></a>',
            "    </div>",
            "  </nav>",
        )
    )


def is_bound(rel: str, text: str) -> bool:
    if rel in NO_SCRIPT_DOCUMENTS:
        return (
            STYLE in text
            and STATIC_STYLE in text
            and STATIC_MARKER in text
            and SCRIPT not in text
            and 'data-szl-proof-flow="record"' in text
            and f'data-szl-proof-theme="{STATIC_THEMES[rel]}"' in text
        )
    return STYLE in text and SCRIPT in text and STATIC_MARKER not in text


def inject(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    text = read(path)
    if "data-szl-proof-flow-opt-out" in text:
        return "opt-out"
    if "</head>" not in text.lower() or "</body>" not in text.lower():
        return "not-document"
    for marker in (
        'data-szl-proof-flow-asset="style"',
        'data-szl-proof-flow-asset="static-style"',
        'data-szl-proof-flow-asset="script"',
        STATIC_MARKER,
    ):
        if text.count(marker) > 1:
            raise RuntimeError(f"duplicate proof-flow marker {marker!r} in {rel}")

    changed = False
    if STYLE not in text:
        index = text.lower().rfind("</head>")
        text = text[:index] + "  " + STYLE + "\n" + text[index:]
        changed = True

    if rel in NO_SCRIPT_DOCUMENTS:
        text, removed = remove_fragment(text, SCRIPT)
        changed = changed or removed
        if STATIC_STYLE not in text:
            index = text.lower().rfind("</head>")
            text = text[:index] + "  " + STATIC_STYLE + "\n" + text[index:]
            changed = True
        text, body_changed = bind_static_body(text, STATIC_THEMES[rel])
        changed = changed or body_changed
        if STATIC_MARKER not in text:
            index = text.lower().rfind("</body>")
            text = text[:index] + static_rail(rel) + "\n" + text[index:]
            changed = True
    else:
        if SCRIPT not in text:
            index = text.lower().rfind("</body>")
            text = text[:index] + "  " + SCRIPT + "\n" + text[index:]
            changed = True

    if changed:
        path.write_text(text, encoding="utf-8", newline="\n")
        return "injected"
    return "present"


def update_state(bound: list[str], examined: int) -> None:
    payload = json.loads(STATE.read_text(encoding="utf-8"))
    payload["state"] = "ROLLED_OUT"
    payload["examined_documents"] = examined
    payload["injected_documents"] = sorted(bound)
    payload["zero_javascript_documents"] = sorted(NO_SCRIPT_DOCUMENTS)
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
        result = ("present" if is_bound(rel, text) else "missing") if args.check else inject(path)
        rows.append({"path": rel, "result": result, "mode": "STATIC" if rel in NO_SCRIPT_DOCUMENTS else "INTERACTIVE"})
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
        bound = [row["path"] for row in rows if row["result"] in {"injected", "present"}]
        update_state(bound, len(rows))
    report = {
        "schema": "szl.proof-flow-shell-rollout/v1",
        "mode": "CHECK" if args.check else "APPLY",
        "examined": len(rows),
        "changed": len(changed),
        "static_documents": len(NO_SCRIPT_DOCUMENTS),
        "rows": rows,
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
