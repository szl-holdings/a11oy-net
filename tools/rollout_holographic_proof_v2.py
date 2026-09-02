#!/usr/bin/env python3
"""Bind Holographic Evidence Vault v2 to a11oy.net proof documents.

Documents with a zero-JavaScript contract receive a CSS-only journey rail.
Other documents receive the interactive first-party controller. The operation
is deterministic, idempotent, and preserves evidence content and claims.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STYLE = '<link rel="stylesheet" href="/assets/szl-holo-proof-v2.css" data-szl-proof-holo-asset="style-v2" />'
SCRIPT = '<script src="/scripts/szl-holo-proof-v2.js" defer data-szl-proof-holo-asset="script-v2"></script>'
STATE = ROOT / "holographic-experience-v2" / "rollout-state.json"
STATIC_MARKER = 'data-szl-proof-holo-static="v2"'
ADOPTED_MARKER = 'data-szl-proof-holo-adopted="true"'
EXCLUDED_PARTS = {".git", "node_modules", "vendor", "fixtures", "archive", "archives", "coverage", "dist"}
ZERO_JAVASCRIPT = {
    "404.html",
    "chat/index.html",
    "code/index.html",
    "diligence/index.html",
    "notes/index.html",
    "record/index.html",
}
JOURNEYS = (
    ("Start", "https://a11oy.net/"),
    ("Products", "https://a-11-oy.com/"),
    ("Models", "https://a11oy.net/estate/"),
    ("Kernels", "https://a11oy.net/khipu/"),
    ("Proof", "https://a11oy.net/record/"),
)
CURRENT = {
    "404.html": "Start",
    "chat/index.html": "Products",
    "code/index.html": "Products",
    "diligence/index.html": "Proof",
    "notes/index.html": "Proof",
    "record/index.html": "Proof",
}


def documents() -> list[Path]:
    found: set[Path] = set()
    not_found = ROOT / "404.html"
    if not_found.is_file():
        found.add(not_found)
    for path in ROOT.rglob("index.html"):
        if not path.is_file():
            continue
        if not set(path.relative_to(ROOT).parts).intersection(EXCLUDED_PARTS):
            found.add(path)
    return sorted(found)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def add_html_attribute(text: str) -> tuple[str, bool]:
    match = re.search(r"<html(?P<attrs>[^>]*)>", text, flags=re.IGNORECASE)
    if match is None:
        raise RuntimeError("document has no html element")
    attrs = match.group("attrs")
    if 'data-szl-proof-holo="v2"' in attrs:
        return text, False
    replacement = f'<html{attrs} data-szl-proof-holo="v2">'
    return text[: match.start()] + replacement + text[match.end() :], True


def add_before(text: str, closing_tag: str, payload: str) -> str:
    offset = text.lower().rfind(closing_tag.lower())
    if offset < 0:
        raise RuntimeError(f"missing closing tag {closing_tag}")
    return text[:offset] + payload + text[offset:]


def remove_own_script(text: str) -> tuple[str, bool]:
    original = text
    pattern = re.compile(
        r"\s*<script\s+src=[\"']/scripts/szl-holo-proof-v2\.js[\"'][^>]*></script>\s*",
        flags=re.IGNORECASE,
    )
    text = pattern.sub("\n", text)
    return text, text != original


def adopt_existing_rail(text: str) -> tuple[str, bool]:
    pattern = re.compile(
        r"<(nav|header)(?P<attrs>[^>]*class=[\"'][^\"']*(?:szl-proof-static-rail|szl-proof-rail)[^\"']*[\"'][^>]*)>",
        flags=re.IGNORECASE,
    )
    match = pattern.search(text)
    if match is None:
        return text, False
    if ADOPTED_MARKER in match.group(0):
        return text, False
    replacement = f'<{match.group(1)}{match.group("attrs")} {ADOPTED_MARKER}>'
    return text[: match.start()] + replacement + text[match.end() :], True


def static_rail(relative: str) -> str:
    current = CURRENT[relative]
    links: list[str] = []
    for label, href in JOURNEYS:
        active = ' aria-current="page"' if label == current else ""
        links.append(
            f'      <a class="szl-proof-link" href="{html.escape(href, quote=True)}"{active}>{html.escape(label)}</a>'
        )
    return "\n".join(
        (
            f'  <nav class="szl-proof-static-rail" aria-label="A11oy proof journeys" {ADOPTED_MARKER} {STATIC_MARKER}>',
            '    <div class="szl-proof-origin"><span>Evidence Vault</span></div>',
            '    <div class="szl-proof-links">',
            *links,
            "    </div>",
            '    <div class="szl-proof-actions">',
            '      <a class="szl-proof-switch" href="https://a-11-oy.com/"><span>Open</span><strong>Product</strong></a>',
            "    </div>",
            "  </nav>",
        )
    )


def is_bound(relative: str, text: str) -> bool:
    if STYLE not in text or 'data-szl-proof-holo="v2"' not in text:
        return False
    if relative in ZERO_JAVASCRIPT:
        return SCRIPT not in text and (ADOPTED_MARKER in text or STATIC_MARKER in text)
    return SCRIPT in text


def bind(path: Path) -> str:
    relative = path.relative_to(ROOT).as_posix()
    text = read(path)
    if "data-szl-proof-holo-disabled" in text:
        return "opt-out"
    if "</head>" not in text.lower() or "</body>" not in text.lower():
        return "not-document"
    for marker in ('data-szl-proof-holo-asset="style-v2"', 'data-szl-proof-holo-asset="script-v2"', STATIC_MARKER):
        if text.count(marker) > 1:
            raise RuntimeError(f"duplicate marker {marker!r} in {relative}")

    changed = False
    text, html_changed = add_html_attribute(text)
    changed = changed or html_changed
    if STYLE not in text:
        text = add_before(text, "</head>", "  " + STYLE + "\n")
        changed = True

    if relative in ZERO_JAVASCRIPT:
        text, removed = remove_own_script(text)
        changed = changed or removed
        text, adopted = adopt_existing_rail(text)
        changed = changed or adopted
        if ADOPTED_MARKER not in text and STATIC_MARKER not in text:
            text = add_before(text, "</body>", static_rail(relative) + "\n")
            changed = True
    elif SCRIPT not in text:
        text = add_before(text, "</body>", "  " + SCRIPT + "\n")
        changed = True

    if changed:
        path.write_text(text, encoding="utf-8", newline="\n")
        return "bound"
    return "present"


def update_state(rows: list[dict[str, str]]) -> None:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    bindings = [row["path"] for row in rows if row["result"] in {"bound", "present"}]
    state["state"] = "ROLLED_OUT"
    state["bindings"] = bindings
    state["examined_documents"] = len(rows)
    state["bound_documents"] = len(bindings)
    state["zero_javascript_documents"] = sorted(ZERO_JAVASCRIPT)
    state["interactive_documents"] = sorted(set(bindings) - ZERO_JAVASCRIPT)
    state["opt_out_documents"] = [row["path"] for row in rows if row["result"] == "opt-out"]
    STATE.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(*, check: bool) -> dict[str, object]:
    rows: list[dict[str, str]] = []
    for path in documents():
        relative = path.relative_to(ROOT).as_posix()
        result = ("present" if is_bound(relative, read(path)) else "missing") if check else bind(path)
        rows.append({"path": relative, "result": result, "mode": "STATIC" if relative in ZERO_JAVASCRIPT else "INTERACTIVE"})
    if not rows:
        raise RuntimeError("no a11oy.net HTML documents were discovered")
    root = next((row for row in rows if row["path"] == "index.html"), None)
    if root is None or root["result"] in {"missing", "not-document", "opt-out"}:
        raise RuntimeError("the a11oy.net front door is not Holographic Evidence Vault v2 bound")
    missing = [row["path"] for row in rows if row["result"] == "missing"]
    if check and missing:
        raise RuntimeError("missing proof holographic binding: " + ", ".join(missing))
    if not check:
        update_state(rows)
    return {
        "schema": "szl.proof-holographic-experience-rollout/v2",
        "mode": "CHECK" if check else "APPLY",
        "examined": len(rows),
        "changed": sum(row["result"] == "bound" for row in rows),
        "static": sum(row["mode"] == "STATIC" for row in rows),
        "interactive": sum(row["mode"] == "INTERACTIVE" for row in rows),
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = run(check=args.check)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
