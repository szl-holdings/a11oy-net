#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "estate" / "kernel-kind-2026-09-11T23-20Z.json"
MEMBERSHIP = ROOT / "public-membership.json"
INVENTORY = ROOT / "public-inventory.json"


def test_kernel_kind_is_hold_and_not_production() -> None:
    payload = json.loads(DOC.read_text(encoding="utf-8"))
    assert payload["schema"] == "szl.kernel-kind-observation/v1"
    assert payload["disposition"] == "HOLD"
    assert payload["production_authorization"] is False
    assert payload["automatic_promotion_authorized"] is False
    assert payload["certified_production_ready"] is False
    assert payload["runtime_loaded"] is False
    assert payload["mirrors_deleted"] is False
    assert payload["revision_binding"]["branch_named_v1_count"] == 0


def test_kernel_counts_are_not_membership_or_inventory() -> None:
    payload = json.loads(DOC.read_text(encoding="utf-8"))
    membership = json.loads(MEMBERSHIP.read_text(encoding="utf-8"))
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    assert payload["kernels_api"]["list_count"] == 14
    assert payload["kernels_api"]["tagged_kernel_count"] == 9
    assert len(payload["kernels_api"]["listed"]) == 14
    assert payload["kernels_api"]["list_count"] != membership["counts"]["models"]
    assert payload["kernels_api"]["tagged_kernel_count"] != membership["counts"]["models"]
    assert payload["kernels_api"]["list_count"] != inventory["counts"]["models"]
    assert payload["scope"]["comparable_to"] == []


def test_missing_v1_branch_is_complete() -> None:
    payload = json.loads(DOC.read_text(encoding="utf-8"))
    missing = {row["id"] for row in payload["revision_binding"]["no_v1_branch_and_no_v1_tag"]}
    assert "SZLHOLDINGS/szl-maskmod" in missing
    assert "SZLHOLDINGS/szl-block-kv" in missing
    assert "SZLHOLDINGS/szl-receipt-attn" in missing
    assert "SZLHOLDINGS/YARQA-ATTN" in missing
    assert "SZLHOLDINGS/szl-formulas" in missing
    assert len(missing) == 7
    assert len(payload["revision_binding"]["tag_v1_0_0_only_no_branch_v1"]) == 7
    assert "SZLHOLDINGS/szl-khipu-kernels" in payload["model_search_kernel_hits"]["model_search_only_not_in_kernels_api"]
