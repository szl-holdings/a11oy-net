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
ESTATE = ROOT / "estate" / "szl-frontier" / "estate-release-train-34297559945.json"

EXPECTED_SOURCE = "0640258ccd63f40605a1811287322e99038836da"
EXPECTED_PREVIOUS = "3590daaadce2d2b07950ba844afe8bd6d870fb12"
EXPECTED_HF_REPO = "e71a9b32159e3964b8ed06ddb0603fe90a8d7f23"
EXPECTED_RUNTIME_SHA = "0af84df5d380f4bd19bd5a14b24fb87520955dd020f87d064d45af9d89516033"
EXPECTED_HF_SYNC_RUN = 34247345227
EXPECTED_HF_SYNC_JOB = 102132616561
EXPECTED_HF_WITNESS = "6aa06d28900620b5c77e3a5c"
HISTORICAL_PRODUCT_SOURCE = "002cd0c2edc8f38b297ae0394ecf8da12c06cc60"
EXPECTED_PRODUCT_SOURCE = "e14af70d8fd24306e449db56450ad01fb524a857"
EXPECTED_PRODUCT_HF_REPO = "8eec9a696e838e6889bd968776d8f0279e188400"
EXPECTED_PRODUCT_SEMANTIC = "7de4d4911c0fcbb556783523a2267422ae0ec4d23a9fef252f799bc9b95e0296"
EXPECTED_PRODUCT_SUMMARY_SHA = "237cd3a48866bb8c26ed40cef2800d18223058abc7d16bbbc337f9180ecd6091"
EXPECTED_PRODUCT_MANIFEST = "2d874a8a07e533f35c82dfeb8f83933849ca45b919e275d8f9e41a189a08b40e"
EXPECTED_ESTATE_RUN = 34297559945
EXPECTED_ESTATE_JOB = 102297362728
EXPECTED_RELEASE_ID = "d1b3d82e190549cefb0d87ce"
EXPECTED_ESTATE_ARTIFACT = "b5eed8c12736c1e28a076f5e73f48f51483703246251205f62b6a2976cc182f6"
EXPECTED_ESTATE_PROOF_CHAIN = "b24aeefb2e6f92b93c027b85357f92ced2d3af28049a423ae1dc612f30c86fb5"
EXPECTED_LYTE_SOURCE = "72560fd5eb68cab08c40565c3c489e42c8442e72"
EXPECTED_LYTE_RUNTIME = "a6a653b0d93a0d150b868a044642ce4f5c71d766"
EXPECTED_LYTE_HF_REPO = "1ff1d239257a0166d784fef358b8a784f9309481"
EXPECTED_RECEIPT_SHA = "bdf6a0aac1af5b06f10ad0e7a9ee9d29e43d16b92654887f0c0b34f25071db46"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _instant(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def check() -> None:
    assert PAGE.is_file(), "frontier proof page is required"
    assert RECORD.is_file(), "machine-readable frontier alignment record is required"
    assert ESTATE.is_file(), "latest immutable estate observation is required"
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    estate = json.loads(ESTATE.read_text(encoding="utf-8"))
    assert record["schema"] == "szl.proof.frontier-alignment.v1"
    assert estate["schema"] == "szl.proof.frontier-estate-release-observation.v1"
    assert record["authorityChain"] == ["GitHub", "Hugging Face", "a-11-oy.com", "a11oy.net"]
    assert estate["authorityChain"] == record["authorityChain"]

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

    historical = record["product"]
    assert historical["witnessScope"] == "HISTORICAL_FRONTIER_NOW_SUMMARY"
    assert historical["supersededByEstateObservation"] == EXPECTED_ESTATE_RUN
    assert historical["summarySchema"] == "szl.frontier-now-summary/v1"
    assert historical["summarySha256"] == EXPECTED_PRODUCT_SUMMARY_SHA and SHA256.fullmatch(EXPECTED_PRODUCT_SUMMARY_SHA)
    assert historical["manifestDigest"] == EXPECTED_PRODUCT_MANIFEST and SHA256.fullmatch(EXPECTED_PRODUCT_MANIFEST)
    assert _instant(historical["generatedAt"]) >= _instant(historical["observedAt"])
    assert _instant(historical["validUntil"]) > _instant(historical["observedAt"])
    assert historical["runtimeReportedSourceRevision"] == HISTORICAL_PRODUCT_SOURCE
    assert historical["githubDefaultBranchRevision"] == HISTORICAL_PRODUCT_SOURCE
    assert historical["equivalenceState"] == "UNAVAILABLE"
    assert historical["claimGate"] == "FAILED_CLOSED"
    assert historical["publicClaimStatus"] == "HELD"
    assert historical["externalWrites"] == "DISABLED"
    assert historical["effectors"] == []
    assert "preserved historical" in historical["note"]
    assert "no longer described as the current product source" in historical["note"]

    current = record["latestEstateObservation"]
    assert current["record"] == "./estate-release-train-34297559945.json"
    assert current["sourceRevision"] == EXPECTED_PRODUCT_SOURCE
    assert current["huggingFaceSpaceRepositoryRevision"] == EXPECTED_PRODUCT_HF_REPO
    assert current["huggingFaceRuntimeSourceRevision"] == EXPECTED_PRODUCT_SOURCE
    assert current["domainRuntimeSourceRevision"] == EXPECTED_PRODUCT_SOURCE
    assert current["sourceRuntimeParity"] == "MATCH"
    assert current["semanticParity"] == "MATCH"
    assert current["semanticSha256"] == EXPECTED_PRODUCT_SEMANTIC and SHA256.fullmatch(EXPECTED_PRODUCT_SEMANTIC)
    assert current["artifactBinding"] == "NOT_REOBSERVED_BY_THIS_VERIFIER"
    assert current["run"] == EXPECTED_ESTATE_RUN
    assert current["job"] == EXPECTED_ESTATE_JOB
    assert current["releaseId"] == EXPECTED_RELEASE_ID
    assert current["actionsArtifactSha256"] == EXPECTED_ESTATE_ARTIFACT and SHA256.fullmatch(EXPECTED_ESTATE_ARTIFACT)
    assert current["proofChainSha256"] == EXPECTED_ESTATE_PROOF_CHAIN and SHA256.fullmatch(EXPECTED_ESTATE_PROOF_CHAIN)
    assert current["providerWritesPerformed"] is False
    assert current["blockers"] == [
        "HF_INVENTORY_COUNT_MISMATCH_OR_UNAVAILABLE",
        "lyte:SOURCE_REVISION_MISMATCH",
    ]
    assert current["inventory"] == {
        "declared": {"models": 45, "datasets": 34, "spaces": 17},
        "observed": {"models": 46, "datasets": 35, "spaces": 21},
        "state": "MISMATCH",
    }
    assert current["lyte"] == {
        "canonicalSourceRevision": EXPECTED_LYTE_SOURCE,
        "huggingFaceSpaceRepositoryRevision": EXPECTED_LYTE_HF_REPO,
        "runtimeSourceRevision": EXPECTED_LYTE_RUNTIME,
        "state": "SOURCE_REVISION_MISMATCH",
    }

    assert estate["product"]["sourceRevision"] == EXPECTED_PRODUCT_SOURCE
    assert estate["product"]["huggingFaceRuntimeSourceRevision"] == EXPECTED_PRODUCT_SOURCE
    assert estate["product"]["domainRuntimeSourceRevision"] == EXPECTED_PRODUCT_SOURCE
    assert estate["product"]["semanticParity"] == "MATCH"
    assert estate["product"]["artifactBinding"] == "NOT_REOBSERVED_BY_THIS_VERIFIER"
    assert estate["huggingFaceInventory"]["state"] == "MISMATCH"
    assert estate["lyte"]["state"] == "SOURCE_REVISION_MISMATCH"
    assert estate["estateReleaseTrain"]["run"] == EXPECTED_ESTATE_RUN
    assert estate["estateReleaseTrain"]["actionsArtifactSha256"] == EXPECTED_ESTATE_ARTIFACT
    assert estate["estateReleaseTrain"]["providerWritesPerformed"] is False
    assert estate["productionDisposition"] == "HOLD"
    assert estate["automaticPromotion"] is False

    proof = record["proof"]
    assert proof["state"] == "CURRENT_FRONTIER_SOURCE_HF_EXACT_LATEST_PRODUCT_ESTATE_OBSERVATION_RECORDED_SUMMARY_BINDING_HISTORICAL"

    measured = record["measuredEvidence"]["glm53FlashVsKhipu"]
    assert measured["decision"] == "EVIDENCE_COMPLETE_REVIEW_REQUIRED"
    assert measured["productionDisposition"] == "HOLD"
    assert measured["promotionEffect"] == "NONE"
    assert measured["candidateScore"] == 0.916667
    assert measured["baselineScore"] == 0.416667
    assert measured["receiptSha256"] == EXPECTED_RECEIPT_SHA and SHA256.fullmatch(EXPECTED_RECEIPT_SHA)

    overall = record["overall"]
    assert overall == {
        "state": "SOURCE_HF_EXACT_PRODUCT_ESTATE_PARITY_MATCH_PROOF_ADVANCED_ESTATE_BLOCKERS_HOLD",
        "productionDisposition": "HOLD",
        "automaticPromotion": False,
    }

    page = PAGE.read_text(encoding="utf-8")
    for expected in (
        EXPECTED_SOURCE, EXPECTED_PREVIOUS, EXPECTED_HF_REPO, EXPECTED_RUNTIME_SHA,
        HISTORICAL_PRODUCT_SOURCE, EXPECTED_PRODUCT_SOURCE, EXPECTED_PRODUCT_HF_REPO,
        EXPECTED_PRODUCT_SEMANTIC, EXPECTED_PRODUCT_SUMMARY_SHA, EXPECTED_ESTATE_ARTIFACT,
        EXPECTED_ESTATE_PROOF_CHAIN, EXPECTED_LYTE_SOURCE, EXPECTED_LYTE_RUNTIME,
        EXPECTED_RECEIPT_SHA,
    ):
        assert expected in page
    assert f"actions/runs/{EXPECTED_HF_SYNC_RUN}" in page
    assert f"actions/runs/{EXPECTED_ESTATE_RUN}" in page
    assert 'href="./alignment.json"' in page
    assert 'href="./estate-release-train-34297559945.json"' in page
    for marker in (
        "HISTORICAL", "MATCH", "DIVERGENT", "MISMATCH", "SOURCE_REVISION_MISMATCH",
        "NOT_REOBSERVED_BY_THIS_VERIFIER", "HOLD", "promotion NONE",
    ):
        assert marker in page
    assert "No ATO" in page
    assert "Λ remains Conjecture 1" in page
    assert "Docker operational" not in page

    print(
        "OK: Frontier GitHub/HF remains exact; current A11oy estate source/runtime and semantic parity "
        "is recorded separately from the historical Frontier-now summary witness; active estate blockers "
        "remain fail-closed and production remains HOLD."
    )


if __name__ == "__main__":
    check()
