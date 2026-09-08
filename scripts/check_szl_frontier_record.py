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

EXPECTED_SOURCE = "0640258ccd63f40605a1811287322e99038836da"
EXPECTED_PREVIOUS = "3590daaadce2d2b07950ba844afe8bd6d870fb12"
EXPECTED_HF_REPO = "e71a9b32159e3964b8ed06ddb0603fe90a8d7f23"
EXPECTED_RUNTIME_SHA = "0af84df5d380f4bd19bd5a14b24fb87520955dd020f87d064d45af9d89516033"
EXPECTED_HF_SYNC_RUN = 34247345227
EXPECTED_HF_SYNC_JOB = 102132616561
EXPECTED_HF_WITNESS = "6aa06d28900620b5c77e3a5c"
EXPECTED_PRODUCT_SOURCE = "002cd0c2edc8f38b297ae0394ecf8da12c06cc60"
EXPECTED_PRODUCT_SUMMARY_SHA = "237cd3a48866bb8c26ed40cef2800d18223058abc7d16bbbc337f9180ecd6091"
EXPECTED_PRODUCT_MANIFEST = "2d874a8a07e533f35c82dfeb8f83933849ca45b919e275d8f9e41a189a08b40e"
EXPECTED_PRODUCT_WITNESS = "6aa06d28900620b5c77e3a5c"
EXPECTED_PRODUCT_SYNC_RUN = 34243871980
EXPECTED_PRODUCT_DEPLOY_JOB = 102120707626
EXPECTED_PRODUCT_READINESS_JOB = 102125540417
EXPECTED_PRODUCT_RELOCK_JOB = 102125773063
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
    assert product["runtimeReportedSourceRevision"] == EXPECTED_PRODUCT_SOURCE
    assert product["githubDefaultBranchRevision"] == EXPECTED_PRODUCT_SOURCE
    assert SHA40.fullmatch(EXPECTED_PRODUCT_SOURCE)
    assert product["sourceRuntimeParity"] == "MATCH"
    assert product["huggingFaceRepositoryRevision"] is None
    assert product["runtimeArtifactDigest"] is None
    assert product["equivalenceState"] == "UNAVAILABLE"
    assert product["equivalenceReason"] == "GITHUB_MAIN_MATCHES_RUNTIME_HF_OVERLAY_AND_ARTIFACT_DIGEST_UNAVAILABLE"
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
    assert product["canonicalSyncWorkflowRun"] == EXPECTED_PRODUCT_SYNC_RUN
    assert product["canonicalDeployJob"] == EXPECTED_PRODUCT_DEPLOY_JOB
    assert product["canonicalReadinessJob"] == EXPECTED_PRODUCT_READINESS_JOB
    assert product["canonicalRelockJob"] == EXPECTED_PRODUCT_RELOCK_JOB
    assert product["canonicalSyncConclusion"] == "PARTIAL_FAILURE_VERTICAL_FLAGSHIP_PUBLISH_ONLY"
    assert "earlier source drift is repaired" in product["note"]
    assert "Complete equivalence remains unavailable" in product["note"]

    proof = record["proof"]
    assert proof["origin"] == "https://a11oy.net"
    assert proof["ownerRepository"] == "szl-holdings/a11oy-net"
    assert proof["previousSourceRevision"] == EXPECTED_PREVIOUS
    assert proof["state"] == "CURRENT_FRONTIER_SOURCE_HF_EXACT_PRODUCT_SOURCE_MATCH_BINDING_UNAVAILABLE_RECORDED"

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
        "state": "SOURCE_HF_EXACT_PRODUCT_SOURCE_MATCH_BINDING_UNAVAILABLE_FAILED_CLOSED",
        "productionDisposition": "HOLD",
        "automaticPromotion": False,
    }

    page = PAGE.read_text(encoding="utf-8")
    for expected in (
        EXPECTED_SOURCE, EXPECTED_PREVIOUS, EXPECTED_HF_REPO, EXPECTED_RUNTIME_SHA,
        EXPECTED_PRODUCT_SOURCE, EXPECTED_PRODUCT_SUMMARY_SHA, EXPECTED_RECEIPT_SHA,
    ):
        assert expected in page
    assert f"actions/runs/{EXPECTED_HF_SYNC_RUN}" in page
    assert f"actions/runs/{EXPECTED_PRODUCT_SYNC_RUN}" in page
    assert 'href="./alignment.json"' in page
    for marker in (
        "OBSERVE_ONLY", "BLOCKED", "MATCH", "UNAVAILABLE", "FAILED_CLOSED",
        "github_inventory_unavailable", "writes <code>DISABLED</code>", "HOLD", "promotion NONE",
    ):
        assert marker in page
    assert "No ATO" in page
    assert "Λ remains Conjecture 1" in page
    assert "Docker operational" not in page

    print(
        "OK: Frontier GitHub/HF is exact, A11oy source/runtime parity is repaired while "
        "complete binding remains unavailable and fail-closed, and production remains HOLD."
    )


if __name__ == "__main__":
    check()
