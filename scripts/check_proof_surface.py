#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Dependency-free contract guard for the a11oy.net proof registry."""

from __future__ import annotations

import json
import re
import struct
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
NOJEKYLL = ROOT / ".nojekyll"
ROBOTS = ROOT / "robots.txt"
SITEMAP = ROOT / "sitemap.xml"
MANIFEST = ROOT / "site.webmanifest"
SECURITY = ROOT / ".well-known" / "security.txt"
SOCIAL_PREVIEW = ROOT / "assets" / "a11oy-net-social.png"
EXPECTED_PROOFS = {
    "runtime-truth",
    "receipt-verifier",
    "assurance",
    "benchmarks",
    "source",
    "estate",
}


def relative_luminance(hex_color: str) -> float:
    channels = [
        int(hex_color[index : index + 2], 16) / 255
        for index in (1, 3, 5)
    ]
    linear = [
        value / 12.92
        if value <= 0.04045
        else ((value + 0.055) / 1.055) ** 2.4
        for value in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(first: str, second: str) -> float:
    high, low = sorted(
        (relative_luminance(first), relative_luminance(second)),
        reverse=True,
    )
    return (high + 0.05) / (low + 0.05)


class Surface(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.anchors: list[dict[str, str | None]] = []
        self.buttons: list[dict[str, str | None]] = []
        self.ids: set[str] = set()
        self.links: list[dict[str, str | None]] = []
        self.metas: list[dict[str, str | None]] = []
        self.scripts: list[dict[str, str | None]] = []

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
        elif tag == "meta":
            self.metas.append(item)
        elif tag == "script":
            self.scripts.append(item)


def check() -> None:
    assert NOJEKYLL.is_file(), (
        ".nojekyll is required to publish .well-known/security.txt on GitHub Pages"
    )
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
    assert {"rel": "manifest", "href": "site.webmanifest"} in surface.links

    def meta_value(kind: str, name: str) -> str | None:
        return next(
            (
                str(meta.get("content"))
                for meta in surface.metas
                if meta.get(kind) == name and meta.get("content")
            ),
            None,
        )

    assert meta_value("property", "og:url") == "https://a11oy.net/"
    assert meta_value("property", "og:image") == (
        "https://a11oy.net/assets/a11oy-net-social.png"
    )
    assert meta_value("name", "twitter:card") == "summary_large_image"
    assert meta_value("name", "twitter:image") == (
        "https://a11oy.net/assets/a11oy-net-social.png"
    )
    assert SOCIAL_PREVIEW.is_file() and SOCIAL_PREVIEW.stat().st_size > 10_000
    preview_bytes = SOCIAL_PREVIEW.read_bytes()
    assert preview_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    preview_width, preview_height = struct.unpack(">II", preview_bytes[16:24])
    assert preview_width >= 1200 and preview_height >= 630
    assert 1.85 <= preview_width / preview_height <= 1.95

    structured_blocks = re.findall(
        r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
        source,
        re.DOTALL,
    )
    assert len(structured_blocks) == 1, "one canonical JSON-LD graph is required"
    structured = json.loads(structured_blocks[0])
    assert structured["@type"] == "WebSite"
    assert structured["url"] == "https://a11oy.net/"
    assert structured["publisher"]["url"] == "https://github.com/szl-holdings"

    robots = ROBOTS.read_text(encoding="utf-8")
    assert "Sitemap: https://a11oy.net/sitemap.xml" in robots
    sitemap = ET.parse(SITEMAP)
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    assert [
        element.text for element in sitemap.findall(".//sm:loc", namespace)
    ] == ["https://a11oy.net/"]
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["start_url"] == "/"
    assert manifest["theme_color"] == "#080c14"
    security = SECURITY.read_text(encoding="utf-8")
    assert "Canonical: https://a11oy.net/.well-known/security.txt" in security
    assert "https://a11oy.com" not in source + robots + security

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
    assert "RUNTIME CHECK BELOW" not in source
    assert source.count('<span class="stack-truth">REPORTED</span>') == 6
    assert (
        "REPORTED identifies listing metadata only; runtime state, capability, "
        "and availability are not checked in this section." in source
    ), "curated Hub cards need bounded non-runtime evidence labels"
    assert 'data-probe="https://a-11-oy.com/verify"' in source
    assert 'data-probe="https://a-11-oy.com/api/a11oy/v1/honest"' in source
    colors = dict(re.findall(r"--([a-z-]+):(#[0-9a-fA-F]{6})", source))
    for background in ("void", "deep", "surface"):
        assert contrast_ratio(colors["ghost"], colors[background]) >= 4.5
    assert source.count('class="st" aria-live="polite"') == 5
    assert 'aria-busy="true"' in source
    assert 'id="atlasObservedAt" role="status"' in source
    assert 'grid.setAttribute("aria-busy","false")' in source
    assert 'new Date().toISOString()' in source
    assert 'fetchJson("https://huggingface.co/api/spaces/"' in source
    assert "var controller=new AbortController()" in source
    assert "if(returned===0)" in source
    assert '["atlasTotal","atlasModels","atlasDatasets","atlasCollections","atlasBuckets"]' in source
    assert "Inventory unavailable; this is not an observed-empty result." in source
    assert 'aria-label="A11oy public evidence dossier"' in source
    assert "Browser registry reads require JavaScript." in source
    assert 'event.key==="Escape"' in source
    assert any(
        script.get("src") == "scripts/atlas_policy.js"
        for script in surface.scripts
    ), "the runtime atlas must load its shared admission policy"
    assert "atlasPolicy.select(spec.type,normalizeItems(payload,spec))" in source, (
        "fetched resources must be filtered before generated-card ingestion"
    )
    assert "atlasPolicy.classify(spec.type,id,item.title)" in source, (
        "runtime-generated cards must carry the admission policy's evidence label"
    )
    assert (
        '{type:"SPACE",url:"https://huggingface.co/api/spaces' not in source
    ), "interactive Space listings must not be fetched for the generated atlas"
    assert "data-filter=\"SPACE\"" not in source
    assert 'id="atlasSpaces"' not in source
    assert (
        "REPORTED means point-in-time public Hub listing metadata only" in source
    ), "artifact cards need an honest, bounded evidence label"
    assert "Executable Spaces and Killinchu-named resources are outside" in source, (
        "the generated atlas boundary must be visible to visitors"
    )


if __name__ == "__main__":
    check()
    print("OK: a11oy.net proof-registry contract is intact.")
