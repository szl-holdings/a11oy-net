#!/usr/bin/env python3
"""Offline contracts for the neutral SZL Spectral Proof v2 layer."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS_PATH = ROOT / "assets" / "szl-spectral-proof-v2.css"
BASE_CSS_PATH = ROOT / "assets" / "szl-flow-proof.css"
STATIC_CSS_PATH = ROOT / "assets" / "szl-flow-proof-static.css"
JS_PATH = ROOT / "scripts" / "szl-flow-proof.js"
REGISTRY_PATH = ROOT / "frontend-theme-registry-v2.json"
CONTRACT_PATH = ROOT / "SPECTRAL_PROOF_V2.md"


class SpectralProofV2Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.css = CSS_PATH.read_text(encoding="utf-8")
        cls.base_css = BASE_CSS_PATH.read_text(encoding="utf-8")
        cls.static_css = STATIC_CSS_PATH.read_text(encoding="utf-8")
        cls.js = JS_PATH.read_text(encoding="utf-8")
        cls.registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        cls.contract = CONTRACT_PATH.read_text(encoding="utf-8")

    def test_assets_are_local_bounded_and_balanced(self) -> None:
        self.assertLess(CSS_PATH.stat().st_size, 24_000)
        self.assertLess(JS_PATH.stat().st_size, 20_000)
        self.assertEqual(self.css.count("{"), self.css.count("}"))
        self.assertIn('var SPECTRAL_STYLE = "/assets/szl-spectral-proof-v2.css"', self.js)
        self.assertTrue(self.static_css.startswith('@import url("/assets/szl-spectral-proof-v2.css");'))
        self.assertNotRegex(self.css + self.js + self.static_css, r"https?://(?:cdn|unpkg|jsdelivr|fonts\.googleapis)")

    def test_new_spectral_sheet_has_no_semantic_color(self) -> None:
        hexes = {value.lower() for value in re.findall(r"#[0-9a-fA-F]{3,8}", self.css)}
        self.assertEqual(hexes - {"#000"}, set())
        allowed_rgb = {(0, 0, 0), (255, 255, 255), (8, 12, 20)}
        for match in re.finditer(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", self.css):
            rgb = tuple(int(match.group(index)) for index in (1, 2, 3))
            self.assertIn(rgb, allowed_rgb, match.group(0))
        for word in ("red", "orange", "yellow", "green", "cyan", "teal", "blue", "purple", "violet", "magenta"):
            self.assertIsNone(re.search(rf"\b{word}\b", self.css, re.IGNORECASE), word)
        self.assertEqual(self.registry["palette_contract"]["mode"], "STRICT_NEUTRAL")
        self.assertIs(self.registry["palette_contract"]["semantic_color"], False)

    def test_runtime_is_nontracking_and_nonmutating(self) -> None:
        combined = self.css + self.js
        for prohibited in (
            "fetch(",
            "XMLHttpRequest",
            "sendBeacon",
            "localStorage",
            "sessionStorage",
            "document.cookie",
            "google-analytics",
        ):
            self.assertNotIn(prohibited, combined)
        self.assertIn("Decorative layers never imply evidence", self.css)
        self.assertIs(self.registry["shared_contract"]["decorative_layers_are_evidence"], False)

    def test_nine_proof_routes_are_distinct_archival_instruments(self) -> None:
        instruments = self.registry["proof_instruments"]
        self.assertEqual(len(instruments), 9)
        self.assertEqual(len({item["route"] for item in instruments}), 9)
        self.assertEqual(len({item["theme"] for item in instruments}), 9)
        for item in instruments:
            self.assertIn(f'body[data-szl-proof-theme="{item["theme"]}"]', self.css)
            self.assertIn(item["label"], self.js)

    def test_holographic_field_has_six_layers_and_one_scheduler(self) -> None:
        for layer in ("grid", "ledger", "nodes", "beam", "scan", "bloom"):
            self.assertIn(f"szl-proof-spectral-{layer}", self.css)
            self.assertIn(f'"{layer}"', self.js)
        self.assertIn("requestAnimationFrame", self.js)
        self.assertIn("pointermove", self.js)
        self.assertNotIn("setInterval", self.js)

    def test_adaptive_performance_and_accessibility_contracts_exist(self) -> None:
        for token in (
            "prefers-reduced-motion",
            "saveData",
            "deviceMemory",
            "hardwareConcurrency",
            'return "quiet"',
            'return "balanced"',
            'return "full"',
        ):
            self.assertIn(token, self.js)
        combined = self.css + self.base_css + self.static_css + self.js
        for token in (
            "min-height: 44px",
            "focus-visible",
            "safe-area-inset-bottom",
            "prefers-reduced-motion",
            "prefers-contrast",
            "forced-colors",
            "@media print",
            'event.key !== "Escape"',
            "aria-live",
            "aria-current",
        ):
            self.assertIn(token, combined)

    def test_zero_javascript_records_remain_zero_javascript(self) -> None:
        expected = set(self.registry["zero_javascript_documents"])
        self.assertEqual(
            expected,
            {"404.html", "chat/index.html", "code/index.html", "diligence/index.html", "notes/index.html", "record/index.html"},
        )
        for relative in expected:
            source = (ROOT / relative).read_text(encoding="utf-8")
            self.assertNotIn("<script", source.lower(), relative)
            self.assertIn('data-szl-proof-flow="record"', source, relative)
            self.assertIn('data-szl-proof-flow-asset="static"', source, relative)

    def test_shared_journeys_connect_distinct_failure_domains(self) -> None:
        journeys = self.registry["shared_contract"]["journeys"]
        self.assertEqual(
            [item["label"] for item in journeys],
            ["Start Here", "Products & Demos", "Models & Data", "Kernels & SDKs", "Proofs & Research"],
        )
        for item in journeys:
            self.assertIn(item["label"], self.js)
        self.assertIn("https://a-11-oy.com", self.js)
        self.assertIn("https://a11oy.net", self.js)
        self.assertIs(self.registry["relationship"]["shared_flow"], True)
        self.assertIs(self.registry["relationship"]["shared_trade_dress"], False)

    def test_truth_boundary_is_explicit(self) -> None:
        truth = " ".join(self.registry["truth_boundary"]).lower()
        self.assertIn("reachability", truth)
        self.assertIn("deployment evidence", truth)
        self.assertIn("machine-readable record", truth)
        self.assertIn("Holographic layers do not establish authenticity", self.contract)


if __name__ == "__main__":
    unittest.main(verbosity=2)
