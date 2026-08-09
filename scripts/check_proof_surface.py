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
MANIFEST_ALIAS = ROOT / "manifest.webmanifest"
HEADERS = ROOT / "_headers"
SECURITY = ROOT / ".well-known" / "security.txt"
SOCIAL_PREVIEW = ROOT / "assets" / "a11oy-net-social.png"
LINK_WORKFLOW = ROOT / ".github" / "workflows" / "link-check.yml"
PROBE_POLICY = ROOT / "scripts" / "probe_policy.js"
PROBE_POLICY_CHECK = ROOT / "scripts" / "check_probe_policy.mjs"
READYZ = ROOT / "readyz"
BUILD_INFO = ROOT / "api" / "build-info"
DILIGENCE = ROOT / "diligence" / "index.html"
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
        self.elements: list[tuple[str, dict[str, str | None]]] = []
        self.ids: set[str] = set()
        self.links: list[dict[str, str | None]] = []
        self.mains: list[dict[str, str | None]] = []
        self.metas: list[dict[str, str | None]] = []
        self.scripts: list[dict[str, str | None]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        item = dict(attrs)
        self.elements.append((tag, item))
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
        elif tag == "main":
            self.mains.append(item)
        elif tag == "script":
            self.scripts.append(item)


def check() -> None:
    assert NOJEKYLL.is_file(), (
        ".nojekyll is required to publish .well-known/security.txt on GitHub Pages"
    )
    workflow = LINK_WORKFLOW.read_text(encoding="utf-8")
    assert re.search(r"^    name: Link & Asset Check$", workflow, re.MULTILINE)
    assert re.search(
        r"^    name: pages build and deployment$", workflow, re.MULTILINE
    )
    assert '.well-known/security.txt' in workflow
    assert 'root.rglob("*.html")' in workflow
    assert "python3 scripts/check_diligence_surface.py" in workflow
    assert "node scripts/check_probe_policy.mjs" in workflow
    for protected_artifact in (
        "404.html",
        "assets/a11oy-mark.svg",
        "assets/diligence.css",
        "diligence/index.html",
        "evidence.json",
        "llms.txt",
        "scripts/check_probe_policy.mjs",
        "scripts/probe_policy.js",
    ):
        assert protected_artifact in workflow
    assert PROBE_POLICY.is_file() and PROBE_POLICY_CHECK.is_file(), (
        "shared fail-closed browser observation policy and regression check are required"
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
                if str(meta.get(kind) or "").lower() == name.lower()
                and meta.get("content")
            ),
            None,
        )

    assert meta_value("name", "referrer") == "no-referrer"
    meta_csp = meta_value("http-equiv", "Content-Security-Policy")
    assert meta_csp is not None, "the root document needs a fallback meta CSP"

    def csp_directives(value: str) -> dict[str, set[str]]:
        parsed: dict[str, set[str]] = {}
        for raw_part in value.split(";"):
            part = raw_part.strip().split()
            if not part:
                continue
            directive = part[0].lower()
            assert directive not in parsed, f"duplicate CSP directive: {directive}"
            parsed[directive] = set(part[1:])
        return parsed

    meta_csp_directives = csp_directives(meta_csp)
    for directive, token in (
        ("default-src", "'self'"),
        ("object-src", "'none'"),
        ("base-uri", "'self'"),
        ("form-action", "'none'"),
    ):
        assert token in meta_csp_directives.get(directive, set()), (
            f"meta CSP must retain {directive} {token}"
        )
    assert "frame-ancestors" not in meta_csp_directives, (
        "frame-ancestors is header-only and must not be claimed by meta CSP"
    )
    assert "upgrade-insecure-requests" in meta_csp_directives
    header_csp_match = re.search(
        r"^\s*Content-Security-Policy:\s*(.+)$",
        HEADERS.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    assert header_csp_match, "the versioned response-header CSP must exist"
    fallback_contract = csp_directives(header_csp_match.group(1))
    fallback_contract.pop("frame-ancestors", None)
    assert meta_csp_directives == fallback_contract, (
        "meta CSP must match the response-header contract except frame-ancestors"
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
    ] == ["https://a11oy.net/", "https://a11oy.net/diligence/"]
    manifest_bytes = MANIFEST.read_bytes()
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    assert manifest["start_url"] == "/"
    assert manifest["theme_color"] == "#080c14"
    assert MANIFEST_ALIAS.read_bytes() == manifest_bytes, (
        "manifest.webmanifest must be byte-identical to site.webmanifest"
    )
    assert DILIGENCE.is_file(), "the public diligence route must exist"
    assert any(
        anchor.get("href") == "/diligence/" for anchor in surface.anchors
    ), "the root proof registry must expose the diligence route"
    readyz_index = READYZ / "index.html" if READYZ.is_dir() else READYZ
    assert readyz_index.is_file(), "front-door readiness route must exist"
    build_info_index = BUILD_INFO / "index.html" if BUILD_INFO.is_dir() else BUILD_INFO
    assert build_info_index.is_file(), "front-door build-info route must exist"
    readyz_html = readyz_index.read_text(encoding="utf-8")
    build_info_html = build_info_index.read_text(encoding="utf-8")
    assert (
        "a-11-oy.com" in readyz_html.lower()
    ), "readiness route must link to the runtime source explicitly"
    assert (
        "static build info surface" in build_info_html.lower()
    ), "build-info route must stay scoped to evidence surface"
    security = SECURITY.read_text(encoding="utf-8")
    assert "Canonical: https://a11oy.net/.well-known/security.txt" in security
    assert "https://a11oy.com" not in source + robots + security

    assert len(surface.mains) == 1, "the root document needs one main landmark"
    main = surface.mains[0]
    assert main.get("id") == "main-content"
    assert main.get("tabindex") == "-1", "the skip target must be focusable"
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
    assert 'menuToggle.textContent=open ? "Close" : "Explore"' in source
    assert (
        'open ? "Close evidence navigation" : "Explore evidence navigation"'
        in source
    )
    assert ".menu-toggle{display:none!important}" in source
    assert ".nav-links{display:flex!important;position:static!important" in source
    assert (
        "JavaScript is disabled. Product links remain available" in source
    ), "no-script mode must retain navigation and disclose unavailable reads"

    assert 'class="live-list" role="list"' not in source
    assert 'el.setAttribute("role","listitem")' not in source
    assert "#atlasResultCount,#atlasState{display:none}" in source

    live_regions = [
        item
        for _, item in surface.elements
        if item.get("aria-live") is not None or item.get("role") == "status"
    ]
    assert len(live_regions) == 2, (
        "dynamic observations must use exactly two bounded live regions"
    )
    live_regions_by_id = {item.get("id"): item for item in live_regions}
    assert set(live_regions_by_id) == {"liveSummary", "atlasResultCount"}
    for region_id in ("liveSummary", "atlasResultCount"):
        region = live_regions_by_id[region_id]
        assert region.get("role") == "status"
        assert region.get("aria-live") == "polite"
        assert region.get("aria-atomic") == "true"
    assert re.search(r"setTimeout\(updateLiveSummary,\s*\d+\)", source)
    assert re.search(r"setTimeout\(render,\s*\d+\)", source), (
        "registry filter announcements must be debounced"
    )
    for _, item in surface.elements:
        classes = set((item.get("class") or "").split())
        if "st" in classes or item.get("id") in {
            "atlasResources",
            "atlasState",
            "atlasObservedAt",
        }:
            assert item.get("aria-live") is None
            assert item.get("role") != "status"

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
    assert "independent verification entry point" not in source.lower()
    assert "public verification entry point" in source.lower()
    assert source.count('data-static="product-route"') == 3
    assert source.count("NOT PROBED · UNKNOWN") == 4, (
        "three product rows and the explanatory boundary must remain explicit"
    )
    assert source.count('data-space="SZLHOLDINGS/') == 2
    expected_space_bindings = {
        "SZLHOLDINGS/szl-estate-live": (
            "https://huggingface.co/api/spaces/SZLHOLDINGS/szl-estate-live",
            "https://szlholdings-szl-estate-live.static.hf.space",
        ),
        "SZLHOLDINGS/receipt-chain-live": (
            "https://huggingface.co/api/spaces/SZLHOLDINGS/receipt-chain-live",
            "https://szlholdings-receipt-chain-live.static.hf.space",
        ),
    }
    observed_space_bindings = [
        (
            str(anchor.get("data-space")),
            str(anchor.get("data-api")),
            str(anchor.get("href")),
        )
        for anchor in surface.anchors
        if anchor.get("data-space")
    ]
    assert len(observed_space_bindings) == len(expected_space_bindings)
    assert {
        space: (api, href) for space, api, href in observed_space_bindings
    } == expected_space_bindings, (
        "each browser-read Space must retain its exact repository/API/link binding"
    )
    assert source.count("NOT OBSERVED · UNAVAILABLE") == 3, (
        "two HF fallbacks and the no-script explanation must fail closed"
    )
    assert "data-probe=" not in source, (
        "product routes are public links only and must not be browser-probed"
    )
    colors = dict(re.findall(r"--([a-z-]+):(#[0-9a-fA-F]{6})", source))
    for background in ("void", "deep", "surface"):
        assert contrast_ratio(colors["ghost"], colors[background]) >= 4.5
    assert 'aria-busy="true"' in source
    assert 'grid.setAttribute("aria-busy","false")' in source
    assert 'new Date().toISOString()' in source
    assert 'fetchJson(binding.api)' in source
    assert 'redirect:"error"' in source
    assert "probePolicy.isExactResponseFor(r,url)" in source
    assert any(
        script.get("src") == "scripts/probe_policy.js"
        for script in surface.scripts
    ), "HF runtime reads must load the shared fail-closed observation policy"
    assert "probePolicy.classifySpaceMetadata(data)" in source
    assert 'probePolicy.classifyFailure("METADATA_REQUEST_FAILED")' in source
    assert 'document.querySelectorAll(".live[data-space]")' in source
    assert 'document.querySelectorAll(".live[data-static]")' not in source
    assert (
        'var rows=Array.from(document.querySelectorAll(".live[data-space]"));'
        in source
    ), "product links must be excluded from runtime-metadata completion counts"
    assert "Public Hub runtime-metadata reads complete" in source
    assert "var controller=new AbortController()" in source
    assert "if(returned===0)" in source
    assert '["atlasTotal","atlasModels","atlasDatasets","atlasCollections","atlasBuckets"]' in source
    assert "Inventory unavailable; this is not an observed-empty result." in source
    assert 'aria-label="A11oy public evidence dossier"' in source
    assert "Browser registry reads require JavaScript." in source
    assert 'event.key==="Escape"' in source
    live_start = source.find('document.querySelectorAll(".live[data-space]")')
    live_end = source.find("var resources=", live_start)
    assert live_start >= 0 and live_end > live_start
    live_source = source[live_start:live_end]
    assert "data-probe" not in live_source
    assert "fetch(el.dataset" not in live_source, (
        "product links must remain static and unprobed"
    )
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
    atlas_search = re.search(r"\.atlas-search\{([^}]*)\}", source)
    assert atlas_search is not None
    search_font = re.search(r"\bfont:\s*(\d+(?:\.\d+)?)px\b", atlas_search.group(1))
    assert search_font is not None and float(search_font.group(1)) >= 16, (
        "the mobile search control must stay at least 16px to avoid focus zoom"
    )


if __name__ == "__main__":
    check()
    print("OK: a11oy.net proof-registry contract is intact.")
