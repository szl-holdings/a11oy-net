#!/usr/bin/env python3
"""Offline contracts for the proof-origin mobile-to-theatre layer."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "assets" / "szl-adaptive-proof-v3.css"
JS = ROOT / "scripts" / "szl-adaptive-proof-v3.js"
HOST_CSS = ROOT / "assets" / "szl-holo-proof-v2.css"
HOST_JS = ROOT / "scripts" / "szl-holo-proof-v2.js"
CSS_IMPORT = '@import url("/assets/szl-adaptive-proof-v3.css"); /* szl:adaptive-proof-v3 */'
JS_LOADER = "data-szl-adaptive-proof-v3-loader"
NO_SCRIPT_DOCUMENTS = (
    "404.html",
    "chat/index.html",
    "code/index.html",
    "diligence/index.html",
    "notes/index.html",
    "record/index.html",
)


class AdaptiveProofV3Contract(unittest.TestCase):
    def setUp(self) -> None:
        self.css = CSS.read_text(encoding="utf-8")
        self.js = JS.read_text(encoding="utf-8")
        self.host_css = HOST_CSS.read_text(encoding="utf-8")
        self.host_js = HOST_JS.read_text(encoding="utf-8")

    def test_host_assets_load_the_layer_exactly_once(self) -> None:
        self.assertEqual(self.host_css.count(CSS_IMPORT), 1)
        self.assertEqual(self.host_js.count(JS_LOADER), 1)

    def test_zero_javascript_records_remain_script_free(self) -> None:
        for rel in NO_SCRIPT_DOCUMENTS:
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertNotIn("<script", text.lower(), rel)
            self.assertNotIn("szl-adaptive-proof-v3.js", text, rel)

    def test_all_viewport_modes_and_landscape_exist(self) -> None:
        for mode in ("mobile", "tablet", "desktop", "theatre"):
            self.assertIn(f'"{mode}"', self.js)
        self.assertIn('data-szl-proof-display-mode="theatre"', self.css)
        self.assertIn("orientation: landscape", self.css)

    def test_touch_overflow_and_accessibility_contracts(self) -> None:
        for token in (
            "--szl-proof-control: 44px",
            "--szl-proof-control-coarse: 48px",
            "overflow-x: clip",
            "overflow-x: auto",
            "safe-area-inset-bottom",
            "container-type: inline-size",
            "prefers-reduced-motion: reduce",
            "prefers-contrast: more",
            "forced-colors: active",
            ":focus-visible",
            "@media print",
        ):
            self.assertIn(token, self.css)

    def test_live_root_targets_inherit_the_full_control_contract(self) -> None:
        selector = ":where(.wordmark, .nav-links a, .origin-switch a, .origin-banner a)"
        self.assertIn(selector, self.css)
        start = self.css.index(selector)
        end = self.css.index("}\n", start)
        rule = self.css[start:end]
        for declaration in (
            "display: inline-flex",
            "min-width: var(--szl-proof-control)",
            "min-height: var(--szl-proof-control)",
            "align-items: center",
            "justify-content: center",
            "touch-action: manipulation",
        ):
            self.assertIn(declaration, rule)

    def test_proof_palette_remains_neutral(self) -> None:
        allowed = {"#fff", "#000"}
        actual = {value.lower() for value in re.findall(r"#[0-9a-fA-F]{3,8}", self.css)}
        self.assertEqual(actual - allowed, set())

    def test_controller_has_no_network_tracking_or_persistence(self) -> None:
        for token in ("fetch(", "XMLHttpRequest", "sendBeacon", "localStorage", "sessionStorage", "document.cookie", "analytics"):
            self.assertNotIn(token, self.js)

    def test_assets_are_bounded_and_truth_neutral(self) -> None:
        self.assertLess(CSS.stat().st_size, 28_000)
        self.assertLess(JS.stat().st_size, 16_000)
        self.assertEqual(self.css.count("{"), self.css.count("}"))
        self.assertNotRegex(self.css + self.js, r"https?://(?:cdn|unpkg|jsdelivr)")
        self.assertIn("Presentation never upgrades an evidence class", self.css)
        self.assertNotIn("DSSE-LIVE", self.js)
        self.assertNotIn("MEASURED", self.js)


if __name__ == "__main__":
    unittest.main()
