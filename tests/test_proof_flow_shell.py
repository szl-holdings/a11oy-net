#!/usr/bin/env python3
"""Offline contract checks for the monochrome proof Flow Shell."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "assets" / "szl-flow-proof.css"
JS = ROOT / "scripts" / "szl-flow-proof.js"
REGISTRY = ROOT / "frontend-theme-registry-v1.json"
STATE = ROOT / "frontend-flow-shell-state.json"
STYLE_MARKER = 'data-szl-proof-flow-asset="style"'
SCRIPT_MARKER = 'data-szl-proof-flow-asset="script"'
ALLOWED_HEX = {"#000", "#080c14", "#1c1c1f", "#2a2a2e", "#7f7f83", "#9a9a9e", "#f0eee6"}


class ProofFlowShellContract(unittest.TestCase):
    def setUp(self) -> None:
        self.css = CSS.read_text(encoding="utf-8")
        self.js = JS.read_text(encoding="utf-8")
        self.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        self.state = json.loads(STATE.read_text(encoding="utf-8"))

    def test_proof_shell_is_strictly_neutral(self) -> None:
        hexes = {item.lower() for item in re.findall(r"#[0-9a-fA-F]{3,8}", self.css)}
        self.assertEqual(hexes - ALLOWED_HEX, set())
        allowed_rgb = {(0, 0, 0), (255, 255, 255), (8, 12, 20), (13, 13, 15)}
        for match in re.finditer(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", self.css):
            rgb = tuple(int(match.group(i)) for i in (1, 2, 3))
            self.assertIn(rgb, allowed_rgb, match.group(0))
        self.assertEqual(self.css.count("{"), self.css.count("}"))

    def test_shared_accessibility_contract(self) -> None:
        self.assertIn("min-height: 44px", self.css)
        self.assertIn("safe-area-inset-bottom", self.css)
        self.assertIn("prefers-reduced-motion", self.css)
        self.assertIn("forced-colors", self.css)

    def test_five_journeys_join_product_and_record(self) -> None:
        for label in ("Start Here", "Products & Demos", "Models & Data", "Kernels & SDKs", "Proofs & Research"):
            self.assertIn(label, self.js)
        self.assertIn("https://a-11-oy.com", self.js)
        self.assertIn("https://a11oy.net", self.js)
        self.assertIn("aria-current", self.js)

    def test_keep_six_registry_is_unique(self) -> None:
        rows = self.registry["application_spaces"]
        self.assertEqual(len(rows), 6)
        self.assertEqual(len({row["instrument"] for row in rows}), 6)
        self.assertEqual(self.registry["shared_contract"]["viewports"], [320, 360, 390, 768, 1024, 1440])

    def test_proof_routes_keep_distinct_monochrome_motifs(self) -> None:
        themes = set(self.registry["proof_routes"].values())
        self.assertGreaterEqual(len(themes), 9)
        for theme in themes - {"ledger"}:
            self.assertIn(f'data-szl-proof-theme="{theme}"', self.css)

    def test_rollout_state_enforces_bound_documents(self) -> None:
        self.assertIn(self.state["state"], {"ASSETS_READY", "ROLLED_OUT"})
        if self.state["state"] == "ROLLED_OUT":
            root = (ROOT / "index.html").read_text(encoding="utf-8")
            self.assertEqual(root.count(STYLE_MARKER), 1)
            self.assertEqual(root.count(SCRIPT_MARKER), 1)
            for rel in self.state.get("injected_documents", []):
                text = (ROOT / rel).read_text(encoding="utf-8")
                self.assertEqual(text.count(STYLE_MARKER), 1, rel)
                self.assertEqual(text.count(SCRIPT_MARKER), 1, rel)

    def test_assets_are_local_only(self) -> None:
        self.assertNotRegex(self.css + self.js, r"https?://(?:cdn|unpkg|jsdelivr)")


if __name__ == "__main__":
    unittest.main()
