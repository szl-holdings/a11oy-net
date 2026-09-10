from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CURRENT = json.loads((ROOT / "public-membership.json").read_text(encoding="utf-8"))
HISTORICAL = json.loads((ROOT / "public-inventory.json").read_text(encoding="utf-8"))


def test_current_public_membership_is_exact_source_bound() -> None:
    assert CURRENT["schema"] == "szl.public-profile-inventory/v1"
    assert CURRENT["scope"]["id"] == "hf-public-author-membership/v1"
    assert CURRENT["scope"]["authentication"] == "none"
    assert CURRENT["scope"]["visibility"] == "public-only"
    assert CURRENT["counts"] == {"datasets": 35, "models": 46, "spaces": 21}
    assert CURRENT["observed_at"] == "2026-09-10T03:20:41Z"
    assert CURRENT["source_repository"] == "szl-holdings/a11oy"
    assert CURRENT["source_revision"] == "4c6621b17ba452d5af7aa2460462fdfbe513509f"
    assert CURRENT["source_sha256"] == "04dc30206d499f004fe8151cfdf63700c380db29c2afc3d97d2a213303421ca2"
    assert CURRENT["scope_sha256"] == "9060fa8d7edcd5c246b86bcfcf1916df44b18038253325336f2f46208f8001ae"
    assert CURRENT["evidence"]["workflow_run"] == 34432937958
    assert CURRENT["evidence"]["artifact"] == 10135145952
    assert CURRENT["production_authorization"] is False
    assert CURRENT["runtime_readiness_inferred"] is False
    assert CURRENT["model_quality_inferred"] is False


def test_detailed_august_snapshot_remains_historical_not_relabelled() -> None:
    assert HISTORICAL["schema"] == "szl.public-hf-inventory/v3"
    assert HISTORICAL["observed_at"] == "2026-08-31T18:59:11Z"
    assert HISTORICAL["observation_mode"] == "UNAUTHENTICATED_PUBLIC_API_SNAPSHOT"
    assert HISTORICAL["counts"]["models"] == 44
    assert HISTORICAL["counts"]["datasets"] == 30
    assert HISTORICAL["counts"]["spaces"] == 48
    assert HISTORICAL["observed_at"] != CURRENT["observed_at"]
    assert HISTORICAL["counts"]["models"] != CURRENT["counts"]["models"]


def test_membership_scope_does_not_claim_collections_or_buckets() -> None:
    assert CURRENT["scope"]["collections_and_buckets"] == "outside-repository-membership-scope"
    assert "collections" not in CURRENT["counts"]
    assert "buckets" not in CURRENT["counts"]
    assert CURRENT["historical_portfolio_contract_replaced"] is False
