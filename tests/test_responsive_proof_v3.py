#!/usr/bin/env python3
"""Offline mobile-to-theatre contract for the independent proof origin."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "assets" / "szl-responsive-proof-v3.css"
STATE = ROOT / "responsive-experience-v3.json"
HOSTS = (
    ROOT / "assets" / "szl-holo-proof-v2.css",
    ROOT / "assets" / "szl-flow-proof-static.css",
)
MARKER = "szl-responsive-proof-v3"


class ResponsiveProofV3Contract(unittest.TestCase):
    def setUp(self) -> None:
        self.css = CSS.read_text(encoding="utf-8")
        self.state = json.loads(STATE.read_text(encoding="utf-8"))

    def test_required_viewports_are_registered(self) -> None:
        viewports = {tuple(row) for row in self.state["viewports"]}
        required = {
            (320, 568), (375, 812), (430, 932), (812, 375), (768, 1024),
            (1440, 900), (1920, 1080), (2560, 1440), (3440, 1440),
        }
        self.assertTrue(required.issubset(viewports))

    def test_compact_landscape_tablet_and_theatre_rules_exist(self) -> None:
        for token in (
            "@media (max-width: 47.999rem)",
            "orientation: landscape",
            "@media (min-width: 100rem)",
            "@media (min-width: 150rem)",
            "grid-template-columns: repeat(12",
            "container-type: inline-size",
            "@container (max-width: 28rem)",
        ):
            self.assertIn(token, self.css)

    def test_evidence_bytes_remain_readable_not_truncated(self) -> None:
        for token in (
            "overflow-wrap: anywhere",
            "white-space: pre",
            "overflow: auto",
            "table-scroll",
            "ledger-scroll",
            "hash-block",
        ):
            self.assertIn(token, self.css)
        self.assertNotIn("text-overflow: ellipsis", self.css)
        self.assertNotIn("line-clamp", self.css)

    def test_touch_keyboard_safe_area_and_forms(self) -> None:
        self.assertIn("--proof-touch: 44px", self.css)
        self.assertIn("--proof-touch-coarse: 48px", self.css)
        self.assertIn(":focus-visible", self.css)
        self.assertIn("safe-area-inset-top", self.css)
        self.assertIn("safe-area-inset-bottom", self.css)
        self.assertIn("font-size: max(16px, 1em)", self.css)

    def test_accessibility_print_and_scriptless_modes(self) -> None:
        for token in (
            "prefers-reduced-motion",
            "prefers-contrast: more",
            "forced-colors: active",
            "@media print",
            ".szl-proof-static-rail",
        ):
            self.assertIn(token, self.css)
        self.assertTrue(self.state["requirements"]["zero_javascript_records_preserved"])

    def test_local_only_neutral_layout_asset(self) -> None:
        self.assertIsNone(re.search(r"https?://", self.css, re.IGNORECASE))
        for prohibited in ("fetch(", "localstorage", "sessionstorage", "document.cookie"):
            self.assertNotIn(prohibited, self.css.lower())
        self.assertEqual(self.css.count("{"), self.css.count("}"))

    def test_binding_state_is_explicit(self) -> None:
        self.assertIn(self.state["state"], {"ASSET_READY", "BOUND"})
        self.assertEqual(self.state["requirements"]["horizontal_overflow_px"], 0)
        self.assertEqual(self.state["requirements"]["external_runtime_dependencies"], 0)
        if self.state["state"] == "BOUND":
            for host in HOSTS:
                text = host.read_text(encoding="utf-8")
                self.assertEqual(text.count(MARKER), 1, host.name)
                self.assertTrue(text.lstrip().startswith('@import url("./szl-responsive-proof-v3.css")'))


if __name__ == "__main__":
    unittest.main()
