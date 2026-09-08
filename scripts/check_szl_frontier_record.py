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

EXPECTED_SOURCE = "1bdad0f8a510afe24db6eb03fb8479e7f8330c6d"
EXPECTED_PREVIOUS = "9a4ed6f"
EXPECTED_HF_SYNC_RUN = 34178621960
EXPECTED_RECEIPT_SHA = "bdf6a0aac1af5b06f10ad0e7a9ee9d29e43d16b92654887f0c0b34f25071db46"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def check() -> None:
    assert PAGE.is_file(), "frontier proof page is required"
    assert RECORD.is_file(), "machine-readable frontier alignment record is required"

    record = json.loads(RECORD.read_text(encoding="utf-8"))
    assert record["schema"] == "szl.proof.frontier-alignment.v1"
    assert record["authorityChain"] == [
        "GitHub",
        "Hugging Face",
        "a-11-oy.com",
        "a11oy.net",
    ]

    source = record["source"]
    assert source["repository"] == "szl-holdings/szl-frontier"
    assert SHA40.fullmatch(source["revision"])
    assert source["revision"] == EXPECTED_SOURCE
    assert source["state"] == "EXACT"

    hub = record["huggingFace"]
    assert hub["space"] == "SZLHOLDINGS/szl-frontier"
    assert hub["expectedSourceRevision"] == EXPECTED_SOURCE
    assert hub["syncWorkflowRun"] == EXPECTED_HF_SYNC_RUN
    assert hub["witness"] == "PASS"

    product = record["product"]
    assert product["origin"] == "https://a-11-oy.com"
    assert product["state"] == "NOT_WITNESSED_BY_THIS_RECORD"
    assert product["promotionEffect"] == "NONE"

    proof = record["proof"]
    assert proof["origin"] == "https://a11oy.net"
    assert proof["ownerRepository"] == "szl-holdings/a11oy-net"
    assert proof["previousSourceRevision"] == EXPECTED_PREVIOUS
    assert proof["state"] == "SOURCE_AND_HF_ALIGNMENT_REPAIRED_IN_RECORD"

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
    assert SHA256.fullmatch(measured["receiptSha256"])
    assert measured["receiptSha256"] == EXPECTED_RECEIPT_SHA
    assert len(measured["limitations"]) >= 5

    overall = record["overall"]
    assert overall["state"] == "PARTIAL_ALIGNMENT_PRODUCT_NOT_WITNESSED"
    assert overall["productionDisposition"] == "HOLD"
    assert overall["automaticPromotion"] is False

    page = PAGE.read_text(encoding="utf-8")
    assert EXPECTED_SOURCE in page
    assert f"runs/{EXPECTED_HF_SYNC_RUN}" in page
    assert 'href="./alignment.json"' in page
    assert EXPECTED_RECEIPT_SHA in page
    assert "NOT WITNESSED BY THIS RECORD" in page
    assert "HOLD" in page
    assert "promotion NONE" in page
    assert "RUNNING</td>" not in page
    assert "Docker operational" not in page
    assert "main <code>9a4ed6f</code>" not in page
    assert "No ATO" in page
    assert "Λ remains Conjecture 1" in page

    print(
        "OK: SZL Frontier proof record is source/HF aligned, "
        "product state is not inferred, and production remains HOLD."
    )


if __name__ == "__main__":
    check()
