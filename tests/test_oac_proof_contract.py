#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bounded OAC proof record: release handoff is not a live provider probe."""

from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
OAC = ROOT / "oac"
SOURCE = "234a2dfb4c511318febfd20ca2f695fa9cb2ea8c"
HUB = "4bf4d94161c0d135af6b5a3bc25f45b06f6e3979"
MODEL = "dd7d109813abcd90c5250106dc2eabd2804e7ac3"
DATASET = "f7ab6170bf78138b187b8cb707d374a25ad85375"
ARTIFACT = "7555d5ab6f6f1c56f7304ba365904479b7fde8819b0b183b8455a3f71f61a4b3"
V2_SOURCE = "a975c6f35f215a120ae68fea3fe69226b9a0a53f"
V2_CARD_SOURCE = "6330dea7318effba583a6501346fee590174a39f"
V2_INITIAL_HUB = "ff107198aa257ce1bb1841377d553bee3f90be41"
V2_HUB = "a824a32d91a383d33a1e1e595f11b8362d1b4efa"
V2_APPLICATION = "3f7554efaddf086680b25301502c3bf176d83089"
V2_SPACE = "1c33503830a12c5661fc3ee8cd0a4b3a75451c25"
V2_WITNESS_RUN = "37728965604"
V2_ORIGIN = "https://szlholdings-oac-system-health-lab.hf.space"
V2_WITNESS_DIGEST = "sha256:cd3de50ce41f911e7636b30766dc27105c6ef2e4684733b3fe756840868ecc2d"


