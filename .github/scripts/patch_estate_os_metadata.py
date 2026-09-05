#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind omitted metadata and compact repeated catalog prose."""
from __future__ import annotations

from pathlib import Path


def replace_once(text: str, old: str, new: str, *, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one replacement target, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    path = Path(".github/scripts/materialize_estate_os_231.py")
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '''    branch_manifest = json.loads(Path("estate/os/data.json").read_text(encoding="utf-8"))
    old = old_assets()
''',
        '''    branch_manifest = json.loads(Path("estate/os/data.json").read_text(encoding="utf-8"))
    prior_manifest = json.loads(
        subprocess.check_output(
            ["git", "show", "origin/main:estate/os/data.json"],
            text=True,
            encoding="utf-8",
        )
    )
    surface = dict(branch_manifest.get("surface") or prior_manifest["surface"])
    surface.update(
        {
            "url": "https://a11oy.net/estate/os/",
            "product": "https://a-11-oy.com",
            "proof": "https://a11oy.net",
            "never": "a11oy.com — foreign storefront",
        }
    )
    later_recapture = branch_manifest.get("laterRecapture") or prior_manifest["laterRecapture"]
    prior_bake = branch_manifest.get("priorBake") or {
        "capturedAt": prior_manifest.get("capturedAt"),
        "scope": prior_manifest.get("scope"),
        "honesty": prior_manifest.get("honesty"),
        "counts": prior_manifest.get("counts"),
        "note": "Preserved metadata for the preceding committed public-partial bake.",
    }
    old = old_assets()
''',
        label="materializer metadata prelude",
    )
    for old, new, label in (
        (
            '"surface": branch_manifest["surface"],',
            '"surface": surface,',
            "surface binding",
        ),
        (
            '"laterRecapture": branch_manifest["laterRecapture"],',
            '"laterRecapture": later_recapture,',
            "later recapture binding",
        ),
        (
            '"priorBake": branch_manifest["priorBake"],',
            '"priorBake": prior_bake,',
            "prior bake binding",
        ),
        (
            'return text[:280]',
            'return text[:220]',
            "description source budget",
        ),
        (
            '"runtimeNote": "Repository inventory only. Runtime was not probed by this static bake.",',
            '"runtimeNote": "Catalog only; runtime unprobed.",',
            "GitHub runtime note compaction",
        ),
        (
            '"runtimeNote": "Public Hub repository observed. Runtime and artifact quality were not inferred.",',
            '"runtimeNote": "Catalog only; runtime unprobed.",',
            "Hub runtime note compaction",
        ),
    ):
        text = replace_once(text, old, new, label=label)
    path.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
