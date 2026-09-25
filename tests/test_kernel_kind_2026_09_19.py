#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "estate" / "kernel-kind-2026-09-19T22-46Z.json"
PRIOR = ROOT / "estate" / "kernel-kind-2026-09-11T23-20Z.json"

CANDIDATES = {
    "SZLHOLDINGS/szl-maskmod",
    "SZLHOLDINGS/szl-block-kv",
    "SZLHOLDINGS/szl-receipt-attn",
    "SZLHOLDINGS/YARQA-ATTN",
}


def test_overdue_record_stays_hold() -> None:
    payload = json.loads(DOC.read_text(encoding="utf-8"))
    assert payload["schema"] == "szl.kernel-kind-observation/v1"
    assert payload["disposition"] == "HOLD"
    assert payload["cutoff_status"] == "OVERDUE"
    assert payload["production_authorization"] is False
    assert payload["automatic_promotion_authorized"] is False
    assert payload["certified_production_ready"] is False
    assert payload["runtime_loaded"] is False
    assert payload["mirrors_deleted"] is False
    assert payload["empty_v1_branch_created"] is False
    assert payload["revision_binding"]["branch_named_v1_count"] == 0
    assert payload["research_candidate"]["production_adoption_requested"] is False


def test_cutoff_is_in_the_past() -> None:
    payload = json.loads(DOC.read_text(encoding="utf-8"))
    cutoff = datetime.fromisoformat(payload["takedown_starts"].replace("Z", "+00:00"))
    observed = datetime.fromisoformat(payload["observed_at"].replace("Z", "+00:00"))
    assert cutoff.tzinfo == timezone.utc
    assert observed > cutoff
    assert payload["days_overdue_at_observation"] >= 6


def test_four_compiled_candidates_still_missing_v1() -> None:
    payload = json.loads(DOC.read_text(encoding="utf-8"))
    rows = payload["revision_binding"]["compiled_candidates_no_v1_branch"]
    ids = {row["id"] for row in rows}
    assert ids == CANDIDATES
    assert all(row["v1"] == "missing" for row in rows)
    assert all(row["main"] and row["main"] != "" for row in rows)


def test_does_not_rewrite_membership_files() -> None:
    payload = json.loads(DOC.read_text(encoding="utf-8"))
    assert "public-membership.json" in payload["does_not_rewrite"]
    assert "public-inventory.json" in payload["does_not_rewrite"]
    assert PRIOR.is_file()
    prior = json.loads(PRIOR.read_text(encoding="utf-8"))
    assert prior["disposition"] == "HOLD"