class Surface(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


def test_oac_release_is_exact_handoff_not_current_probe():
    data = (OAC / "release.json").read_bytes()
    assert len(data) < 12000
    record = json.loads(data)
    assert record["schema"] == "szl.oac.release-snapshot.v1"
    assert record["kind"] == "STATIC_DOCUMENT"
    assert record["release_kind"] == "SNAPSHOT"
    assert record["evidence_class"] == "REPORTED"
    assert record["provenance"] == "RELEASE_HANDOFF"
    assert record["snapshot_date"] == "2026-10-02"
    assert record["currentness"] == "NOT_PROBED_BY_STATIC_PAGE"
    assert record["provider_live_verification"] is False
    assert record["production_operational"] is False
    assert record["canonical_url"] == "https://a11oy.net/oac/"
    assert record["source"]["repository"] == "szl-holdings/szl-forge"
    assert record["source"]["revision"] == SOURCE
    assert record["source"]["url"].endswith("/" + SOURCE)
    assert record["hub"]["revision"] == HUB
    assert record["hub"]["url"].endswith("/" + HUB)
    assert record["model"]["revision"] == MODEL
    assert record["model"]["url"].endswith("/" + MODEL)
    assert record["dataset"]["revision"] == DATASET
    assert record["dataset"]["url"].endswith("/" + DATASET)
    assert record["demo"]["url"] == "https://szlholdings-oac-system-health-lab.hf.space"
    assert record["demo"]["mutable"] is True
    assert record["demo"]["pinned_release"] is False
    assert record["demo"]["embedded"] is False
    assert record["ci"]["run_id"] == 36966679696
    assert record["ci"]["status"] == "PASS_REPORTED_FROM_EXACT_SOURCE_HANDOFF"
    assert record["artifact"]["id"] == 11209469462
    assert record["artifact"]["sha256"] == ARTIFACT
    assert record["artifact"]["digest_provenance"] == "GITHUB_API_REPORTED"
    assert record["artifact"]["bytes_verified_here"] is False
    assert record["synthetic_witness"]["runtime_source_revision"] == SOURCE
    assert record["synthetic_witness"]["continuous_monitoring"] is False
    assert record["synthetic_witness"]["independently_replayed_here"] is False
    assert record["scope"]["input"] == "synthetic numeric telemetry"
    for key in ("clinical", "device_control", "patient_data", "new_training"):
        assert record["scope"][key] is False
    assert record["scope"]["production_authorization"] == "NOT_CLAIMED"
    assert record["local_verification"]["provider_evidence_verified"] is False


def test_oac_v2_artifact_is_separate_declared_and_non_authoritative():
    data = (OAC / "v2-artifact.json").read_bytes()
    assert len(data) < 12000
    record = json.loads(data)
    assert record["schema"] == "szl.oac.ops-health-v2-artifact-snapshot.v1"
    assert record["kind"] == "STATIC_DOCUMENT"
    assert record["evidence_class"] == "DECLARED"
    assert record["snapshot_date"] == "2026-10-08"
    assert record["currentness"] == "UNKNOWN"
    assert record["source"]["packaging_revision"] == V2_SOURCE
    assert record["source"]["url"].endswith("/" + V2_SOURCE + "/publishing/oac-ops-health-v2")
    assert record["source"]["card_correction_revision"] == V2_CARD_SOURCE
    assert record["source"]["card_correction_url"].endswith("/" + V2_CARD_SOURCE + "/publishing/oac-ops-health-v2")
    assert record["hub"]["initial_revision"] == V2_INITIAL_HUB
    assert record["hub"]["initial_url"].endswith("/" + V2_INITIAL_HUB)
    assert record["hub"]["revision"] == V2_HUB
    assert record["hub"]["url"].endswith("/" + V2_HUB)
    assert record["hub"]["publisher_run"].endswith("/37726459882")
    assert record["hub"]["source_to_hub_byte_parity_replayed_here"] is False
    assert record["receipt"] == {
        "signed": False,
        "file_digests_recorded": True,
        "declared_local_research_origin_authenticated": False,
    }
    assert record["artifact"]["input_evidence_class"] == "SIMULATED"
    assert record["artifact"]["bounded_input_fields"] == 8
    assert record["artifact"]["proposals"] == ["ALERT", "NO_ALERT", "ABSTAIN"]
    assert record["artifact"]["transformer_checkpoint"] is False
    assert record["artifact"]["independent_evaluation_replayed_here"] is False
    assert record["artifact"]["complete_origin_layer_test_replay_available"] is False
    for key in ("message_acknowledgement", "device_control", "result_interpretation",
                "result_release", "care_decision", "clinical_validation",
                "production_authorization"):
        assert record["authority"][key] is False
    assert record["authority"]["proposal_only"] is True
    assert record["runtime"]["v2_service_claimed"] is True
    assert record["runtime"]["provider_live_verification"] is False
    assert record["runtime"]["status"] == "UNKNOWN"
    assert record["runtime"]["status_scope"] == "CURRENT_STATE_NOT_PROBED_BY_STATIC_PAGE"
    assert record["runtime"]["probe_performed"] is False
    assert record["runtime"]["mutable_v1_demo_is_v2"] is False
    assert record["runtime"]["same_mutable_space_hosts_opt_in_v2"] is True
    assert record["runtime"]["opt_in_preview_url"] == V2_ORIGIN + "/#v2-panel"
    assert record["runtime"]["identity_url"] == V2_ORIGIN + "/api/v2/identity"
    assert record["runtime"]["readiness_url"] == V2_ORIGIN + "/api/v2/readyz"
    witness = record["runtime"]["hosted_witness"]
    assert witness["evidence_class"] == "REPORTED"
    assert witness["completed_at_utc"] == "2026-10-08T04:46:32Z"
    assert witness["application_source_revision"] == V2_APPLICATION
    assert witness["space_revision"] == V2_SPACE
    assert witness["hub_model_revision"] == V2_HUB
    assert witness["run_url"].endswith("/" + V2_WITNESS_RUN)
    assert witness["artifact_id"] == 11529195992
    assert witness["artifact_digest"] == V2_WITNESS_DIGEST
    assert witness["status"] == "PASS_REPORTED"
    assert witness["source_parity_scope"] == "IMMUTABLE_GIT_ARTIFACT_PARITY"
    assert witness["source_parity_count"] == 4
    assert witness["synthetic_case_count"] == 3
    for key in ("source_to_hub_model_byte_parity_replayed_here",
                "independently_replayed_here", "continuous_monitoring",
                "product_site_readiness_established", "clinical_use_authorized",
                "production_promotion_allowed"):
        assert witness[key] is False
    assert record["relationship_to_v1"]["release_record"] == "release.json"
    assert record["relationship_to_v1"]["supersedes_v1_snapshot"] is False
    assert record["local_verification"]["provider_evidence_verified"] is False


def test_oac_html_keeps_identity_scope_and_local_navigation():
    data = (OAC / "index.html").read_bytes()
    assert len(data) < 18000
    source = data.decode("utf-8")
    parser = Surface()
    parser.feed(source)
    elements = parser.elements
    assert not any(tag in {"script", "iframe", "form", "object", "embed"}
                   for tag, _ in elements)
    assert not any(key.startswith("on") for _, attrs in elements for key in attrs)
    assert any(tag == "link" and attrs.get("rel") == "canonical"
               and attrs.get("href") == "https://a11oy.net/oac/" for tag, attrs in elements)
    stylesheet = [attrs["href"] for tag, attrs in elements
                  if tag == "link" and attrs.get("rel") == "stylesheet"]
    assert stylesheet == [
        "/assets/szl/szl-tokens.css",
        "/assets/kanchay.css", "/assets/szl-flow-proof.css",
        "/assets/szl-flow-proof-static.css", "/assets/szl-holo-proof-v2.css",
    ]
    assert all((ROOT / asset.lstrip("/")).is_file() for asset in stylesheet)
    anchors = [attrs["href"] for tag, attrs in elements if tag == "a"]
    for ref in anchors:
        parsed = urlparse(ref)
        assert parsed.scheme in {"", "https"}
        if not parsed.scheme and parsed.path:
            target = ROOT / parsed.path.lstrip("/") if ref.startswith("/") else OAC / parsed.path
            assert target.is_file() or (target / "index.html").is_file(), ref
    for label in ("RECORD", "REPORTED", "UNKNOWN", "DECLARED", "SIMULATED",
                  "current state by this page", "synthetic numeric telemetry", "not clinical",
                  "not device control", "No new training", "mutable demo"):
        assert label in source
    for identity in (SOURCE, HUB, MODEL, DATASET, ARTIFACT, V2_SOURCE,
                     V2_CARD_SOURCE, V2_INITIAL_HUB, V2_HUB, V2_APPLICATION,
                     V2_SPACE, "36966679696", "11209469462", "37726459882",
                     V2_WITNESS_RUN):
        assert identity in source
    assert "unsigned receipt records file digests" in source
    assert "does not authenticate that origin" in source
    assert 'href="v2-artifact.json"' in source
    assert "four immutable Git artifact matches" in source
    assert "does not establish a-11-oy.com product readiness" in source
    assert "does not probe current provider state" in source
    assert 'href="https://szlholdings-oac-system-health-lab.hf.space/#v2-panel"' in source
    assert 'href="https://szlholdings-oac-system-health-lab.hf.space/api/v2/identity"' in source
    assert 'href="https://szlholdings-oac-system-health-lab.hf.space/api/v2/readyz"' in source
    assert 'href="#main"' in source
    assert 'id="main"' in source
    assert "min-height:44px" in source
    assert "focus-visible" in source
    assert "prefers-reduced-motion" in source
    csp = next(attrs["content"] for tag, attrs in elements if tag == "meta"
               and attrs.get("http-equiv") == "Content-Security-Policy")
    for directive in ("script-src 'none'", "connect-src 'none'", "frame-src 'none'",
                      "form-action 'none'", "object-src 'none'"):
        assert directive in csp


def test_oac_static_catalog_admission_is_not_provider_evidence():
    source = (OAC / "index.html").read_text(encoding="utf-8")
    for marker in (
        'data-szl-proof-flow-asset="style"',
        'data-szl-proof-flow-asset="static-style"',
        'data-szl-proof-flow-asset="static"',
        'data-szl-proof-holo-asset="style-v2"',
        'data-szl-proof-holo-adopted="true"',
        'data-szl-proof-flow="record"',
        'data-szl-proof-theme="forensic"',
    ):
        assert source.count(marker) == 1, marker
    assert "ROLLED_OUT presentation catalogs describe source-tree bindings" in source
    assert "not new provider publication or readiness" in source
    flow = json.loads((ROOT / "frontend-flow-shell-state.json").read_bytes())
    holographic = json.loads((ROOT / "holographic-experience-v2/rollout-state.json").read_bytes())
    assert flow["state"] == holographic["state"] == "ROLLED_OUT"
    assert flow["examined_documents"] == 46
    assert flow["injected_documents"].count("oac/index.html") == 1
    assert flow["zero_javascript_documents"].count("oac/index.html") == 1
    assert holographic["examined_documents"] == 48
    assert holographic["bound_documents"] == 46
    assert holographic["bindings"].count("oac/index.html") == 1
    assert holographic["zero_javascript_documents"].count("oac/index.html") == 1
    assert "oac/index.html" not in holographic["interactive_documents"]
    assert "oac/index.html" not in holographic["opt_out_documents"]
    record = json.loads((OAC / "release.json").read_bytes())
    assert record["currentness"] == "NOT_PROBED_BY_STATIC_PAGE"
    assert record["provider_live_verification"] is False


if __name__ == "__main__":
    test_oac_release_is_exact_handoff_not_current_probe()
    test_oac_v2_artifact_is_separate_declared_and_non_authoritative()
    test_oac_html_keeps_identity_scope_and_local_navigation()
    test_oac_static_catalog_admission_is_not_provider_evidence()
    print("OK: OAC static release contract; current provider state remains NOT_PROBED by this page.")
