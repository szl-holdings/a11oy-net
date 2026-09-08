#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed contract for the source-bound SZL Frontier proof record."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "estate" / "szl-frontier" / "index.html"
RECORD = ROOT / "estate" / "szl-frontier" / "alignment.json"

EXPECTED_SOURCE = "3ee8d770f73306307b91359f3bfea39451e2efb2"
EXPECTED_PREVIOUS = "979a8074772d11ab5c8d34d5c942577e1bee9eb6"
EXPECTED_HF_REPO = "66d14801b8950b8da5cfa15ad33adf3ed4c4d9fe"
EXPECTED_RUNTIME_SHA = "cd43c9a18e4780691c770119a60ca93836b557d0c327c5aacfe7fd6b10f718a8"
EXPECTED_HF_SYNC_RUN = 34219011040
EXPECTED_HF_SYNC_JOB = 102037461401
EXPECTED_PRODUCT_RUNTIME = "573992a648a3d3ddb48470654841a89b1739d3e7"
EXPECTED_PRODUCT_SUMMARY_SHA = "f0d20dd31c406166c8f84d48976cbfb26131228b68f854fc5b5c52056328362e"
EXPECTED_PRODUCT_MANIFEST = "2f27e71c0aaa1edc96f0b0c1dffac9019603b412ca45cb54dd33e3899bbad55b"
EXPECTED_RECEIPT_SHA = "bdf6a0aac1af5b06f10ad0e7a9ee9d29e43d16b92654887f0c0b34f25071db46"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _instant(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def check() -> None:
    assert PAGE.is_file(), "frontier proof page is required"
    assert RECORD.is_file(), "machine-readable frontier alignment record is required"

    record = json.loads(RECORD.read_text(encoding="utf-8"))
    assert record["schema"] == "szl.proof.frontier-alignment.v1"
    assert record["authorityChain"] == ["GitHub", "Hugging Face", "a-11-oy.com", "a11oy.net"]

    source = record["source"]
    assert source["repository"] == "szl-holdings/szl-frontier"
    assert source["revision"] == EXPECTED_SOURCE and SHA40.fullmatch(source["revision"])
    assert source["previousRevision"] == EXPECTED_PREVIOUS
    assert source["state"] == "EXACT_AT_OBSERVATION"

    hub = record["huggingFace"]
    assert hub["space"] == "SZLHOLDINGS/szl-frontier"
    assert hub["spaceRepositoryRevision"] == EXPECTED_HF_REPO
    assert SHA40.fullmatch(hub["spaceRepositoryRevision"])
    assert hub["runtimeDeploymentSourceRevision"] == EXPECTED_SOURCE
    assert hub["runtimeDeploymentSha256"] == EXPECTED_RUNTIME_SHA
    assert SHA256.fullmatch(hub["runtimeDeploymentSha256"])
    assert hub["runtimeStage"] == "RUNNING"
    assert hub["syncWorkflowRun"] == EXPECTED_HF_SYNC_RUN
    assert hub["syncWorkflowJob"] == EXPECTED_HF_SYNC_JOB
    assert hub["independentWitnessJob"] == "6a9fef518e5f7b7fd14cb9f9"
    assert hub["witness"] == "PASS"
    assert "not for a model" in hub["evidence"]

    product = record["product"]
    assert product["origin"] == "https://a-11-oy.com"
    assert product["summarySchema"] == "szl.frontier-now-summary/v1"
    assert product["summarySha256"] == EXPECTED_PRODUCT_SUMMARY_SHA
    assert SHA256.fullmatch(product["summarySha256"])
    assert product["manifestDigest"] == EXPECTED_PRODUCT_MANIFEST
    assert SHA256.fullmatch(product["manifestDigest"])
    assert _instant(product["generatedAt"]) >= _instant(product["observedAt"])
    assert _instant(product["validUntil"]) > _instant(product["observedAt"])
    assert product["operatingMode"] == "OBSERVE_ONLY"
    assert product["observationState"] == "BLOCKED"
    assert product["runtimeReportedSourceRevision"] == EXPECTED_PRODUCT_RUNTIME
    assert product["githubDefaultBranchRevision"] == EXPECTED_PRODUCT_RUNTIME
    assert SHA40.fullmatch(product["runtimeReportedSourceRevision"])
    assert product["runtimeReportedSourceRevision"] != EXPECTED_SOURCE
    assert product["huggingFaceRepositoryRevision"] is None
    assert product["runtimeArtifactDigest"] is None
    assert product["equivalenceState"] == "UNAVAILABLE"
    assert product["equivalenceReason"] == "GITHUB_MAIN_MATCHES_RUNTIME_HF_OVERLAY_AND_ARTIFACT_DIGEST_UNAVAILABLE"
    assert product["claimGate"] == "FAILED_CLOSED"
    assert product["claimGateReason"] == "EXACT_SOURCE_RUNTIME_BINDING_UNAVAILABLE"
    assert product["criticalFailures"] == ["github_inventory_unavailable"]
    assert product["externalWrites"] == "DISABLED"
    assert product["automaticRetries"] == 0
    assert product["effectors"] == []
    assert product["promotionEffect"] == "NONE"
    assert product["independentWitnessJob"] == "6a9fef85b012ba1d5b8f2a77"
    assert "not the szl-frontier source revision" in product["note"]

    proof = record["proof"]
    assert proof["origin"] == "https://a11oy.net"
    assert proof["ownerRepository"] == "szl-holdings/a11oy-net"
    assert proof["previousSourceRevision"] == EXPECTED_PREVIOUS
    assert proof["state"] == "CURRENT_FRONTIER_SOURCE_AND_HF_RUNTIME_RECORDED"

    measured = record["measuredEvidence"]["glm53FlashVsKhipu"]
    assert measured["decision"] == "EVIDENCE_COMPLETE_REVIEW_REQUIRED"
    assert measured["productionDisposition"] == "HOLD"
    assert measured["promotionEffect"] == "NONE"
    assert measured["candidateScore"] == 0.916667
    assert measured["baselineScore"] == 0.416667
    assert measured["scoreDelta"] == 0.5
    assert measured["candidateSchemaValidRate"] == 1.0
    assert measured["baselineSchemaValidRate"] == 0.5
    assert measured["candidateBaselineMeanLatencyRatio"] == 0.303195
    assert measured["receiptSha256"] == EXPECTED_RECEIPT_SHA
    assert SHA256.fullmatch(measured["receiptSha256"])
    assert len(measured["limitations"]) >= 5

    overall = record["overall"]
    assert overall["state"] == "SOURCE_HF_EXACT_PRODUCT_EQUIVALENCE_UNAVAILABLE"
    assert overall["productionDisposition"] == "HOLD"
    assert overall["automaticPromotion"] is False

    page = PAGE.read_text(encoding="utf-8")
    for expected in (
        EXPECTED_SOURCE,
        EXPECTED_PREVIOUS,
        EXPECTED_HF_REPO,
        EXPECTED_RUNTIME_SHA,
        EXPECTED_PRODUCT_RUNTIME,
        EXPECTED_PRODUCT_SUMMARY_SHA,
        EXPECTED_RECEIPT_SHA,
    ):
        assert expected in page
    assert f"actions/runs/{EXPECTED_HF_SYNC_RUN}" in page
    assert 'href="./alignment.json"' in page
    assert "OBSERVE_ONLY" in page
    assert "BLOCKED" in page
    assert "FAILED_CLOSED" in page
    assert "github_inventory_unavailable" in page
    assert "writes DISABLED" in page
    assert "HOLD" in page
    assert "promotion NONE" in page
    assert "Docker operational" not in page
    assert "No ATO" in page
    assert "Λ remains Conjecture 1" in page

    print(
        "OK: SZL Frontier GitHub/HF source is exact at observation, "
        "A11oy product identity is separately bound and fail-closed, "
        "and production remains HOLD."
    )


if __name__ == "__main__":
    check()
