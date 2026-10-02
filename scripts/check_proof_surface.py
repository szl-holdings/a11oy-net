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
PAGES_ARTIFACT_BUILDER = ROOT / "scripts" / "build_pages_artifact.py"
GENERATOR = ROOT / "scripts" / "generate_hf_inventory.py"
HF_INVENTORY = ROOT / "public-inventory.json"
HF_CURRENT = ROOT / "estate" / "hf-current.json"
HF_LIVE_ALIGN = ROOT / "live-align" / "hf_live_inventory.json"
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



def _links_to_host(html: str, host: str) -> bool:
    """True when some absolute URL in ``html`` resolves to exactly ``host`` (hostname-exact, not substring)."""
    from urllib.parse import urlsplit
    for url in re.findall(r"https?://[^\s\"'<>]+", html):
        if (urlsplit(url).hostname or "").lower() == host:
            return True
    return False

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


def load_generator():
    import importlib.util

    spec = importlib.util.spec_from_file_location("generate_hf_inventory", GENERATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


HUB_LINK = re.compile(
    r"https://huggingface\.co/(?:(datasets|spaces|kernels)/)?(SZLHOLDINGS/[A-Za-z0-9._-]+)"
)
HUB_SPACE_API = re.compile(r"https://huggingface\.co/api/spaces/(SZLHOLDINGS/[A-Za-z0-9._-]+)")
SPACE_HOST = re.compile(r"https://([a-z0-9-]+\.(?:static\.)?hf\.space)\b")


def check_generated_hf_inventory() -> None:
    """Generated Hub inventory: schema, self-consistency, links, freshness.

    No count is typed here. Every count must equal the length of the id list
    it summarizes in the same generated document, every derived document must
    equal what the generator derives from public-inventory.json, and every
    page must be exactly what the generator renders from estate/hf-current.json.
    """
    from collections import Counter
    from datetime import datetime, timedelta, timezone

    gen = load_generator()
    inventory = json.loads(HF_INVENTORY.read_text(encoding="utf-8"))
    current = json.loads(HF_CURRENT.read_text(encoding="utf-8"))
    live_align = json.loads(HF_LIVE_ALIGN.read_text(encoding="utf-8"))
    models = json.loads((ROOT / "models.json").read_text(encoding="utf-8"))
    spaces = json.loads((ROOT / "spaces.json").read_text(encoding="utf-8"))

    # (a) schema and observation mode
    assert inventory["schema"] == gen.SCHEMA_INVENTORY
    assert current["schema"] == gen.SCHEMA_CURRENT
    assert live_align["schema"] == gen.SCHEMA_LIVE_ALIGN
    for document in (inventory, current, live_align):
        assert document["organization"] == "SZLHOLDINGS"
        assert document["observation_mode"] == "UNAUTHENTICATED_PUBLIC_API_SNAPSHOT"
        assert document["generated_by"] == "scripts/generate_hf_inventory.py"
    assert inventory["private_assets"] == current["private_assets"] == "NOT_OBSERVED"
    assert inventory["claim_boundaries"]["private_assets"] == "NOT_OBSERVED"
    assert inventory["content_sha256"] == gen.inventory_content_sha(inventory), (
        "public-inventory.json was edited by hand; rerun scripts/generate_hf_inventory.py"
    )
    assert current["source_content_sha256"] == inventory["content_sha256"]

    # (b) self-consistency: every count is the length of its own id list
    resources = inventory["resources"]
    counts = inventory["counts"]
    for kind in ("models", "datasets", "spaces", "kernels", "collections", "buckets"):
        ids = [row.get("id") or row.get("slug") for row in resources[kind]]
        assert counts[kind] == len(ids) == len(set(ids)), kind
        assert ids == sorted(ids), f"{kind} ids must be sorted"
    assert counts["spaces"] == counts["spaces_list_api_rows"] + counts["special_spaces_added"]
    assert counts["hub_artifacts_total"] == sum(
        counts[kind] for kind in ("models", "datasets", "spaces", "kernels", "collections")
    )
    assert counts["public_resources_total"] == counts["hub_artifacts_total"] + counts["buckets"]
    stages = Counter(row["runtime"]["stage"] or "NOT_REPORTED" for row in resources["spaces"])
    assert inventory["spaces_by_runtime_stage"] == dict(sorted(stages.items()))
    for row in resources["collections"]:
        assert row["item_count"] == len(row["items"]), row["slug"]
    for row in resources["buckets"]:
        assert isinstance(row["observed_object_count"], int), row["id"]
    assert current["counts"] == {
        "buckets": counts["buckets"],
        "collections": counts["collections"],
        "datasets_public": counts["datasets"],
        "kernels": counts["kernels"],
        "models": counts["models"],
        "public_resources_total": counts["public_resources_total"],
        "spaces_public": counts["spaces"],
    }
    assert current == gen.build_current(inventory, spaces, gen.historical_rows(ROOT)), (
        "estate/hf-current.json is not what the generator derives; rerun it"
    )
    assert live_align == gen.build_live_align(inventory, ROOT), (
        "live-align/hf_live_inventory.json is not what the generator derives; rerun it"
    )
    assert spaces["hub_presence"] == gen.build_spaces_contract(spaces, inventory)["hub_presence"]
    hub = models["hub"]
    assert (hub["models"], hub["datasets"], hub["spaces"], hub["kernels"]) == (
        counts["models"],
        counts["datasets"],
        counts["spaces"],
        counts["kernels"],
    )
    assert hub["private"] == "NOT_OBSERVED"
    assert models["captured_at"] == inventory["observed_at"]
    assert [row["id"] for row in models["models"]] == [row["id"] for row in resources["models"]]
    assert len(models["models"]) == hub["models"]
    class_counts = Counter(row["class"] for row in models["models"])
    assert models["counts"] == {name: class_counts.get(name, 0) for name in models["counts"]}
    assert set(models["counts"]) == set(models["classes"]) >= set(class_counts)
    assert sum(models["counts"].values()) == len(models["models"])
    for row in models["models"]:
        assert row["trained"] is (row["class"] in ("TRAINED_WEIGHTS", "NANO_SYNTHETIC")), row["id"]
    assert not re.search(r"\b\d+ (public )?(Hub )?(models|datasets|Spaces)\b", models["reader_guide"]), (
        "models.json prose must not type Hub counts"
    )

    # observed_at is a real UTC second, not in the future
    observed_at = inventory["observed_at"]
    assert gen.valid_timestamp(observed_at)
    assert current["observed_at"] == live_align["observed_at"] == observed_at
    assert current["observed_date"] == observed_at[:10]
    observed = datetime.strptime(observed_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    assert observed <= now + timedelta(minutes=5), "observed_at lies in the future"
    if now - observed > timedelta(days=8):
        # Not a failure: every page prints observed_at beside its counts and the
        # home badge turns STALE, so an old observation is labelled, not hidden.
        print(
            f"WARNING: generated Hub inventory observed {observed_at} is more than 8 days old; "
            "run .github/workflows/hf-inventory-refresh.yml"
        )

    # pages render exactly what the generator writes from estate/hf-current.json
    for page in gen.PAGES:
        text = (ROOT / page).read_text(encoding="utf-8")
        assert gen.render_page(text, current) == text, (
            f"{page}: generated regions are stale; run scripts/generate_hf_inventory.py"
        )
        keys = {key for key, _ in gen.page_fields(text)}
        assert keys, f"{page} must render its counts from estate/hf-current.json"
        if any(key.startswith("counts.") for key in keys):
            assert keys & {"observed_at", "observed_date"}, (
                f"{page} prints generated counts without their observation date"
            )

    # (c) every Hub asset or Space host these surfaces link is publicly listed
    pools = {
        "": {row["id"] for row in resources["models"]},
        "datasets": {row["id"] for row in resources["datasets"]},
        "spaces": {row["id"] for row in resources["spaces"]},
        "kernels": {row["id"] for row in resources["kernels"]},
    }
    hosts = {urlparse(row["canonical_live_url"]).netloc for row in resources["spaces"]}
    for relative in (*gen.PAGES, "estate/os/data.json", "estate/os/data.delta.json"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        for kind, ident in HUB_LINK.findall(text):
            assert ident in pools[kind], f"{relative} links absent Hub asset {kind or 'models'}/{ident}"
        for ident in HUB_SPACE_API.findall(text):
            assert ident in pools["spaces"], f"{relative} reads absent Space API {ident}"
        for host in SPACE_HOST.findall(text):
            assert host in hosts, f"{relative} links absent Space host {host}"

    # The dated hologram bake keeps its rows; a Hub link it no longer may print
    # is nulled and named in linkRetirements, never silently dropped.
    bake = json.loads((ROOT / "estate" / "os" / "data.json").read_text(encoding="utf-8"))
    retirements = bake.get("linkRetirements")
    if retirements is not None:
        assert gen.valid_timestamp(retirements["retiredAt"])
        assert retirements["source"] == "/estate/hf-current.json"
        rows = {row["id"]: row for row in bake["assets"]}
        for entry in retirements["retired"]:
            field = entry["field"]
            assert field.startswith("urls."), entry
            assert rows[entry["asset"]]["urls"][field.split(".", 1)[1]] is None, entry

    # live Space rows: spaces.json KEEP policy, publicly listed, front-door withheld excluded
    cards = current["live_space_cards"]
    assert [card["id"] for card in cards] == [
        f"SZLHOLDINGS/{item['id']}"
        for item in spaces["keep"]
        if f"SZLHOLDINGS/{item['id']}" in pools["spaces"] and "killinchu" not in item["id"].lower()
    ]
    for card in cards:
        assert card["api"] == f"https://huggingface.co/api/spaces/{card['id']}"
        assert card["href"] == f"https://huggingface.co/spaces/{card['id']}"


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
    assert "if: github.event_name == 'pull_request'" in workflow
    assert 'root.rglob("*.html")' in workflow
    assert "python3 scripts/check_diligence_surface.py" in workflow
    assert "node scripts/check_probe_policy.mjs" in workflow
    assert STAMP_HEALTH_SHA.is_file(), "Pages artifact stamp for health.json sha must exist"
    assert PAGES_ARTIFACT_BUILDER.is_file(), "isolated Pages artifact builder must exist"
    assert "python3 scripts/build_pages_artifact.py" in workflow
    assert "--source-revision \"${SOURCE_REVISION}\"" in workflow
    assert "actions/configure-pages@45bfe0192ca1faeb007ade9deae92b16b8254a0d" in workflow
    assert "actions/upload-pages-artifact@fc324d3547104276b827a68afc52ff2a11cc49c9" in workflow
    assert "actions/deploy-pages@368f82528645a54fb793d4d04e342629a3f51346" in workflow
    assert "include-hidden-files: true" in workflow
    assert "enablement: false" in workflow
    assert "github.ref == 'refs/heads/main'" in workflow
    assert "git ls-remote \"https://github.com/${GITHUB_REPOSITORY}.git\" refs/heads/main" in workflow
    assert "pages: write" in workflow and "id-token: write" in workflow
    assert "cancel-in-progress: false" in workflow
    assert "Unsupported Pages build_type" in workflow
    assert "gh api \"repos/${GITHUB_REPOSITORY}/pages\" --jq '.build_type'" in workflow
    assert "-X PUT" not in workflow and "-X POST" not in workflow
    assert "python3 scripts/check_honest_kernel_bind.py" in workflow
    assert "node scripts/check_honest_kernel_bind.mjs" in workflow
    builder = PAGES_ARTIFACT_BUILDER.read_text(encoding="utf-8")
    assert 'EXCLUDED_TOP_LEVEL = {".git", ".github"}' in builder
    assert '_git(root, "ls-tree", "-rz", "--full-tree", source_revision)' in builder
    assert '("git", "-C", str(root), "cat-file", "--batch")' in builder
    assert 'stamp(output / "health.json", source_revision)' in builder
    assert 'artifact output must be outside the source tree' in builder
    for protected_artifact in (
        ".well-known/security.txt",
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
        assert protected_artifact in builder
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
    assert structured["alternateName"] == "a11oy"  # lexicon locked 2026-08-30: the product is a11oy; "Alloy" subtitle retired (lexicon_gate)
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
        "https://a11oy.net/ayllu/",
        "https://a11oy.net/khipu/",
        "https://a11oy.net/experiments/",
        "https://a11oy.net/diligence/",
        "https://a11oy.net/record/",
        "https://a11oy.net/oac/",
        "https://a11oy.net/estate/",
        "https://a11oy.net/estate/os/",
        "https://a11oy.net/estate/plane/",
        "https://a11oy.net/estate/thread-ops/",
        "https://a11oy.net/command/",
        "https://a11oy.net/notes/",
        "https://a11oy.net/chat/",
        "https://a11oy.net/code/",
        "https://a11oy.net/atelier/",
        "https://a11oy.net/decision/",
        "https://a11oy.net/terra/",
        "https://a11oy.net/aegis/",
        "https://a11oy.net/puriq-markets/",
        "https://a11oy.net/counsel/",
        "https://a11oy.net/vessels/",
        "https://a11oy.net/ayllu/psyche/",
        "https://a11oy.net/five-space/",
        "https://a11oy.net/nexus/",
        "https://a11oy.net/factory/",
        "https://a11oy.net/origin/",
        "https://a11oy.net/frontiers/",
        "https://a11oy.net/experiments/confirmation/",
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
    assert (ROOT / "estate" / "index.html").is_file(), "estate snapshot HTML must exist"
    assert (ROOT / "estate.json").is_file(), "estate snapshot contract must exist"
    assert (ROOT / "factory" / "index.html").is_file(), "factory RECORD HTML must exist"
    assert (ROOT / "factory.json").is_file(), "factory RECORD contract must exist"
    assert (ROOT / "origin" / "index.html").is_file(), "origin lock RECORD HTML must exist"
    assert (ROOT / "origin.json").is_file(), "origin lock contract must exist"
    origin_src = (ROOT / "origin" / "index.html").read_text(encoding="utf-8")
    assert "script-src 'none'" in origin_src
    assert "INC-05" in origin_src
    assert "https://a11oy.com" not in origin_src
    origin_contract = json.loads((ROOT / "origin.json").read_text(encoding="utf-8"))
    assert origin_contract["incident"] == "INC-05"
    assert origin_contract["boundaries"]["does_not_change_dns"] is True
    assert origin_contract["boundaries"]["grok_spa_not_published_here"] is True
    assert (ROOT / "frontiers" / "index.html").is_file(), "named frontiers SNAPSHOT HTML must exist"
    assert (ROOT / "frontiers.json").is_file(), "named frontiers contract must exist"
    frontiers_src = (ROOT / "frontiers" / "index.html").read_text(encoding="utf-8")
    assert "script-src 'none'" in frontiers_src
    assert "STRUCTURAL-ONLY" in frontiers_src
    assert "https://a11oy.com" not in frontiers_src
    frontiers_contract = json.loads((ROOT / "frontiers.json").read_text(encoding="utf-8"))
    assert frontiers_contract["promotion"]["verdict"] == "BLOCKED"
    assert frontiers_contract["boundaries"]["does_not_rewrite_factory"] is True
    assert frontiers_contract["boundaries"]["grok_spa_not_published_here"] is True
    assert frontiers_contract["compiler"]["fail_closed"] is True
    assert frontiers_contract["compiler"]["n27"] == "BLOCKED NEVER_DISPATCH"
    assert frontiers_contract["compiler"]["production_certificate"] is False
    assert 'id="compiler"' in frontiers_src
    assert "NEVER_DISPATCH" in frontiers_src
    plane = ROOT / "estate" / "plane"
    assert (plane / "index.html").is_file(), "estate OS plane hologram HTML must exist"
    assert (plane / "app.js").is_file(), "estate OS plane hologram script must exist"
    assert (plane / "data.json").is_file(), "estate OS plane hologram bake must exist"
    assert (plane / "plane.css").is_file(), "estate OS plane hologram styles must exist"
    plane_html = (plane / "index.html").read_text(encoding="utf-8")
    plane_js = (plane / "app.js").read_text(encoding="utf-8")
    assert "script-src 'self'" in plane_html
    assert "not a live dashboard" in plane_html.lower()
    assert "not a fourth origin" in plane_html.lower()
    assert "PROPOSE_ONLY" in plane_html
    assert "Conjecture 1" in plane_html
    assert 'href="/verify"' not in plane_html and 'href="/verify/"' not in plane_html
    assert "https://a11oy.com" not in plane_html
    assert "https://a11oy.com" not in plane_js
    hologram = ROOT / "estate" / "os"
    assert (hologram / "index.html").is_file(), "estate catalog hologram HTML must exist"
    assert (hologram / "app.js").is_file(), "estate catalog hologram script must exist"
    assert (hologram / "data.json").is_file(), "estate catalog hologram bake must exist"
    assert (hologram / "os.css").is_file(), "estate catalog hologram styles must exist"
    hologram_html = (hologram / "index.html").read_text(encoding="utf-8")
    hologram_js = (hologram / "app.js").read_text(encoding="utf-8")
    assert "script-src 'self'" in hologram_html
    assert "not a live dashboard" in hologram_html.lower()
    assert "not a fourth origin" in hologram_html.lower()
    assert "READ-ONLY" in hologram_html or "read-only" in hologram_html.lower()
    assert "Conjecture 1" in hologram_html
    assert 'href="/verify"' not in hologram_html and 'href="/verify/"' not in hologram_html
    assert "https://a11oy.com" not in hologram_html
    assert "https://a11oy.com" not in hologram_js
    estate_html = (ROOT / "estate" / "index.html").read_text(encoding="utf-8")
    assert 'href="/estate/os/"' in estate_html, "estate snapshot must hand off to the hologram"
    assert 'href="/estate/plane/"' in estate_html, "estate snapshot must hand off to the control-plane hologram"
    assert (ROOT / "command" / "index.html").is_file(), "command RECORD must exist"
    command_source = (ROOT / "command" / "index.html").read_text(encoding="utf-8")
    assert "script-src 'none'" in command_source
    assert "Never a11oy.com." in command_source
    assert "https://a-11-oy.com/series-a" in command_source
    assert "not a live operator console" in command_source.lower()
    assert "Formula authority NONE" in command_source or "formula authority NONE" in command_source
    assert "googleapis.com" not in command_source
    assert "cdn." not in command_source
    assert "https://a11oy.com" not in command_source
    estate_contract = json.loads((ROOT / "estate.json").read_text(encoding="utf-8"))
    # estate.json is the dated 2026-08-31 snapshot. It is kept historical and
    # internally consistent; it is never the current count. Current counts are
    # generated into estate/hf-current.json (check_generated_hf_inventory).
    hub_snapshot = estate_contract["huggingface"]
    public_spaces = hub_snapshot["public_spaces"]
    assert hub_snapshot["spaces_public"] == len(public_spaces) == len(set(public_spaces))
    assert public_spaces == sorted(public_spaces)
    assert all(space.startswith("SZLHOLDINGS/") for space in public_spaces)
    assert estate_contract["reader_guide"].startswith("HISTORICAL:"), (
        "estate.json must say it is the dated historical snapshot"
    )
    assert "/estate/hf-current.json" in estate_contract["reader_guide"]
    assert estate_contract["origins"]["product"] == "https://a-11-oy.com"
    spaces_contract = json.loads((ROOT / "spaces.json").read_text(encoding="utf-8"))
    keep_ids = [item["id"] for item in spaces_contract["keep"]]
    assert keep_ids == [
        "a11oy",
        "killinchu",
        "immune",
        "szl-khipu",
        "szl-atelier",
        "governed-receipt-verifier",
    ]
    assert spaces_contract["cut"]["keep"] == len(keep_ids)
    recapture = estate_contract["recapture_2026_08_30"]
    assert recapture["spaces_json_keep"] == len(keep_ids)
    assert recapture["atlas_keep_7_rewritten"] is False
    assert recapture["unprivate_38"] is False
    assert recapture["operational"] is False
    # KEEP-6 is policy, not Hub state. The verifier's 2026-09-26 NOT_FOUND
    # result remains a dated historical check; the generated hub_presence
    # is authoritative for the current public listing. Its runtime is not
    # inferred. Anatomy and holographic still carry the old Hub record.
    verifier = next(item for item in spaces_contract["keep"] if item["id"] == "governed-receipt-verifier")
    assert "Public Hub application KEEP" not in verifier["why"]
    assert "historical" in verifier["why"] and "hub_presence" in verifier["why"]
    assert "hub_status" not in verifier
    assert verifier["historical_hub_status"] == "NOT_FOUND"
    assert verifier["historical_hub_status_evidence_class"] == "REPORTED"
    assert verifier["historical_hub_status_observed_at"] == "2026-09-26T01:52:53Z"
    fold_by_id = {item["id"]: item for item in spaces_contract["fold"]}
    for hub_entry in (fold_by_id["anatomy"], fold_by_id["holographic"]):
        assert hub_entry.get("hub_status") == "NOT_FOUND", hub_entry["id"]
        assert hub_entry.get("hub_status_evidence_class") == "REPORTED", hub_entry["id"]
    assert fold_by_id["anatomy"]["dest"] == "https://a-11-oy.com/anatomy-v5"
    assert fold_by_id["holographic"]["dest"] == "https://a-11-oy.com/anatomy-v5"
    assert "re-privatized" not in fold_by_id["anatomy"]["why"]
    assert "david-leads" not in keep_ids
    assert "anatomy" not in keep_ids
    assert "szl-real-estate" not in keep_ids
    nexus = next(item for item in spaces_contract["fold"] if item["id"] == "nexus")
    assert nexus["dest"] == "https://a-11-oy.com/nexus"
    models_contract = json.loads((ROOT / "models.json").read_text(encoding="utf-8"))
    assert models_contract["operational"] is False
    assert models_contract["trained_all"] is all(
        item["trained"] for item in models_contract["models"]
    )
    assert models_contract["energy"] == "UNAVAILABLE"
    assert models_contract["boundaries"]["atlas_keep_7_not_rewritten"] is True
    assert not any(item.get("operational") for item in models_contract["models"])
    check_generated_hf_inventory()
    assert (ROOT / "atlas.json").is_file(), "atlas machine contract must exist"
    atlas_contract = json.loads((ROOT / "atlas.json").read_text(encoding="utf-8"))
    assert atlas_contract["status"]["state"] == "HISTORICAL", (
        "dated atlas.json observations must not claim CURRENT"
    )
    assert atlas_contract["status"]["current_public_inventory"] == "/public-inventory.json"
    assert atlas_contract["status"]["probed_at"] == atlas_contract["hub_snapshot"]["observed_at"]
    current_public = json.loads(HF_INVENTORY.read_text(encoding="utf-8"))
    assert atlas_contract["hub_snapshot"]["observed_at"] < current_public["observed_at"]
    assert (ROOT / "notes" / "index.html").is_file(), "dated notes must exist"
    assert (ROOT / "atelier" / "index.html").is_file(), "atelier walk must exist"
    assert (ROOT / "khipu" / "index.html").is_file(), "khipu RECORD must exist"
    khipu_src = (ROOT / "khipu" / "index.html").read_text(encoding="utf-8")
    assert "Kernel is not run here" in khipu_src or "does not run the kernel" in khipu_src
    assert "Conjecture 1" in khipu_src
    assert "https://a11oy.com" not in khipu_src
    assert "Never a11oy.com" in khipu_src or "never a11oy.com" in khipu_src
    assert "cdn." not in khipu_src
    assert (ROOT / "decision" / "index.html").is_file(), "decision RECORD must exist"
    assert (ROOT / "decision.json").is_file(), "decision machine contract must exist"
    for stub in ("terra", "aegis", "puriq-markets", "counsel", "vessels", "five-space", "nexus"):
        path = ROOT / stub / "index.html"
        assert path.is_file(), f"{stub} RECORD stub must exist"
        text = path.read_text(encoding="utf-8")
        assert "script-src 'none'" in text, f"{stub} must ship CSP script-src none"
        assert "googleapis.com" not in text
        assert "cdn." not in text
        assert "Formula authority NONE" in text or "formula authority NONE" in text
        assert "https://a11oy.com" not in text
        assert "Never a11oy.com." in text
    psyche = ROOT / "ayllu" / "psyche" / "index.html"
    assert psyche.is_file(), "Wiñay/Huklla/IIT honesty RECORD must exist"
    psyche_text = psyche.read_text(encoding="utf-8")
    assert "script-src 'none'" in psyche_text
    assert "connect-src 'none'" in psyche_text
    assert "googleapis.com" not in psyche_text
    assert "cdn." not in psyche_text
    assert "https://a11oy.com" not in psyche_text
    assert "Never a11oy.com." in psyche_text
    assert "UNAVAILABLE" in psyche_text
    assert "CONJECTURE" in psyche_text
    assert "this origin does not run" in psyche_text.lower()
    assert "Not IIT" in psyche_text or "not IIT" in psyche_text
    winay = json.loads((ROOT / "ayllu" / "winay.json").read_text(encoding="utf-8"))
    assert winay["labels"]["iit_phi_s"] == "UNAVAILABLE"
    assert winay["labels"]["presence"] == "CONJECTURE"
    assert winay["iit"]["phi_s"] is None
    assert winay["boundaries"]["this_origin_runs_the_pulse"] is False
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
    assert any(
        anchor.get("href") == "/atelier/" for anchor in surface.anchors
    ), "the root proof registry must expose the atelier walk"
    assert any(
        anchor.get("href") == "/khipu/" for anchor in surface.anchors
    ), "the root proof registry must expose the khipu RECORD"
    # The former subtitle "Alloy by SZL Holdings" was retired 2026-08-30 (lexicon_gate);
    # the canon line now records the retirement as history, and this check enforces that record.
    assert "Former subtitle" in source
    assert "id=\"summary\"" in source
    assert "id=\"record\"" in source
    assert "id=\"github-atlas\"" in source
    assert "Ninety seconds" in source
    assert "Origin health document" in source
    assert "healthz is not published" in source.lower()
    assert "https://a11oy.net/record/" in source
    assert "The RECORD index lives at" in source
    # record.json carries no signature field; no RECORD surface may call the index signed.
    for record_surface in (INDEX, ROOT / "record" / "index.html", ROOT / "record.json"):
        assert "signed RECORD" not in record_surface.read_text(encoding="utf-8"), (
            f"{record_surface.relative_to(ROOT)} must not call the RECORD index signed"
        )
    # record.json public_key labels stay in the SZL evidence vocabulary
    # (szl-holdings/.github docs/PUBLIC_EXPERIENCE_FRONTIER_V4.md).
    szl_evidence_classes = {
        "MEASURED", "REPORTED", "MODELED", "UNAVAILABLE", "UNSIGNED", "CONJECTURE",
    }
    pending = [json.loads((ROOT / "record.json").read_text(encoding="utf-8"))["public_key"]]
    while pending:
        node = pending.pop()
        if isinstance(node, list):
            pending.extend(node)
        elif isinstance(node, dict):
            for key, value in node.items():
                if key.endswith("evidence_class"):
                    assert value in szl_evidence_classes, (
                        f"record.json public_key {key}={value!r} is outside the SZL evidence vocabulary"
                    )
                pending.append(value)
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
    # audit 2026-08-30: primary nav trimmed to exactly six peers — Record, Spec,
    # Conformance, Security, Diligence, Estate. Atlas and Index stay on-page
    # sections: the #atlas / #index fragments still resolve, the sections are
    # unchanged below the fold; they are no longer top-level nav peers.
    assert ">Record</a>" in nav_block and 'href="/record/"' in nav_block
    assert ">Spec ↗</a>" in nav_block and (
        'href="https://github.com/szl-holdings/governed-receipt-spec"' in nav_block
    ), "Spec peer links the governed-receipt-spec repo"
    assert ">Conformance ↗</a>" in nav_block and (
        'href="https://huggingface.co/datasets/SZLHOLDINGS/governed-receipts-bench"' in nav_block
    ), "Conformance peer links the receipts bench dataset"
    assert ">Security</a>" in nav_block and 'href="/.well-known/security.txt"' in nav_block
    assert ">Diligence</a>" in nav_block and 'href="/diligence/"' in nav_block
    assert ">Estate</a>" in nav_block and 'href="/estate/"' in nav_block
    assert ">Atlas</a>" not in nav_block and 'href="#atlas"' not in nav_block, (
        "Atlas moved out of the trimmed nav; the #atlas section stays on-page"
    )
    assert ">Index</a>" not in nav_block and 'href="#index"' not in nav_block, (
        "Index moved out of the trimmed nav; the #index section stays on-page"
    )
    assert 'href="/atelier/"' not in nav_block, "Atelier is a lab under Index, not a nav peer"
    assert 'href="/notes/"' not in nav_block, "Notes is a lab under Index, not a nav peer"
    assert "Evidence index" not in nav_block
    assert "Live reads" not in nav_block
    assert "Public registry" not in nav_block
    assert "Walk 40 models" not in source, "atelier is not a first-fold CTA"
    assert "Open RECORD" in source, "first fold CTA is RECORD"
    assert 'id="index"' in source, "Index catalog must exist on the proof homepage"
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
    assert _links_to_host(
        readyz_html, "a-11-oy.com"
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

    # The #inventory count bar renders /public-inventory.json, generated by
    # scripts/generate_hf_inventory.py (the 2026-08-31 capture is kept as
    # public-inventory-2026-08-31.json). It must stay labelled as a dated
    # snapshot, with the observed_at badge above the counts that
    # scripts/inventory_cards.js marks STALE after 24 hours.
    snapshot_badges = [
        item for _, item in surface.elements if item.get("id") == "invSnapshotState"
    ]
    assert len(snapshot_badges) == 1, (
        "the inventory count bar must carry exactly one dated-snapshot badge"
    )
    assert snapshot_badges[0].get("data-state") == "unavailable"
    assert "SNAPSHOT DATE UNREAD" in source
    assert "A dated public Hub snapshot, as cards. Not a live count." in source
    assert "Every public artifact this origin already publishes" not in source, (
        "the frozen inventory snapshot must not return to a present-tense heading"
    )
    inventory_at = source.index('id="inventory"')
    snapshot_badge_at = source.index('id="invSnapshotState"')
    assert inventory_at < snapshot_badge_at < source.index('id="invTotal"'), (
        "the snapshot badge must sit inside #inventory, above the count bar it dates"
    )
    inventory_cards = (ROOT / "scripts" / "inventory_cards.js").read_text(
        encoding="utf-8"
    )
    assert "renderSnapshotAge(inventory, Date.now());" in inventory_cards
    assert "age > DAY_MS" in inventory_cards

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
    # 2026-09-25: anatomy and holographic Hub Spaces answer HTTP 401 to the
    # public; their cards drop REPORTED (14 -> 12) and carry no link.
    # 2026-09-26: an authenticated SZLHOLDINGS org-admin read returned 404 for
    # anatomy, holographic and governed-receipt-verifier. The verifier later
    # reappeared in the generated public listing, while the dated row remains
    # historical. The two curated missing cards stay unlinked.
    assert source.count('<span class="stack-truth">REPORTED</span>') == 12
    assert source.count('<span class="stack-truth">NOT FOUND</span>') == 2
    assert "RETIRED/PRIVATE" not in source
    assert (
        '<div class="dossier-row"><span class="dossier-index">07</span><span><b>Verifier Space</b>'
        '<small>Historical check: SZLHOLDINGS/governed-receipt-verifier returned HTTP 401 '
        'to the public and 404 to an authenticated org-admin read on 2026-09-26. '
        'Current public listings appear in the generated rows below; runtime remains '
        'unverified.</small></span><span class="dossier-action">HISTORICAL</span></div>' in source
    ), "dossier row 07 must distinguish its historical check from the current listing"
    curated, marker, _ = source.partition("<!-- hf-current:live-space-rows begin")
    assert marker, "current live-space rows marker is required"
    for retired in ("anatomy", "holographic", "governed-receipt-verifier"):
        assert f'href="https://huggingface.co/spaces/SZLHOLDINGS/{retired}"' not in curated
    assert 'href="https://github.com/szl-holdings/szl-experiments"' not in source
    assert (
        "REPORTED identifies listing metadata only; runtime state, capability, "
        "and availability are not checked in this section." in source
    ), "curated Hub cards need bounded non-runtime evidence labels"
    assert "independent verification entry point" not in source.lower()
    assert "public verification entry point" in source.lower()
    assert source.count('data-static="product-route"') == 4
    assert source.count("NOT PROBED · UNKNOWN") == 5, (
        "four product rows and the explanatory boundary must remain explicit"
    )
    # The browser-read Hub Space rows are generated from
    # estate/hf-current.json live_space_cards (the /spaces.json KEEP ids the
    # public listing still returns); the inline script reads the same file for
    # its bindings, so no Space id is typed in this check or in the script.
    live_cards = json.loads(HF_CURRENT.read_text(encoding="utf-8"))["live_space_cards"]
    assert live_cards, "at least one KEEP Space must be publicly listed to render a live row"
    assert source.count('data-space="SZLHOLDINGS/') == len(live_cards)
    expected_space_bindings = {
        card["id"]: (card["api"], card["href"]) for card in live_cards
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
    assert 'fetchJson(new URL("/estate/hf-current.json",window.location.href).href)' in source
    assert "current.live_space_cards" in source
    assert 'probePolicy.classifyFailure("SPACE_BINDINGS_UNAVAILABLE")' in source
    assert "szl-estate-live" not in source and "receipt-chain-live" not in source, (
        "absent Hub Spaces must not be probed or linked from the front door"
    )
    assert source.count("NOT OBSERVED · UNAVAILABLE") == len(live_cards) + 1, (
        "every HF fallback and the no-script explanation must fail closed"
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
    assert 'class="frontier-kernel"' in source
    assert "Lean-8 kernel" in source
    assert "not ROADMAP" in source
    frontier_kernel = re.search(
        r'class="frontier-kernel"[^>]*>.*?</p>',
        source,
        re.I | re.S,
    )
    assert frontier_kernel, "Frontier must host a live Lean-8 kernel chip"
    assert "stack-truth roadmap" not in frontier_kernel.group(0)
    assert "cls-roadmap" not in frontier_kernel.group(0)
    assert ">25<" not in frontier_kernel.group(0)
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
    # 2026-09-25: the dossier verifier row points at product-origin /verify,
    # never the Perplexity sidecar (origin-drift-2026-09-02.json marks
    # a11oy-verify.pplx.app NOT_PRODUCT_ORIGIN).
    assert "pplx.app" not in source
    assert (
        '<a class="dossier-row" href="https://a-11-oy.com/verify" target="_blank" '
        'rel="noopener"><span class="dossier-index">05</span>' in source
    ), "dossier row 05 must link product-origin /verify"
    assert "The dated static registry snapshot remains visible" in source
    assert 'data-static-snapshot="hf-current"' in source
    # audit 2026-08-30: static fallbacks are honest em-dashes (the same state a
    # failed live read renders), never hand-typed estate counts; the browser
    # refresh still fills live numbers, and every count zone points at the
    # generated estate/hf-current.json (the dated estate.json is historical).
    assert '<b id="atlasTotal">—</b>' in source
    assert '<b id="atlasModels">—</b>' in source
    assert '<b id="atlasDatasets">—</b>' in source
    assert '<b id="atlasCollections">—</b>' in source
    assert '<b id="atlasBuckets">—</b>' in source
    assert "estate counts render from estate/hf-current.json" in source, (
        "count placeholders must point at the generated estate/hf-current.json"
    )
    assert "estate counts render from estate.json manifest" not in source
    assert not re.search(r'id="atlas\w+">\d+<', source), (
        "no atlas stat may carry a hand-typed numeric fallback"
    )
    assert "2026-08-11" not in source, (
        "the noscript/fallback snapshot must not retain the prior 2026-08-11 counts"
    )
    assert source.count('<span class="stack-truth roadmap">ROADMAP</span>') == 8, (
        "empty Hub cards and KERNEL originals stay ROADMAP; adapters with bytes are REPORTED"
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
    for model in ("qantu", "waman", "chakana", "tinku"):
        assert f'href="https://huggingface.co/SZLHOLDINGS/{model}"' not in source
        card = next((line for line in source.splitlines() if f"<h3>{model}</h3>" in line), None)
        assert card is not None and '<div class="stack-card">' in card
        assert "No public Hub card" in card and "ROADMAP" in card
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
