# SPDX-License-Identifier: Apache-2.0
# © 2026 Lutar, Stephen P. — SZL Holdings · ORCID 0009-0001-0110-4173
# Doctrine v11 LOCKED. Λ = Conjecture 1 (NOT a theorem).
"""Fail-closed unit tests for the a11oy.net investor smoke gate (no live HTTP).

S7 against live index.html chips lives in test_investor_smoke_bind.py so this
file can stay green while INTI's /honest bind is still RED.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import investor_smoke_gate as gate  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "investor_smoke"


def test_skip_as_green_is_rejected():
    empty = gate.Matrix()
    errors = gate.validate_matrix(empty, required=("S7", "S1"))
    assert any("missing probe S7" in err for err in errors)
    assert any("missing probe S1" in err for err in errors)
    assert any("skip-as-green" in err for err in errors)


def test_snapshot_without_date_is_rejected():
    with pytest.raises(ValueError, match="SNAPSHOT requires a date"):
        gate.Verdict(id="L1", status="SNAPSHOT", detail="stress", evidence="none")


def test_snapshot_with_date_is_accepted():
    item = gate.Verdict(
        id="L1",
        status="SNAPSHOT",
        detail="not run",
        evidence="SNAPSHOT 2026-08-28",
        snapshot_date="2026-08-28",
    )
    matrix = gate.Matrix()
    matrix.add(item)
    errors = gate.validate_matrix(matrix, required=("L1",))
    assert errors == []


def test_unavailable_only_for_listed_ids():
    matrix = gate.Matrix()
    matrix.add(
        gate.Verdict(id="S1", status="UNAVAILABLE", detail="network", evidence="none")
    )
    errors = gate.validate_matrix(matrix, required=("S1",))
    assert any("UNAVAILABLE not allowed" in err for err in errors)


def test_s4_s6_s9_unavailable_is_honest():
    matrix = gate.Matrix()
    for item in gate.unavailable_placeholders():
        matrix.add(item)
    errors = gate.validate_matrix(matrix, required=("S4", "S6", "S9"))
    assert errors == []


def test_post_is_forbidden():
    with pytest.raises(ValueError, match="forbids POST"):
        gate.http_request("https://example.invalid/", method="POST")


def test_s7_fails_when_kernel_chip_is_genome():
    text = (FIXTURES / "kernel_slot_genome_bind.html").read_text(encoding="utf-8")
    failures = gate.kernel_slot_bind_failures(text, source_name="fixture-genome")
    assert failures
    blob = " ".join(failures)
    assert "LOCKED-PROVEN" in blob or "cnt-locked" in blob
    verdict = gate.s7_bind_agreement(extra_evidence=failures, chips_bind_honest=False)
    assert verdict.status == "FAIL"
    assert verdict.owner == "INTI"
    assert "25" in verdict.detail


def test_s7_fails_when_kernel_chip_is_static_eight_without_honest():
    text = (FIXTURES / "kernel_slot_static_eight.html").read_text(encoding="utf-8")
    failures = gate.kernel_slot_bind_failures(text, source_name="fixture-static")
    assert failures
    assert any("hardcoded" in item.lower() or "does not bind" in item for item in failures)


def test_s7_passes_when_kernel_chip_binds_honest_and_catalog_25_is_labelled():
    text = (FIXTURES / "kernel_slot_honest_bind.html").read_text(encoding="utf-8")
    failures = gate.kernel_slot_bind_failures(text, source_name="fixture-honest")
    assert failures == []
    verdict = gate.s7_bind_agreement(chips_bind_honest=True)
    assert verdict.status == "PASS"


def test_d5_labels_catalog_25_not_kernel():
    verdict = gate.evaluate_catalog_vs_kernel(ROOT)
    assert verdict.status == "PASS"
    assert verdict.id == "D5"
    assert "25" in verdict.detail
    assert "S7" in verdict.detail


def test_s11_missing_space_is_fail_not_skip():
    verdict = gate.s11_verdict(ROOT)
    assert verdict.status == "FAIL", verdict.detail
    assert "skip" in verdict.detail.lower() or "no Hugging Face Space" in verdict.detail


def test_s12_missing_yaml_is_fail_not_skip():
    verdict = gate.s12_verdict(ROOT)
    assert verdict.status == "FAIL", verdict.detail
    assert "FAIL" in verdict.detail or "frontmatter" in verdict.detail or "YAML" in verdict.detail


def test_l_rows_are_snapshot_2026_08_28():
    rows = {item.id: item for item in gate.snapshot_l_verdicts()}
    assert set(rows) == set(gate.SNAPSHOT_IDS)
    for item in rows.values():
        assert item.status == "SNAPSHOT"
        assert item.snapshot_date == "2026-08-28"
        assert "no N" in item.detail


def test_unlabeled_iss_coords_are_red():
    payload = {
        "source": "Where-the-ISS-at",
        "mode": "live",
        "data": {"latitude": 27.4, "longitude": -91.3, "altitude": 417.7},
    }
    hits = gate.unlabeled_numeric_coords(payload)
    assert hits, "bare ISS digits must be unlabeled FAIL"


def test_measured_without_method_is_not_enough():
    payload = {
        "data": {"latitude": {"value": 27.4, "label": "MEASURED"}},
    }
    assert gate.unlabeled_numeric_coords(payload), "MEASURED without method is unlabeled"


def test_measured_with_method_and_unavailable_are_ok():
    measured = {
        "data": {
            "latitude": {"value": 27.4, "label": "MEASURED", "method": "where-the-iss-at"},
            "longitude": {"value": -91.3, "label": "MEASURED", "method": "where-the-iss-at"},
        },
    }
    assert gate.unlabeled_numeric_coords(measured) == []
    unavailable_num = {
        "data": {"latitude": {"value": 0.0, "label": "UNAVAILABLE"}},
    }
    assert gate.unlabeled_numeric_coords(unavailable_num) == []


def test_first_viewport_rejects_bare_latitude():
    html = "<section id='hero'><p>latitude 27.3999 longitude -91.32</p></section>"
    hits = gate.first_viewport_unlabeled_latitude(html)
    assert hits
    labelled = "<section id='hero'><p>latitude UNAVAILABLE</p></section>"
    assert gate.first_viewport_unlabeled_latitude(labelled) == []
    measured = (
        "<section id='hero'><p>latitude 27.4 MEASURED method=where-the-iss-at</p></section>"
    )
    assert gate.first_viewport_unlabeled_latitude(measured) == []


def test_index_first_viewport_has_no_raw_latitude():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    assert gate.first_viewport_unlabeled_latitude(html) == []


def test_signer_enum_extract():
    assert (
        gate.extract_signer_status({"rollup": {"signer": {"status": "DSSE-LIVE"}}})
        == "DSSE-LIVE"
    )
    assert gate.extract_signer_status({"lean_sha": "c7c0ba17", "status": "ok"}) is None
    assert gate.extract_sha({"lean_sha": "c7c0ba17"}) is None
    assert gate.extract_sha({"git_sha": "dffd0c03b9dfcc3af4f0a5f6576a854e3bc0f894"})


def test_s2_requires_sha_and_signer():
    fail = gate.s2_from_payload({"git_sha": "abc"}, source="/health.json")
    assert fail
    fail2 = gate.s2_from_payload(
        {"git_sha": "abc", "signer": {"status": "DSSE-LIVE"}}, source="/health.json"
    )
    assert fail2 == []


def test_locked_formula_count_nested_or_top_level():
    assert gate.locked_formula_count_from_honest({"locked_formula_count": 8}) == 8
    assert (
        gate.locked_formula_count_from_honest(
            {"doctrine_lock": {"locked_formula_count": 8}}
        )
        == 8
    )
    assert gate.locked_formula_count_from_honest({"kernel_commit": "c7c0ba17"}) is None


def test_static_debug_rows_are_honest():
    rows = {item.id: item for item in gate.static_debug_verdicts(ROOT)}
    for key in ("D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9"):
        assert rows[key].status == "PASS", (key, rows[key].detail, rows[key].evidence)
    assert rows["D10"].status == "SNAPSHOT"
    assert rows["D10"].snapshot_date == "2026-08-28"
    assert rows["wire-D"].status == "UNCONFIGURED"


def test_inclusion_labels_gaps_does_not_invent_agreement():
    verdict = gate.inclusion_verdict(ROOT)
    assert verdict.status == "PASS"
    assert "labelled gap" in verdict.detail
    assert "do not invent" in verdict.detail.lower()
    assert "no git tags" in verdict.evidence or "HF card" in verdict.evidence


def test_contract_matrix_does_not_skip_required_ids():
    matrix = gate.contract_matrix(ROOT)
    errors = gate.validate_matrix(matrix, required=gate.CONTRACT_REQUIRED_IDS)
    assert errors == []
    assert matrix.by_id("S7") is not None
    assert matrix.by_id("S7").status == "FAIL"
    assert matrix.by_id("S11").status == "FAIL"
    assert matrix.by_id("S12").status == "FAIL"


def test_s5_static_does_not_mint():
    verdict = gate.s5_static_verdict(ROOT)
    assert verdict.status == "PASS", verdict.detail
