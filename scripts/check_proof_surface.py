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
CNAME = ROOT / "CNAME"
SECURITY = ROOT / ".well-known" / "security.txt"
SOCIAL_PREVIEW = ROOT / "assets" / "a11oy-net-social.png"
LINK_WORKFLOW = ROOT / ".github" / "workflows" / "link-check.yml"
PROBE_POLICY = ROOT / "scripts" / "probe_policy.js"
PROBE_POLICY_CHECK = ROOT / "scripts" / "check_probe_policy.mjs"
HONEST_KERNEL_BIND = ROOT / "scripts" / "honest_kernel_bind.js"
HONEST_KERNEL_BIND_CHECK = ROOT / "scripts" / "check_honest_kernel_bind.mjs"
READYZ = ROOT / "readyz"
BUILD_INFO = ROOT / "api" / "build-info"
DILIGENCE = ROOT / "diligence" / "index.html"
STAMP_HEALTH_SHA = ROOT / "scripts" / "stamp_health_sha.py"
LAST_PUBLISHED_MAIN_SHA = "82ad0481753ddd0043e3b55352704e187be14a08"
ALLOWED_HEALTH_SIGNERS = ("DSSE-LIVE", "UNSIGNED-LOCAL", "unavailable")
EXPECTED_PROOFS = {
    "runtime-truth",
    "receipt-verifier",
    "record",
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
    assert CNAME.read_text(encoding="utf-8").strip() == "a11oy.net", (
        "CNAME must remain a11oy.net; this origin is not a product host"
    )
    assert not (ROOT / "api" / "lake").exists(), (
        "this origin must not host /api/lake; live receipts stay on the product Space"
    )
    assert not (ROOT / "receipts").exists()
    assert not (ROOT / "record" / "receipts").exists()
    assert not list(ROOT.glob("*.dsse.json"))
    workflow = LINK_WORKFLOW.read_text(encoding="utf-8")
    assert re.search(r"^    name: Link & Asset Check$", workflow, re.MULTILINE)
    assert re.search(
        r"^    name: pages build and deployment$", workflow, re.MULTILINE
    )
    assert '.well-known/security.txt' in workflow
    assert 'root.rglob("*.html")' in workflow
    assert "python3 scripts/check_diligence_surface.py" in workflow
    assert "node scripts/check_probe_policy.mjs" in workflow
    assert "python3 scripts/stamp_health_sha.py --sha \"${GITHUB_SHA}\"" in workflow
    assert STAMP_HEALTH_SHA.is_file(), "Pages artifact stamp for health.json sha must exist"
    assert "python3 scripts/check_honest_kernel_bind.py" in workflow
    assert "node scripts/check_honest_kernel_bind.mjs" in workflow
    for protected_artifact in (
        "404.html",
        "assets/a11oy-mark.svg",
        "assets/diligence.css",
        "assets/kanchay.css",
        "chat/index.html",
        "code/index.html",
        "diligence/index.html",
        "evidence.json",
        "health.json",
        "llms.txt",
        "notes/index.html",
        "record.json",
        "record/index.html",
        "atlas.json",
        "scripts/check_probe_policy.mjs",
        "scripts/honest_kernel_bind.js",
        "scripts/probe_policy.js",
    ):
        assert protected_artifact in workflow
    assert PROBE_POLICY.is_file() and PROBE_POLICY_CHECK.is_file(), (
        "shared fail-closed browser observation policy and regression check are required"
    )
    assert HONEST_KERNEL_BIND.is_file() and HONEST_KERNEL_BIND_CHECK.is_file(), (
        "shared fail-closed /honest kernel-chip bind and regression check are required"
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
    assert structured["name"] == "a11oy Proof Registry"
    assert structured["alternateName"] == "Alloy by SZL Holdings"
    assert structured["sameAs"] == [
        "https://a11oy.net/diligence/",
        "https://a11oy.net/record/",
        "https://a11oy.net/notes/",
    ]
    assert all(str(url).startswith("https://a11oy.net/") for url in structured["sameAs"])
    assert "huggingface.co/spaces" not in json.dumps(structured)
    assert "a11oy.com" not in json.dumps(structured)
    assert structured["publisher"]["url"] == "https://github.com/szl-holdings"
    assert structured["isRelatedTo"]["name"] == "a11oy"
    assert structured["isRelatedTo"]["url"] == "https://a-11-oy.com/"

    robots = ROBOTS.read_text(encoding="utf-8")
    assert "Sitemap: https://a11oy.net/sitemap.xml" in robots
    sitemap = ET.parse(SITEMAP)
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    assert [
        element.text for element in sitemap.findall(".//sm:loc", namespace)
    ] == [
        "https://a11oy.net/",
        "https://a11oy.net/diligence/",
        "https://a11oy.net/record/",
        "https://a11oy.net/notes/",
        "https://a11oy.net/chat/",
        "https://a11oy.net/code/",
    ]
    assert "healthz" not in SITEMAP.read_text(encoding="utf-8")
    assert "readyz" not in SITEMAP.read_text(encoding="utf-8")
    manifest_bytes = MANIFEST.read_bytes()
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    assert manifest["start_url"] == "/"
    assert manifest["theme_color"] == "#080c14"
    assert MANIFEST_ALIAS.read_bytes() == manifest_bytes, (
        "manifest.webmanifest must be byte-identical to site.webmanifest"
    )
    assert DILIGENCE.is_file(), "the public diligence route must exist"
    assert (ROOT / "record" / "index.html").is_file(), "canonical RECORD must exist"
    assert (ROOT / "record.json").is_file(), "RECORD machine contract must exist"
    assert (ROOT / "atlas.json").is_file(), "atlas machine contract must exist"
    assert (ROOT / "notes" / "index.html").is_file(), "dated notes must exist"
    assert (ROOT / "health.json").is_file(), "static JSON probe document must exist"
    health = json.loads((ROOT / "health.json").read_text(encoding="utf-8"))
    assert health["path"] == "/health.json"
    assert health["probe_contract"] == "STATIC_DOCUMENT"
    assert health["dsse_live"] == "NOT_CLAIMED"
    assert health["signer"] == "unavailable"
    assert health["signer"] in ALLOWED_HEALTH_SIGNERS
    assert health["signer"] != "DSSE-LIVE"
    assert health["signer"] != "UNSIGNED-LOCAL"
    assert health["sha"] == LAST_PUBLISHED_MAIN_SHA
    assert re.fullmatch(r"[0-9a-f]{40}", health["sha"])
    assert health["uptime"] == "NOT_MEASURED"
    health_blob = json.dumps(health)
    assert "exactly 8" not in health_blob
    assert "exactly eight" not in health_blob.lower()
    assert "locked-proven" not in health_blob.lower()
    assert "hardcoded-8" not in health_blob
    assert health["readyz"] == "NOT_A_HEALTH_URL"
    assert health["healthz"] == "NOT_PUBLISHED"
    assert health["json_probe_document"] == "https://a11oy.net/health.json"
    import importlib.util
    import shutil
    import tempfile

    spec = importlib.util.spec_from_file_location("stamp_health_sha", STAMP_HEALTH_SHA)
    assert spec is not None and spec.loader is not None
    stamp_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stamp_mod)
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "health.json"
        shutil.copyfile(ROOT / "health.json", copy)
        stamped = stamp_mod.stamp(copy, "a" * 40)
        assert stamped["sha"] == "a" * 40
        assert stamped["signer"] == "unavailable"
        assert stamped["uptime"] == "NOT_MEASURED"
        assert stamped["dsse_live"] == "NOT_CLAIMED"
        for forbidden_signer in ("DSSE-LIVE", "UNSIGNED-LOCAL"):
            tampered = json.loads(copy.read_text(encoding="utf-8"))
            tampered["signer"] = forbidden_signer
            copy.write_text(json.dumps(tampered), encoding="utf-8")
            try:
                stamp_mod.stamp(copy, "b" * 40)
            except ValueError:
                pass
            else:
                raise AssertionError(
                    f"stamp_health_sha must refuse signer={forbidden_signer}"
                )
    assert not (ROOT / "healthz").exists(), "/healthz must not be published as a competing route"
    assert not (ROOT / "healthz.html").exists(), "/healthz must not be published as a competing file"
    assert any(
        anchor.get("href") == "/diligence/" for anchor in surface.anchors
    ), "the root proof registry must expose the diligence route"
    assert any(
        anchor.get("href") == "/record/" for anchor in surface.anchors
    ), "the root proof registry must expose RECORD"
    assert "Alloy by SZL Holdings" in source
    assert "id=\"summary\"" in source
    assert "id=\"record\"" in source
    assert "id=\"github-atlas\"" in source
    assert "Ninety seconds" in source
    assert "Origin health document" in source
    assert "healthz is not published" in source.lower()
    assert "https://a11oy.net/record/" in source
    assert "The signed RECORD index lives at" in source
    assert "https://a-11-oy.com/verify" in source
    assert "Receipt store on this origin" in source
    assert "api/lake" not in source, (
        "root first paint must not fetch or register the product lake API"
    )
    assert "fetch(\"https://a-11-oy.com" not in source
    assert "huggingface.co/spaces" not in meta_value("property", "og:url")
    assert meta_value("property", "og:url") == "https://a11oy.net/"
    landmark_markup = {
        "navigation": re.findall(
            r"<nav\b.*?</nav>", source, re.DOTALL | re.IGNORECASE
        ),
        "footer": re.findall(
            r"<footer\b.*?</footer>", source, re.DOTALL | re.IGNORECASE
        ),
    }
    for landmark, blocks in landmark_markup.items():
        assert len(blocks) == 1, (
            f"the root proof registry must have exactly one {landmark}"
        )
    nav_block, footer_block = (
        landmark_markup["navigation"][0],
        landmark_markup["footer"][0],
    )
    assert "Chat gateway" not in nav_block, (
        "Chat gateway must not remain a top-level nav peer"
    )
    assert "Code gateway" not in nav_block, (
        "Code gateway must not remain a top-level nav peer"
    )
    assert "Product ↗" in nav_block, "Product ↗ must remain the outbound origin"
    assert nav_block.count("origin-switch") == 1, (
        "root must keep a single Product | Proof header"
    )
    assert 'aria-current="true"' in nav_block and ">Proof</a>" in nav_block, (
        "Proof must remain the current origin on a11oy.net"
    )
    assert "RECORD" in nav_block
    assert "Hub atlas and ROADMAP live here" in source, (
        "Hub atlas + ROADMAP must be locked to a11oy.net, not the product domain"
    )
    assert "without leaving the flagship" not in source
    assert not (ROOT / "investor").exists(), "do not invent /investor"
    assert not (ROOT / "verify").exists(), "do not clone /verify onto .net"
    assert 'href="/investor"' not in source
    assert 'href="/verify"' not in source and 'href="/verify/"' not in source
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Hub atlas and ROADMAP live here" in readme
    assert "There is no `/investor` route" in readme or "no `/investor` route" in readme
    for gateway in ("chat", "code"):
        assert (ROOT / gateway / "index.html").is_file()
        assert f'href="/{gateway}/"' in footer_block, (
            f"the root footer must keep the {gateway} diligence handoff discoverable"
        )
        assert f'href="/{gateway}/"' not in nav_block
    readyz_index = READYZ / "index.html" if READYZ.is_dir() else READYZ
    assert readyz_index.is_file(), "front-door readiness route must exist"
    build_info_index = BUILD_INFO / "index.html" if BUILD_INFO.is_dir() else BUILD_INFO
    assert build_info_index.is_file(), "front-door build-info route must exist"
    readyz_html = readyz_index.read_text(encoding="utf-8")
    build_info_html = build_info_index.read_text(encoding="utf-8")
    assert (
        "not a json health" in readyz_html.lower()
        or "not json health" in readyz_html.lower()
    ), "readyz must not be registered as a health URL"
    assert "not a health url" in readyz_html.lower() or "not a health probe" in readyz_html.lower()
    assert "/health.json" in readyz_html
    assert "healthz" in readyz_html.lower()
    assert "not published" in readyz_html.lower()
    assert (
        "a-11-oy.com" in readyz_html.lower()
    ), "readiness route must link to the runtime source explicitly"
    assert (
        "static build info surface" in build_info_html.lower()
    ), "build-info route must stay scoped to evidence surface"
    security = SECURITY.read_text(encoding="utf-8")
    assert "Canonical: https://a11oy.net/.well-known/security.txt" in security
    assert "https://a11oy.com" not in source + robots + security
    forbidden = "https://a11oy.com"
    for path in ROOT.rglob("*"):
        if ".git" in path.parts or "scripts" in path.parts or not path.is_file():
            continue
        if path.suffix.lower() not in {
            ".html",
            ".json",
            ".md",
            ".txt",
            ".py",
            ".js",
            ".mjs",
            ".yml",
            ".css",
            ".xml",
        }:
            continue
        text = path.read_text(encoding="utf-8")
        assert forbidden not in text, (
            f"{path.relative_to(ROOT)} must not stamp the furniture-shop domain {forbidden}"
        )
    record_source = (ROOT / "record" / "index.html").read_text(encoding="utf-8")
    assert "https://a11oy.net/record/" in record_source
    assert "https://a-11-oy.com/verify" in record_source
    assert "id=\"permalinks\"" in record_source
    assert "id=\"receipt-ids\"" in record_source
    assert "id=\"live-store\"" in record_source
    assert "no receipt store" in record_source.lower() or "not a receipt database" in record_source.lower()
    assert "SZLHOLDINGS/szl-evidence" in record_source
    assert "/api/lake/v1/receipts" in record_source
    assert "not a product host" in record_source.lower()
    assert "empty is UNAVAILABLE" in record_source.lower() or "empty, labelled unavailable" in record_source.lower()
    assert "Two hosts. Two jobs." in record_source

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
    assert "main{position:relative;z-index:1}" in source
    assert "nav{position:sticky;top:0;z-index:10;" in source
    short_screen_nav = """@media(max-height:500px) and (max-width:900px){
  html{scroll-padding-top:0}
  nav{position:relative}
  [id]{scroll-margin-top:12px}
}"""
    assert source.count(short_screen_nav) == 1, (
        "short-screen navigation must remain positioned so its z-index stays "
        "above the positioned main content"
    )
    assert ".menu-toggle{display:none!important}" in source
    assert ".nav-links{display:flex!important;position:static!important" in source
    noscript_styles = re.findall(
        r"<noscript>\s*<style>(.*?)</style>\s*</noscript>",
        source,
        re.DOTALL | re.IGNORECASE,
    )
    assert len(noscript_styles) == 1, (
        "the no-script navigation contract must have one scoped style block"
    )
    no_script_style = noscript_styles[0]
    assert "html{scroll-padding-top:0!important}" in no_script_style
    assert "nav{position:static!important}" in no_script_style
    assert "[id]{scroll-margin-top:0!important}" in no_script_style
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
    assert colors["void"] == "#080c14"
    assert colors["proof"] == "#3af4c8"
    assert colors["lattice"] == "#5b8dee"
    assert colors["gold"] == "#d7b96b"
    for background in ("void", "deep", "surface"):
        assert contrast_ratio(colors["ghost"], colors[background]) >= 4.5
    assert "#c9b787" not in source.lower()
    assert "#5fb3a3" not in source.lower()
    assert "#0a0a0a" not in source.lower()
    kanchay = (ROOT / "assets" / "kanchay.css").read_text(encoding="utf-8")
    assert "--void:#080c14" in kanchay
    assert "--proof:#3af4c8" in kanchay
    assert "--lattice:#5b8dee" in kanchay
    assert "--gold:#d7b96b" in kanchay
    assert "Space Grotesk" in kanchay and "JetBrains Mono" in kanchay
    assert ".empty-panel" in kanchay
    assert "kanchay-lattice-drift" in kanchay
    assert "prefers-reduced-motion:reduce" in kanchay
    assert "class=\"empty-panel\"" in source or "empty-panel" in source
    assert "PROOF REGISTRY" in source
    assert colors["gray"] == "#7d8aa0"
    assert ".wordmark .glyph{width:26px;height:26px;border-radius:7px;background:var(--surface);border:1px solid var(--border);display:grid;place-items:center;color:var(--gray);" in source
    assert 'id="atlasResources" aria-busy="false"' in source
    assert 'grid.setAttribute("aria-busy","true")' in source
    assert 'grid.setAttribute("aria-busy","false")' in source
    assert 'new Date().toISOString()' in source
    assert 'fetchJson(binding.api)' in source
    assert 'redirect:"error"' in source
    assert "probePolicy.isExactResponseFor(r,url)" in source
    assert any(
        script.get("src") == "scripts/probe_policy.js"
        for script in surface.scripts
    ), "HF runtime reads must load the shared fail-closed observation policy"
    assert any(
        script.get("src") == "scripts/honest_kernel_bind.js"
        for script in surface.scripts
    ), "kernel chips must load the shared fail-closed /honest bind"
    assert "exactly 8" not in source
    assert "exactly eight" not in source.lower()
    assert 'data-kernel-chip="locked-proven"' in source
    assert 'data-honest-url="https://a-11-oy.com/api/a11oy/v1/honest"' in source
    assert 'data-honest-field="locked_formula_count"' in source
    assert 'id="cnt-locked"' in source
    assert "catalog LOCKED-PROVEN" in source
    assert "Lean-8 ≠ genome-144" in source
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
    assert "The dated static registry snapshot remains visible" in source
    assert 'data-static-snapshot="2026-08-28"' in source
    assert '<b id="atlasTotal">57</b>' in source
    assert '<b id="atlasModels">17</b>' in source
    assert '<b id="atlasDatasets">27</b>' in source
    assert '<b id="atlasCollections">12</b>' in source
    assert '<b id="atlasBuckets">1</b>' in source
    assert "2026-08-11" not in source, (
        "the noscript/fallback snapshot must not retain the prior 2026-08-11 counts"
    )
    assert source.count('<span class="stack-truth roadmap">ROADMAP</span>') == 12, (
        "Fall 2026 cuts and KERNEL originals must remain ROADMAP, never OPERATIONAL"
    )
    assert not re.search(r'class="stack-truth[^"]*"[^>]*>OPERATIONAL', source), (
        "no stack listing may carry an OPERATIONAL label"
    )
    assert "tok/s" not in source.lower()
    assert "KHIPU-R2" in source
    assert "WILLAY" in source
    assert "YARQA-ATTN" in source
    assert "A11OY-MINI" in source
    assert 'href="https://huggingface.co/SZLHOLDINGS/chaski"' in source
    assert 'href="https://huggingface.co/SZLHOLDINGS/qantu"' in source
    assert 'href="https://huggingface.co/SZLHOLDINGS/waman"' in source
    assert 'href="https://huggingface.co/SZLHOLDINGS/chakana"' in source
    assert 'href="https://huggingface.co/SZLHOLDINGS/tinku"' in source
    assert source.count('href="https://huggingface.co/SZLHOLDINGS/YARQA-ATTN"') == 1, (
        "YARQA-ATTN stays one KERNEL-owned cutting card, not a fourth Triton stack"
    )
    assert "alias for szl-receipt-attn" not in source
    assert "ATELIER · YARQA" not in source
    yarqa_start = source.find("<h3>YARQA-ATTN</h3>")
    assert yarqa_start >= 0
    yarqa = source[yarqa_start : source.find("</a>", yarqa_start)]
    assert "KERNEL-owned" in yarqa
    assert "alias" not in yarqa
    assert "ATELIER model" in yarqa and "not an ATELIER model" in yarqa
    kernels_start = source.find('<section id="kernels"')
    kernels_end = source.find("<section", kernels_start + 1)
    assert kernels_start >= 0 and kernels_end > kernels_start, (
        "KERNEL originals must be a first-class section, not Hub-card-only stubs"
    )
    kernels = source[kernels_start:kernels_end]
    assert kernels.count('<span class="stack-truth roadmap">ROADMAP</span>') == 3
    assert "OPERATIONAL" not in kernels.replace("not OPERATIONAL", "")
    assert "<h3>YARQA-ATTN</h3>" not in kernels
    assert "<h3>Sage" not in kernels
    assert "not listed as shipped" in kernels
    assert "Only szl-receipt-attn has Triton bytes on main" in kernels
    assert "CPU Khipu lab pin" in kernels
    assert "Conjecture 1" in kernels
    assert "theorem" not in kernels.lower()
    assert 'href="https://github.com/szl-holdings/szl-receipt-attn"' in kernels
    assert 'href="https://github.com/szl-holdings/szl-maskmod"' in kernels
    assert 'href="https://github.com/szl-holdings/szl-block-kv"' in kernels
    assert 'href="https://huggingface.co/SZLHOLDINGS/szl-receipt-attn"' in kernels
    assert 'href="https://huggingface.co/SZLHOLDINGS/szl-maskmod"' in kernels
    assert 'href="https://huggingface.co/SZLHOLDINGS/szl-block-kv"' in kernels

    def kernel_card(name: str) -> str:
        start = kernels.find(f"<h3>{name}</h3>")
        assert start >= 0, f"missing KERNEL card {name}"
        end = kernels.find("<h3>", start + 1)
        if end < 0:
            end = len(kernels)
        return kernels[start:end]

    receipt = kernel_card("szl-receipt-attn")
    maskmod = kernel_card("szl-maskmod")
    block_kv = kernel_card("szl-block-kv")
    assert "Triton bytes are in-tree" in receipt
    assert "not Triton-in-tree" in maskmod
    assert "Triton bytes" not in maskmod
    assert "torch paged KV gather" in block_kv
    assert "the gather is not a Triton kernel" in block_kv
    assert "Triton page kernel remains ROADMAP" in block_kv
    assert "szl-serve stays a CPU Khipu lab pin" in kernels
    assert "KILLINCHU-EYE" not in source
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
