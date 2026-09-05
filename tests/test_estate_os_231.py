# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

DATA = Path("estate/os/data.json")
BAKE = Path("estate/os/bake.json")
RECEIPT = Path("estate/os/materialization-receipt.json")
APP = Path("estate/os/app.js")
FLOW_STATE = Path("frontend-flow-shell-state.json")
HOLO_STATE = Path("holographic-experience-v2/rollout-state.json")

EXPECTED_LANES = {
    "github": 117,
    "model": 44,
    "dataset": 33,
    "space": 16,
    "collection": 21,
}
EXPECTED_RINGS = {
    "holographic": 6,
    "flagship": 8,
    "vertical": 57,
    "kernel": 50,
    "archive": 38,
    "docs": 64,
    "organ": 8,
}
EXPECTED_NEW_PROOF_DOCUMENTS = {
    "estate/frontier-2026-09-04/index.html",
    "status/index.html",
    "estate/alloy-os/index.html",
    "estate/szl-frontier/index.html",
    "khipu/nan/index.html",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_monolith_is_complete_unique_and_bounded() -> None:
    payload = load(DATA)
    assets = payload["assets"]
    assert payload["contract"] == "szl.estate-hud.hologram/v1"
    assert payload["scope"] == "PUBLIC_PARTIAL"
    assert payload["honesty"] == "UNSIGNED-honest"
    assert payload["lambda"] == "Conjecture 1 OPEN"
    assert len(assets) == 231
    assert len({row["id"] for row in assets}) == 231
    assert Counter(row["lane"] for row in assets) == Counter(EXPECTED_LANES)
    assert Counter(row["ring"] for row in assets) == Counter(EXPECTED_RINGS)
    assert payload["counts"]["assets"] == 231
    assert DATA.stat().st_size <= 200_000


def test_origin_and_runtime_truth_boundaries_are_preserved() -> None:
    payload = load(DATA)
    encoded = DATA.read_text(encoding="utf-8")
    assert payload["surface"]["url"] == "https://a11oy.net/estate/os/"
    assert payload["surface"]["product"] == "https://a-11-oy.com"
    assert payload["surface"]["proof"] == "https://a11oy.net"
    foreign_origin = "https://a11oy" + ".com"
    assert foreign_origin not in encoded
    assert payload["generation"]["runtimeProbesPerformed"] is False
    assert payload["generation"]["providerMutationsPerformed"] is False
    assert payload["generation"]["credentialValuesRecorded"] is False
    assert payload["laterRecapture"]["huggingface"]["spaces_public"] == 48


def test_bake_and_receipt_bind_exact_monolith_bytes() -> None:
    raw = DATA.read_bytes()
    bake = load(BAKE)
    receipt = load(RECEIPT)
    expected_sha = hashlib.sha256(raw).hexdigest()
    assert bake["monolith"]["bytes"] == len(raw)
    assert bake["monolith"]["sha256"] == expected_sha
    assert bake["monolith"]["uniqueAssets"] == 231
    assert receipt["complete"] is True
    assert receipt["monolith"]["sha256"] == expected_sha
    assert receipt["provider_mutations_performed"] is False
    assert receipt["credential_values_recorded"] is False


def test_renderer_loads_only_the_committed_monolith() -> None:
    source = APP.read_text(encoding="utf-8")
    assert 'fetch("./data.json", { redirect: "error" })' in source
    assert "assets-github-a.json" not in source
    assert "assets-model.json" not in source
    assert "data.json did not load" in source
    assert "not an observed-empty inventory" in source


def test_new_proof_documents_are_registered_by_both_shells() -> None:
    flow = load(FLOW_STATE)
    holo = load(HOLO_STATE)
    flow_documents = set(flow["injected_documents"])
    holo_documents = set(holo["bindings"])
    assert EXPECTED_NEW_PROOF_DOCUMENTS <= flow_documents
    assert EXPECTED_NEW_PROOF_DOCUMENTS <= holo_documents
    assert flow["examined_documents"] == len(flow_documents)
    assert holo["bound_documents"] == len(holo_documents)
