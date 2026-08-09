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
EVIDENCE = ROOT / "evidence.json"
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
        EVIDENCE,
        LLMS,
        NOT_FOUND,
        STYLE,
        ICON,
        BUILD_INFO,
        READYZ,
        MANIFEST,
        MANIFEST_ALIAS,
    ):
        assert required.is_file() and required.stat().st_size > 0, required

    diligence = check_document(
        DILIGENCE, canonical="https://a11oy.net/diligence/"
    )
    assert {"main", "scope", "investors", "developers", "risks", "labels"} <= diligence.ids
    assert {"rel": "stylesheet", "href": "/assets/diligence.css"} in diligence.links
    assert 'id="main" tabindex="-1"' in DILIGENCE.read_text(encoding="utf-8")
    diligence_hrefs = {anchor.get("href") for anchor in diligence.anchors}
    assert {
        "/evidence.json",
        "/site.webmanifest",
        "/llms.txt",
        "/api/build-info/",
        "/readyz/",
    } <= diligence_hrefs, "diligence must link every local machine contract"
    check_document(NOT_FOUND, canonical=None)

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
        "product_runtime_readiness": "NOT_MEASURED",
        "immutable_build_identity": "NOT_CLAIMED",
        "runtime_source": "https://a-11-oy.com/api/a11oy/v1/honest",
    }

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
        "static_build_info",
        "static_reachability",
        "product_honesty_manifest",
        "receipt_verifier",
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
    assert "does not establish A11oy product-runtime readiness" in llms
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["start_url"] == "/"
    assert MANIFEST_ALIAS.read_bytes() == MANIFEST.read_bytes()
    diligence_source = DILIGENCE.read_text(encoding="utf-8")
    assert "durable operating boundaries" not in diligence_source
    assert "source-bound live readback URI" in diligence_source
    css = STYLE.read_text(encoding="utf-8")
    assert "@media print" in css
    assert "@media(prefers-reduced-motion:reduce)" in css


if __name__ == "__main__":
    check()
    print("OK: diligence room and machine evidence contract are intact.")
