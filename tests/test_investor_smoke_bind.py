# SPDX-License-Identifier: Apache-2.0
# © 2026 Lutar, Stephen P. — SZL Holdings · ORCID 0009-0001-0110-4173
# Doctrine v11 LOCKED. Λ = Conjecture 1 (NOT a theorem).
"""S7 fail-closed: every a11oy.net kernel chip binds /honest (8 or N/A / UNAVAILABLE).

Committed chips bind via scripts/honest_kernel_bind.js (#24). Catalog genome
LOCKED-PROVEN=25 stays labelled. Do not demand 25 be deleted. Hardcoded 8 is
not a bind.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import investor_smoke_gate as gate  # noqa: E402


def test_every_kernel_chip_binds_honest():
    verdict = gate.s7_verdict(ROOT)
    failures = gate.analyze_repo_kernel_binds(ROOT)
    assert not failures, (
        "a11oy.net kernel chips must bind /honest locked_formula_count=8 or N/A "
        "/ UNAVAILABLE, not genome LOCKED-PROVEN=25. Both numbers are real. "
        "Catalog 25 stays labelled. Do not demand 25 be deleted. "
        f"{failures} {verdict.detail}"
    )
    assert verdict.status == "PASS", verdict.detail
