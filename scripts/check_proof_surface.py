#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Dependency-free contract guard for the a11oy.net proof registry."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
EXPECTED_PROOFS = {
    "runtime-truth",
    "receipt-verifier",
    "assurance",
    "benchmarks",
    "source",
    "estate",
}


class Surface(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.anchors: list[dict[str, str | None]] = []
        self.buttons: list[dict[str, str | None]] = []
        self.ids: set[str] = set()
        self.links: list[dict[str, str | None]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        item = dict(attrs)
        if item.get("id"):
            self.ids.add(str(item["id"]))
        if tag == "a":
            self.anchors.append(item)
        elif tag == "button":
            self.buttons.append(item)
        elif tag == "link":
            self.links.append(item)


def check() -> None:
    source = INDEX.read_text(encoding="utf-8")
    surface = Surface()
    surface.feed(source)

    canonical = [
        link
        for link in surface.links
        if link.get("rel") == "canonical"
    ]
    assert canonical == [
        {"rel": "canonical", "href": "https://a11oy.net/"}
    ], "a11oy.net must remain its own canonical proof domain"

    assert "main-content" in surface.ids
    assert any(
        anchor.get("class") == "skip-link"
        and anchor.get("href") == "#main-content"
        for anchor in surface.anchors
    ), "keyboard users need a working skip link"

    menu = next(
        (button for button in surface.buttons if button.get("id") == "menuToggle"),
        None,
    )
    assert menu is not None
    assert menu.get("type") == "button"
    assert menu.get("aria-controls") == "primaryLinks"
    assert menu.get("aria-expanded") == "false"
    assert "primaryLinks" in surface.ids

    proof_ids = {
        str(anchor["data-proof"])
        for anchor in surface.anchors
        if anchor.get("data-proof")
    }
    assert proof_ids == EXPECTED_PROOFS

    for anchor in surface.anchors:
        href = anchor.get("href") or ""
        assert "killinchu" not in href.lower(), (
            "the proof front door must not promote the access-gated Killinchu surface"
        )
        if anchor.get("target") == "_blank":
            assert "noopener" in (anchor.get("rel") or "").split()
        parsed = urlparse(href)
        if parsed.scheme:
            assert parsed.scheme == "https", f"external evidence link is not HTTPS: {href}"

    assert "MEASURED NOW" not in source
    assert 'data-probe="https://a-11-oy.com/verify"' in source
    assert 'data-probe="https://a-11-oy.com/api/a11oy/v1/honest"' in source
    assert 'event.key==="Escape"' in source


if __name__ == "__main__":
    check()
    print("OK: a11oy.net proof-registry contract is intact.")
