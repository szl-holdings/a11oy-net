#!/usr/bin/env python3
"""Offline contract checks for the monochrome proof Flow Shell."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "assets" / "szl-flow-proof.css"
STATIC_CSS = ROOT / "assets" / "szl-flow-proof-static.css"
JS = ROOT / "scripts" / "szl-flow-proof.js"
ROLLOUT = ROOT / "tools" / "rollout_proof_flow_shell.py"
REGISTRY = ROOT / "frontend-theme-registry-v1.json"
STATE = ROOT / "frontend-flow-shell-state.json"
STYLE_MARKER = 'data-szl-proof-flow-asset="style"'
STATIC_STYLE_MARKER = 'data-szl-proof-flow-asset="static-style"'
SCRIPT_MARKER = 'data-szl-proof-flow-asset="script"'
STATIC_MARKER = 'data-szl-proof-flow-asset="static"'
NO_SCRIPT_DOCUMENTS = {
    "404.html",
    "chat/index.html",
    "code/index.html",
    "diligence/index.html",
    "notes/index.html",
    "record/index.html",
}
ALLOWED_HEX = {"#000", "#080c14", "#1c1c1f", "#2a2a2e", "#7f7f83", "#9a9a9e", "#f0eee6"}


class ProofFlowShellContract(unittest.TestCase):
    def setUp(self) -> None:
        self.css = CSS.read_text(encoding="utf-8")
        self.static_css = STATIC_CSS.read_text(encoding="utf-8")
        self.js = JS.read_text(encoding="utf-8")
        self.rollout = ROLLOUT.read_text(encoding="utf-8")
        self.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        self.state = json.loads(STATE.read_text(encoding="utf-8"))

    def test_proof_shell_is_strictly_neutral(self) -> None:
        styles = self.css + "\n" + self.static_css
        hexes = {item.lower() for item in re.findall(r"#[0-9a-fA-F]{3,8}", styles)}
        self.assertEqual(hexes - ALLOWED_HEX, set())
        allowed_rgb = {(0, 0, 0), (255, 255, 255), (8, 12, 20), (13, 13, 15)}
        for match in re.finditer(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", styles):
            rgb = tuple(int(match.group(i)) for i in (1, 2, 3))
            self.assertIn(rgb, allowed_rgb, match.group(0))
        self.assertEqual(styles.count("{"), styles.count("}"))

    def test_shared_accessibility_contract(self) -> None:
        self.assertIn("min-height: 44px", self.css)
        self.assertIn("safe-area-inset-bottom", self.css)
        self.assertIn("prefers-reduced-motion", self.css)
        self.assertIn("forced-colors", self.css)
        self.assertIn("overflow-x: auto", self.static_css)

    def test_five_journeys_join_product_and_record(self) -> None:
        implementation = self.js + "\n" + self.rollout
        for label in ("Start Here", "Products & Demos", "Models & Data", "Kernels & SDKs", "Proofs & Research"):
            self.assertIn(label, implementation)
        self.assertIn("https://a-11-oy.com", implementation)
        self.assertIn("https://a11oy.net", implementation)
        self.assertIn("aria-current", implementation)

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
            bound = set(self.state.get("injected_documents", []))
            self.assertEqual(bound, {path.relative_to(ROOT).as_posix() for path in ROOT.rglob("index.html")} | {"404.html"})
            self.assertEqual(set(self.state.get("zero_javascript_documents", [])), NO_SCRIPT_DOCUMENTS)
            for rel in bound:
                text = (ROOT / rel).read_text(encoding="utf-8")
                self.assertEqual(text.count(STYLE_MARKER), 1, rel)
                if rel in NO_SCRIPT_DOCUMENTS:
                    self.assertEqual(text.count(STATIC_STYLE_MARKER), 1, rel)
                    self.assertEqual(text.count(STATIC_MARKER), 1, rel)
                    self.assertEqual(text.count(SCRIPT_MARKER), 0, rel)
                    self.assertNotIn("<script", text.lower(), rel)
                    self.assertIn('data-szl-proof-flow="record"', text, rel)
                else:
                    self.assertEqual(text.count(SCRIPT_MARKER), 1, rel)
                    self.assertEqual(text.count(STATIC_MARKER), 0, rel)

    def test_no_script_contract_is_explicit_and_complete(self) -> None:
        for rel in NO_SCRIPT_DOCUMENTS:
            self.assertIn(f'"{rel}"', self.rollout)
        self.assertIn("static_rail", self.rollout)
        self.assertIn("STATIC_STYLE", self.rollout)

    def test_assets_are_local_only(self) -> None:
        implementation = self.css + self.static_css + self.js + self.rollout
        self.assertNotRegex(implementation, r"https?://(?:cdn|unpkg|jsdelivr)")


if __name__ == "__main__":
    unittest.main()
