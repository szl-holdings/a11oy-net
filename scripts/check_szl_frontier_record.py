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

EXPECTED_SOURCE = "3590daaadce2d2b07950ba844afe8bd6d870fb12"
EXPECTED_PREVIOUS = "3ee8d770f73306307b91359f3bfea39451e2efb2"
EXPECTED_HF_REPO = "e736cc087805c8bbc915aee2dcd94db678095efe"
EXPECTED_RUNTIME_SHA = "5abc1febe85b1c6e9c741e5bacee95f80d52638de001bf2618001fdfd7b61940"
EXPECTED_HF_SYNC_RUN = 34236458955
EXPECTED_HF_SYNC_JOB = 102095318561
EXPECTED_HF_WITNESS = "6aa0177f32d5d0c22c5ad971"
EXPECTED_PRODUCT_RUNTIME = "8d59d6cea71f86605353be91dbda2bfa44fc731d"
EXPECTED_PRODUCT_GITHUB = "c0373bd53aed420bcd22c57dbb5dff585f200f91"
EXPECTED_PRODUCT_SUMMARY_SHA = "fc51c9590bc92c019021b2882374a69ccdc0ac351f6fa9f0050df6f9674efc8e"
EXPECTED_PRODUCT_MANIFEST = "17535f50e15594020fd2bed815e7a8c794fed33cfd49086010ce8fd5619e3394"
EXPECTED_PRODUCT_WITNESS = "6aa0179f900620b5c77e26ad"
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
    assert source == {
        "repository": "szl-holdings/szl-frontier",
        "revision": EXPECTED_SOURCE,
        "previousRevision": EXPECTED_PREVIOUS,
        "state": "EXACT_AT_OBSERVATION",
    }
    assert SHA40.fullmatch(source["revision"])

    hub = record["huggingFace"]
    assert hub["space"] == "SZLHOLDINGS/szl-frontier"
    assert hub["spaceRepositoryRevision"] == EXPECTED_HF_REPO and SHA40.fullmatch(EXPECTED_HF_REPO)
    assert hub["runtimeDeploymentSourceRevision"] == EXPECTED_SOURCE
    assert hub["runtimeDeploymentSha256"] == EXPECTED_RUNTIME_SHA and SHA256.fullmatch(EXPECTED_RUNTIME_SHA)
    assert hub["runtimeStage"] == "RUNNING"
    assert hub["syncWorkflowRun"] == EXPECTED_HF_SYNC_RUN
    assert hub["syncWorkflowJob"] == EXPECTED_HF_SYNC_JOB
    assert hub["independentWitnessJob"] == EXPECTED_HF_WITNESS
    assert hub["witness"] == "PASS"
    assert "not to a model" in hub["evidence"]

    product = record["product"]
    assert product["origin"] == "https://a-11-oy.com"
    assert product["summarySchema"] == "szl.frontier-now-summary/v1"
    assert product["summarySha256"] == EXPECTED_PRODUCT_SUMMARY_SHA and SHA256.fullmatch(EXPECTED_PRODUCT_SUMMARY_SHA)
    assert product["manifestDigest"] == EXPECTED_PRODUCT_MANIFEST and SHA256.fullmatch(EXPECTED_PRODUCT_MANIFEST)
    assert _instant(product["generatedAt"]) >= _instant(product["observedAt"])
    assert _instant(product["validUntil"]) > _instant(product["observedAt"])
    assert product["operatingMode"] == "OBSERVE_ONLY"
    assert product["observationState"] == "BLOCKED"
    assert product["runtimeReportedSourceRevision"] == EXPECTED_PRODUCT_RUNTIME
    assert product["githubDefaultBranchRevision"] == EXPECTED_PRODUCT_GITHUB
    assert SHA40.fullmatch(EXPECTED_PRODUCT_RUNTIME) and SHA40.fullmatch(EXPECTED_PRODUCT_GITHUB)
    assert EXPECTED_PRODUCT_RUNTIME != EXPECTED_PRODUCT_GITHUB
    assert EXPECTED_PRODUCT_RUNTIME != EXPECTED_SOURCE and EXPECTED_PRODUCT_GITHUB != EXPECTED_SOURCE
    assert product["huggingFaceRepositoryRevision"] is None
    assert product["runtimeArtifactDigest"] is None
    assert product["equivalenceState"] == "DRIFT"
    assert product["equivalenceReason"] == "GITHUB_DEFAULT_BRANCH_DRIFTS_FROM_RUNTIME_REPORTED_REVISION"
    assert product["claimGate"] == "FAILED_CLOSED"
    assert product["claimGateReason"] == "EXACT_SOURCE_RUNTIME_BINDING_UNAVAILABLE"
    assert product["publicClaimStatus"] == "HELD"
    assert product["criticalFailures"] == ["github_inventory_unavailable"]
    assert product["enforcementState"] == "FAILED_CLOSED"
    assert product["externalWrites"] == "DISABLED"
    assert product["automaticRetries"] == 0
    assert product["effectors"] == []
    assert product["proofRailState"] == "OBSERVED"
    assert product["lastKnownCounts"] == {
        "state": "BLOCKED", "models": 46, "datasets": 43, "spaces": 26,
        "collections": 21, "buckets": 6, "kernels": 14,
    }
    assert product["independentWitnessJob"] == EXPECTED_PRODUCT_WITNESS
    assert "product itself reports source drift" in product["note"]

    proof = record["proof"]
    assert proof["origin"] == "https://a11oy.net"
    assert proof["ownerRepository"] == "szl-holdings/a11oy-net"
    assert proof["previousSourceRevision"] == EXPECTED_PREVIOUS
    assert proof["state"] == "CURRENT_FRONTIER_SOURCE_HF_EXACT_AND_PRODUCT_DRIFT_RECORDED"

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
    assert measured["receiptSha256"] == EXPECTED_RECEIPT_SHA and SHA256.fullmatch(EXPECTED_RECEIPT_SHA)
    assert len(measured["limitations"]) >= 5

    overall = record["overall"]
    assert overall == {
        "state": "SOURCE_HF_EXACT_PRODUCT_SOURCE_DRIFT_FAILED_CLOSED",
        "productionDisposition": "HOLD",
        "automaticPromotion": False,
    }

    page = PAGE.read_text(encoding="utf-8")
    for expected in (
        EXPECTED_SOURCE, EXPECTED_PREVIOUS, EXPECTED_HF_REPO, EXPECTED_RUNTIME_SHA,
        EXPECTED_PRODUCT_RUNTIME, EXPECTED_PRODUCT_GITHUB, EXPECTED_PRODUCT_SUMMARY_SHA,
        EXPECTED_RECEIPT_SHA,
    ):
        assert expected in page
    assert f"actions/runs/{EXPECTED_HF_SYNC_RUN}" in page
    assert 'href="./alignment.json"' in page
    for marker in ("OBSERVE_ONLY", "BLOCKED", "DRIFT", "FAILED_CLOSED", "github_inventory_unavailable", "writes <code>DISABLED</code>", "HOLD", "promotion NONE"):
        assert marker in page
    assert "No ATO" in page
    assert "Λ remains Conjecture 1" in page
    assert "Docker operational" not in page

    print("OK: Frontier GitHub/HF is exact, A11oy product drift is preserved fail-closed, and production remains HOLD.")


if __name__ == "__main__":
    check()
