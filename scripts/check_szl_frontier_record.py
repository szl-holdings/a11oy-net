#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed contract for the source-bound SZL Frontier proof record."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "estate" / "szl-frontier" / "index.html"
RECORD = ROOT / "estate" / "szl-frontier" / "alignment.json"

EXPECTED_SOURCE = "979a8074772d11ab5c8d34d5c942577e1bee9eb6"
EXPECTED_PREVIOUS = "1bdad0f8a510afe24db6eb03fb8479e7f8330c6d"
EXPECTED_RUNTIME_SHA = "54be4a3150b6f701a66fc9996cfbf6feb973d25a8d28abf54f1be07e21173a18"
EXPECTED_RECEIPT_SHA = "bdf6a0aac1af5b06f10ad0e7a9ee9d29e43d16b92654887f0c0b34f25071db46"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


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
    assert hub["runtimeDeploymentSourceRevision"] == EXPECTED_SOURCE
    assert hub["runtimeDeploymentSha256"] == EXPECTED_RUNTIME_SHA
    assert SHA256.fullmatch(hub["runtimeDeploymentSha256"])
    assert hub["runtimeStage"] == "RUNNING"
    assert hub["witness"] == "PASS"

    product = record["product"]
    assert product["origin"] == "https://a-11-oy.com"
    assert product["operatingMode"] == "OBSERVE_ONLY"
    assert product["equivalenceState"] == "UNAVAILABLE"
    assert product["claimGate"] == "FAILED_CLOSED"
    assert product["criticalFailures"] == ["github_inventory_unavailable"]
    assert product["promotionEffect"] == "NONE"

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
    assert EXPECTED_SOURCE in page
    assert EXPECTED_PREVIOUS in page
    assert EXPECTED_RUNTIME_SHA in page
    assert 'href="./alignment.json"' in page
    assert EXPECTED_RECEIPT_SHA in page
    assert "OBSERVE_ONLY" in page
    assert "FAILED_CLOSED" in page
    assert "github_inventory_unavailable" in page
    assert "HOLD" in page
    assert "promotion NONE" in page
    assert "Docker operational" not in page
    assert "No ATO" in page
    assert "Λ remains Conjecture 1" in page

    print(
        "OK: SZL Frontier GitHub/HF source is exact at observation, "
        "product equivalence remains unavailable/fail-closed, and production is HOLD."
    )


if __name__ == "__main__":
    check()
