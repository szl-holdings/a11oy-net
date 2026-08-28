#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Validate the investor/developer diligence room and machine contract."""

from __future__ import annotations

import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DILIGENCE = ROOT / "diligence" / "index.html"
CHAT = ROOT / "chat" / "index.html"
CODE = ROOT / "code" / "index.html"
RECORD = ROOT / "record" / "index.html"
NOTES = ROOT / "notes" / "index.html"
EVIDENCE = ROOT / "evidence.json"
RECORD_JSON = ROOT / "record.json"
ATLAS_JSON = ROOT / "atlas.json"
LLMS = ROOT / "llms.txt"
NOT_FOUND = ROOT / "404.html"
STYLE = ROOT / "assets" / "diligence.css"
ICON = ROOT / "assets" / "a11oy-mark.svg"
BUILD_INFO = ROOT / "api" / "build-info" / "index.html"
READYZ = ROOT / "readyz" / "index.html"
MANIFEST = ROOT / "site.webmanifest"
MANIFEST_ALIAS = ROOT / "manifest.webmanifest"


class Document(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.anchors: list[dict[str, str | None]] = []
        self.ids: set[str] = set()
        self.links: list[dict[str, str | None]] = []
        self.metas: list[dict[str, str | None]] = []
        self.scripts = 0
        self.main_count = 0
        self.h1_count = 0

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        item = dict(attrs)
        if item.get("id"):
            self.ids.add(str(item["id"]))
        if tag == "a":
            self.anchors.append(item)
        elif tag == "link":
            self.links.append(item)
        elif tag == "meta":
            self.metas.append(item)
        elif tag == "script":
            self.scripts += 1
        elif tag == "main":
            self.main_count += 1
        elif tag == "h1":
            self.h1_count += 1


def check_document(path: Path, *, canonical: str | None) -> Document:
    source = path.read_text(encoding="utf-8")
    document = Document()
    document.feed(source)
    assert document.main_count == 1, f"{path}: exactly one main landmark required"
    assert document.h1_count == 1, f"{path}: exactly one h1 required"
    assert '<html lang="en">' in source, f"{path}: document language required"
    assert 'name="referrer" content="no-referrer"' in source
    assert 'http-equiv="Content-Security-Policy"' in source
    assert document.scripts == 0, f"{path}: no JavaScript is required"
    if canonical:
        assert {"rel": "canonical", "href": canonical} in document.links
    for anchor in document.anchors:
        href = anchor.get("href") or ""
        parsed = urlparse(href)
        if parsed.scheme:
            assert parsed.scheme == "https", f"non-HTTPS link: {href}"
        if anchor.get("target") == "_blank":
            assert "noopener" in (anchor.get("rel") or "").split()
    return document


def embedded_json_contract(path: Path, aria_label: str) -> dict[str, object]:
    source = path.read_text(encoding="utf-8")
    pattern = re.compile(
        r'<pre(?=[^>]*\baria-label="'
        + re.escape(aria_label)
        + r'")[^>]*>\s*<code>(.*?)</code>\s*</pre>',
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(source)
    assert match is not None, f"{path}: missing {aria_label!r} JSON contract"
    value = json.loads(html.unescape(match.group(1)))
    assert isinstance(value, dict), f"{path}: embedded contract must be an object"
    return value


def check() -> None:
    for required in (
        DILIGENCE,
        CHAT,
        CODE,
        RECORD,
        NOTES,
        EVIDENCE,
        RECORD_JSON,
        ATLAS_JSON,
        LLMS,
        NOT_FOUND,
        STYLE,
        ICON,
        ROOT / "assets" / "kanchay.css",
        BUILD_INFO,
        READYZ,
        MANIFEST,
        MANIFEST_ALIAS,
    ):
        assert required.is_file() and required.stat().st_size > 0, required

    diligence = check_document(
        DILIGENCE, canonical="https://a11oy.net/diligence/"
    )
    assert {"main", "scope", "investors", "developers", "risks", "labels", "summary"} <= diligence.ids
    assert {"rel": "stylesheet", "href": "/assets/diligence.css"} in diligence.links
    assert {"rel": "stylesheet", "href": "/assets/kanchay.css"} in diligence.links
    assert 'id="main" tabindex="-1"' in DILIGENCE.read_text(encoding="utf-8")
    diligence_source = DILIGENCE.read_text(encoding="utf-8")
    assert "Alloy by SZL Holdings" in diligence_source
    assert "Origin health document" in diligence_source
    assert "healthz is not published" in diligence_source.lower()
    assert "Receipt store on this origin" in diligence_source
    diligence_hrefs = {anchor.get("href") for anchor in diligence.anchors}
    assert {
        "/evidence.json",
        "/record.json",
        "/atlas.json",
        "/site.webmanifest",
        "/llms.txt",
        "/api/build-info/",
        "/health.json",
        "/readyz/",
        "/record/",
        "/notes/",
        "/chat/",
        "/code/",
    } <= diligence_hrefs, "diligence must link every local machine contract"
    diligence_nav = re.search(
        r"<nav\b.*?</nav>", diligence_source, re.IGNORECASE | re.DOTALL
    )
    assert diligence_nav is not None
    assert "Chat gateway" not in diligence_nav.group(0)
    assert "Code gateway" not in diligence_nav.group(0)
    assert "Product ↗" in diligence_nav.group(0)
    assert diligence_nav.group(0).count("origin-switch") == 1, (
        "diligence must keep a single Product | Proof header"
    )
    assert 'id="handoffs"' in diligence_source
    assert "/chat/" in diligence_source and "/code/" in diligence_source
    record = check_document(RECORD, canonical="https://a11oy.net/record/")
    notes = check_document(NOTES, canonical="https://a11oy.net/notes/")
    assert {"main", "permalinks", "receipt-ids", "live-store", "stores", "verify"} <= record.ids
    assert any(anchor.get("href") == "https://a-11-oy.com/verify" for anchor in record.anchors)
    assert any(anchor.get("href") == "/record.json" for anchor in record.anchors)
    assert "Alloy by SZL Holdings" in RECORD.read_text(encoding="utf-8")
    assert "Alloy by SZL Holdings" in NOTES.read_text(encoding="utf-8")
    assert "Product ↗" in RECORD.read_text(encoding="utf-8")
    assert "Product ↗" in NOTES.read_text(encoding="utf-8")
    assert RECORD.read_text(encoding="utf-8").count("origin-switch") == 1
    assert NOTES.read_text(encoding="utf-8").count("origin-switch") == 1
    assert "https://a11oy.com" not in RECORD.read_text(encoding="utf-8")
    assert "https://huggingface.co/spaces" not in [
        link.get("href") for link in record.links if link.get("rel") == "canonical"
    ]
    check_document(NOT_FOUND, canonical=None)

    chat = check_document(CHAT, canonical="https://a11oy.net/chat/")
    code = check_document(CODE, canonical="https://a11oy.net/code/")
    for document, required_hrefs in (
        (
            chat,
            {
                "https://a-11-oy.com/console",
                "https://a-11-oy.com/api/a11oy/v1/honest",
                "https://a-11-oy.com/api/build-info",
                "https://a-11-oy.com/verify",
                "https://github.com/szl-holdings/a11oy",
            },
        ),
        (
            code,
            {
                "https://a-11-oy.com/code",
                "https://a-11-oy.com/api/a11oy/v1/code/capabilities",
                "https://a-11-oy.com/api/a11oy/v1/code/runloop/health",
                "https://a-11-oy.com/verify",
                "https://github.com/szl-holdings/a11oy",
            },
        ),
    ):
        hrefs = {anchor.get("href") for anchor in document.anchors}
        assert required_hrefs <= hrefs
    assert "does not authenticate a user" in CHAT.read_text(encoding="utf-8")
    assert "does not execute code" in CODE.read_text(encoding="utf-8")

    build_info = embedded_json_contract(BUILD_INFO, "Static build-info contract")
    assert build_info == {
        "site": "a11oy.net",
        "surface": "public evidence front door",
        "artifact_kind": "static",
        "status": "PARTIAL",
        "evidence_class": "REPORTED",
        "build_info": {
            "source_repository": "https://github.com/szl-holdings/a11oy-net",
            "scope": "public documentation and evidence links only",
            "immutable_build_identity": "NOT_CLAIMED",
            "source_revision": "NOT_PUBLISHED_BY_THIS_ROUTE",
        },
        "product_runtime_truth": "NOT_IMPLIED",
        "runtime_source": "https://a-11-oy.com/api/a11oy/v1/honest",
        "observed_at_utc": None,
    }
    readyz = embedded_json_contract(READYZ, "Static reachability contract")
    assert readyz == {
        "surface": "a11oy.net",
        "artifact": "public evidence front door",
        "artifact_kind": "static",
        "readyz": "REACHABILITY_ONLY",
        "readyz_is_health_url": False,
        "healthz": "NOT_PUBLISHED",
        "healthz_is_health_url": False,
        "json_probe_document": "https://a11oy.net/health.json",
        "product_runtime_readiness": "NOT_MEASURED",
        "immutable_build_identity": "NOT_CLAIMED",
        "runtime_source": "https://a-11-oy.com/api/a11oy/v1/honest",
    }
    health = json.loads((ROOT / "health.json").read_text(encoding="utf-8"))
    assert health["path"] == "/health.json"
    assert health["artifact_kind"] == "static"
    assert health["dsse_live"] == "NOT_CLAIMED"
    assert health["uptime"] == "NOT_MEASURED"
    assert health["readyz"] == "NOT_A_HEALTH_URL"
    assert health["healthz"] == "NOT_PUBLISHED"
    assert health["json_probe_document"] == "https://a11oy.net/health.json"
    assert health["record"] == "https://a11oy.net/record/"
    assert health["interactive_verifier"] == "https://a-11-oy.com/verify"
    assert not (ROOT / "healthz").exists()
    assert not (ROOT / "healthz.html").exists()

    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert evidence["contract_version"] == "1.0.0"
    assert evidence["status"]["state"] == "PARTIAL"
    assert evidence["status"]["evidence_class"] == "REPORTED"
    assert evidence["boundaries"] == {
        "product_runtime_is_separate": True,
        "private_resources_requested": False,
        "public_hub_metadata_is_authenticated_inventory": False,
        "http_response_proves_capability": False,
        "static_readyz_proves_product_readiness": False,
        "live_edge_security_headers_deployment_proven": False,
    }
    assert evidence["observations"]["edge_security_headers"] == {
        "state": "UNKNOWN",
        "evidence_class": "UNKNOWN",
        "source_uri": None,
        "observed_at_utc": None,
        "source_revision": None,
        "reason": (
            "No source-bound live response-header readback is attached to this "
            "candidate. The committed _headers file is policy intent, not "
            "deployment evidence."
        ),
    }
    names = {entry["name"] for entry in evidence["entrypoints"]}
    assert {
        "diligence_room",
        "record_index",
        "record_contract",
        "hub_atlas",
        "dated_notes",
        "governed_console_gateway",
        "governed_code_gateway",
        "static_build_info",
        "static_health_document",
        "static_reachability",
        "product_honesty_manifest",
        "receipt_verifier",
        "product_lake_receipts",
        "implementation_source",
        "proof_registry_source",
        "public_hub_registry",
        "security_reporting",
    } == names
    assert set(evidence["labels"]) == {
        "MEASURED",
        "REPORTED",
        "MODELED",
        "HEURISTIC",
        "UNKNOWN",
        "UNAVAILABLE",
    }
    llms = LLMS.read_text(encoding="utf-8")
    assert "https://a11oy.net/evidence.json" in llms
    assert "https://a11oy.net/record/" in llms
    assert "does not establish A11oy product-runtime readiness" in llms
    assert "This repository has no receipt store" in llms or "no receipt store" in llms
    assert "SZLHOLDINGS/szl-evidence" in llms
    assert "CNAME is a11oy.net" in llms
    assert "_headers is policy intent" in llms
    assert "/healthz is not published" in llms
    assert "https://a11oy.net/health.json" in llms
    record_contract = json.loads(RECORD_JSON.read_text(encoding="utf-8"))
    assert record_contract["surface"]["url"] == "https://a11oy.net/record/"
    assert record_contract["permalinks"] == {
        "record_html": "https://a11oy.net/record/",
        "record_json": "https://a11oy.net/record.json",
        "interactive_verify_tool": "https://a-11-oy.com/verify",
    }
    assert "Different hosts" in record_contract["reader_guide"] or "different hosts" in record_contract["reader_guide"].lower()
    assert record_contract["boundaries"]["interactive_verifier_cloned"] is False
    assert record_contract["boundaries"]["product_runtime_required_for_first_paint"] is False
    assert record_contract["boundaries"]["receipt_database_hosted_here"] is False
    assert record_contract["boundaries"]["lake_api_hosted_here"] is False
    assert record_contract["boundaries"]["this_origin_is_not_a_product_host"] is True
    assert record_contract["live_store"]["hosted_here"] is False
    assert record_contract["live_store"]["query_api"]["path"] == "/api/lake/v1/receipts"
    assert record_contract["live_store"]["query_api"]["url"] == "https://a-11-oy.com/api/lake/v1/receipts"
    assert record_contract["live_store"]["persistence"]["resource"] == "SZLHOLDINGS/szl-evidence"
    assert record_contract["live_store"]["persistence"]["public_listing"] is False
    assert record_contract["status"]["receipt_ids"] == []
    assert record_contract["status"]["receipt_ids_class"] == "UNAVAILABLE"
    atlas_contract = json.loads(ATLAS_JSON.read_text(encoding="utf-8"))
    assert atlas_contract["hub_snapshot"]["observed_at"] == "2026-08-28"
    assert atlas_contract["hub_snapshot"]["n"] == 57
    assert atlas_contract["boundaries"]["reachability_is_not_quality"] is True
    assert atlas_contract["boundaries"]["killinchu_named_resources_excluded"] is True
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["start_url"] == "/"
    assert MANIFEST_ALIAS.read_bytes() == MANIFEST.read_bytes()
    diligence_source = DILIGENCE.read_text(encoding="utf-8")
    assert "durable operating boundaries" not in diligence_source
    assert "source-bound live readback URI" in diligence_source
    css = STYLE.read_text(encoding="utf-8")
    assert "@media print" in css
    assert "@media(prefers-reduced-motion:reduce)" in css
    assert "--void:#080c14" in css
    assert "--proof:#3af4c8" in css
    assert "--lattice:#5b8dee" in css
    assert "--gold:#d7b96b" in css
    assert "#c9b787" not in css.lower()
    assert "#5fb3a3" not in css.lower()
    assert "Product ↗" in CHAT.read_text(encoding="utf-8")
    assert "Product ↗" in CODE.read_text(encoding="utf-8")
    assert "Diligence handoff" in CHAT.read_text(encoding="utf-8")
    assert "Diligence handoff" in CODE.read_text(encoding="utf-8")
    assert 'href="/investor"' not in diligence_source
    assert not (ROOT / "investor").exists()
    assert not (ROOT / "verify").exists()
    assert "this registry does not clone" in diligence_source
    chat_source = CHAT.read_text(encoding="utf-8")
    code_source = CODE.read_text(encoding="utf-8")
    assert chat_source.count("empty-panel") == 1
    assert code_source.count("empty-panel") == 1
    assert "https://a-11-oy.com/verify" in llms
    assert "There is no /investor route" in llms
    not_found = NOT_FOUND.read_text(encoding="utf-8")
    assert "no local /verify clone" in not_found
    assert "no /investor route" in not_found


if __name__ == "__main__":
    check()
    print("OK: diligence room and machine evidence contract are intact.")
