#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "estate" / "kernel-sha-binding-2026-09-11T23-52Z.json"
PRIOR = ROOT / "estate" / "kernel-kind-2026-09-11T23-20Z.json"
MEMBERSHIP = ROOT / "public-membership.json"
INVENTORY = ROOT / "public-inventory.json"


def test_sha_binding_is_hold_and_not_production() -> None:
    payload = json.loads(DOC.read_text(encoding="utf-8"))
    assert payload["schema"] == "szl.kernel-sha-binding/v1"
    assert payload["disposition"] == "HOLD"
    assert payload["production_authorization"] is False
    assert payload["automatic_promotion_authorized"] is False
    assert payload["certified_production_ready"] is False
    assert payload["runtime_loaded"] is False
    assert payload["mirrors_deleted"] is False
    assert payload["counts"]["named_v1_branch"] == 0
    assert payload["counts"]["kernel_sha_equals_model_sha"] == 0


def test_does_not_rewrite_prior_kernel_kind_or_inventory() -> None:
    payload = json.loads(DOC.read_text(encoding="utf-8"))
    prior = json.loads(PRIOR.read_text(encoding="utf-8"))
    membership = json.loads(MEMBERSHIP.read_text(encoding="utf-8"))
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    assert "estate/kernel-kind-2026-09-11T23-20Z.json" in payload["does_not_rewrite"]
    assert payload["counts"]["listed"] == prior["kernels_api"]["list_count"] == 14
    assert payload["counts"]["tagged_kernel"] == prior["kernels_api"]["tagged_kernel_count"] == 9
    assert payload["counts"]["listed"] != membership["counts"]["models"]
    assert payload["counts"]["listed"] != inventory["counts"]["models"]


def test_every_row_has_incomparable_kernel_and_model_sha() -> None:
    payload = json.loads(DOC.read_text(encoding="utf-8"))
    rows = payload["repositories"]
    assert len(rows) == 14
    assert all(row["v1_branch"] is False for row in rows)
    assert all(row["kernel_sha"] != row["model_sha"] for row in rows)
    assert all(len(row["kernel_sha"]) == 40 and len(row["model_sha"]) == 40 for row in rows)
