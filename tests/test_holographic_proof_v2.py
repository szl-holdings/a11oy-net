#!/usr/bin/env python3
"""Offline contracts for the A11oy Holographic Evidence Vault v2."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS_PATH = ROOT / "assets" / "szl-holo-proof-v2.css"
JS_PATH = ROOT / "scripts" / "szl-holo-proof-v2.js"
BINDER_PATH = ROOT / "tools" / "rollout_holographic_proof_v2.py"
STATE_PATH = ROOT / "holographic-experience-v2" / "rollout-state.json"
STYLE_MARKER = 'data-szl-proof-holo-asset="style-v2"'
SCRIPT_MARKER = 'data-szl-proof-holo-asset="script-v2"'
STATIC_MARKER = 'data-szl-proof-holo-static="v2"'
ADOPTED_MARKER = 'data-szl-proof-holo-adopted="true"'
BASELINE_ZERO_JAVASCRIPT = {
    "404.html",
    "chat/index.html",
    "code/index.html",
    "diligence/index.html",
    "notes/index.html",
    "record/index.html",
}


def source_requires_zero_javascript(relative: str) -> bool:
    text = (ROOT / relative).read_text(encoding="utf-8")
    return relative in BASELINE_ZERO_JAVASCRIPT or bool(
        re.search(
            r"(?:^|[;\"'\s])script-src\s+(?:'none'|\"none\")(?:[;\"'\s]|$)",
            text,
            flags=re.IGNORECASE,
        )
    )


class HolographicProofV2Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.css = CSS_PATH.read_text(encoding="utf-8")
        cls.javascript = JS_PATH.read_text(encoding="utf-8")
        cls.binder = BINDER_PATH.read_text(encoding="utf-8")
        cls.state = json.loads(STATE_PATH.read_text(encoding="utf-8"))

    def test_proof_identity_is_restrained_and_evidence_specific(self) -> None:
        implementation = (self.css + self.javascript).lower()
        for token in (
            "holographic evidence vault",
            "checksum constellations",
            "--szl-proof-v2-mint",
            "--szl-proof-v2-amber",
            "repeating-linear-gradient",
        ):
            self.assertIn(token, implementation)
        self.assertNotIn("threat-lattice", self.css)
        self.assertNotIn("agent-swarm", self.css)

    def test_accessibility_contract(self) -> None:
        for token in (
            "min-height:44px",
            "safe-area-inset",
            "prefers-reduced-motion",
            "prefers-contrast",
            "forced-colors",
            "focus-visible",
            "@media print",
        ):
            self.assertIn(token, self.css)
        for token in ("Escape", "aria-expanded", "Skip to main content"):
            self.assertIn(token, self.javascript)

    def test_runtime_is_first_party_non_tracking_and_bounded(self) -> None:
        implementation = self.css + "\n" + self.javascript
        for prohibited in (
            "fetch(", "XMLHttpRequest", "sendBeacon", "localStorage", "sessionStorage",
            "document.cookie", "google-analytics", "googletagmanager", "cdn.jsdelivr.net",
            "unpkg.com", "fonts.googleapis.com", "setInterval",
        ):
            self.assertNotIn(prohibited, implementation)
        self.assertIn("requestAnimationFrame", self.javascript)
        self.assertIn("SAVE_DATA", self.javascript)
        self.assertIn("document.hidden", self.javascript)
        self.assertLessEqual(self.css.count("animation:"), 2)

    def test_decorative_motion_is_not_telemetry(self) -> None:
        self.assertIn("measuredTelemetry: false", self.javascript)
        self.assertIs(self.state["decorative_motion_is_measured_telemetry"], False)
        self.assertIn("Decorative effects never imply measured runtime state", self.css)

    def test_zero_javascript_contract_is_explicit_and_csp_aware(self) -> None:
        state_zero = set(self.state["zero_javascript_documents"])
        self.assertTrue(BASELINE_ZERO_JAVASCRIPT.issubset(state_zero))
        for relative in BASELINE_ZERO_JAVASCRIPT:
            self.assertIn(f'"{relative}"', self.binder)
        self.assertIn("has_zero_javascript_contract", self.binder)
        self.assertIn("script-src", self.binder)
        self.assertIn("static_rail", self.binder)
        self.assertIn("remove_own_script", self.binder)
        self.assertIn(STATIC_MARKER, self.binder)
        self.assertIn(ADOPTED_MARKER, self.binder)

    def test_existing_flow_rail_is_adopted_not_duplicated(self) -> None:
        self.assertIn("adopt_existing_rail", self.binder)
        self.assertIn("szl-proof-static-rail|szl-proof-rail", self.binder)
        self.assertIn("adoptExistingRail", self.javascript)
        self.assertIn('querySelector(".szl-proof-rail, .szl-proof-static-rail")', self.javascript)

    def test_stylesheet_is_balanced_and_mobile_safe(self) -> None:
        without_comments = re.sub(r"/\*.*?\*/", "", self.css, flags=re.DOTALL)
        self.assertEqual(without_comments.count("{"), without_comments.count("}"))
        self.assertIn("overflow-x:clip", self.css)
        self.assertIn("max-width:760px", self.css)
        self.assertIn("overflow-x:auto", self.css)

    def test_raw_asset_budgets(self) -> None:
        self.assertLess(CSS_PATH.stat().st_size, 60_000)
        self.assertLess(JS_PATH.stat().st_size, 40_000)

    def test_rollout_state_enforces_exact_mode_when_active(self) -> None:
        self.assertIn(self.state["state"], {"ASSETS_READY", "ROLLED_OUT"})
        if self.state["state"] != "ROLLED_OUT":
            return
        bindings = set(self.state.get("bindings", []))
        discovered = {path.relative_to(ROOT).as_posix() for path in ROOT.rglob("index.html")}
        discovered.add("404.html")
        self.assertEqual(bindings, discovered)
        self.assertEqual(self.state["bound_documents"], len(bindings))
        expected_static = {relative for relative in bindings if source_requires_zero_javascript(relative)}
        self.assertEqual(set(self.state["zero_javascript_documents"]), expected_static)
        for relative in bindings:
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertEqual(text.count(STYLE_MARKER), 1, relative)
            self.assertIn('data-szl-proof-holo="v2"', text, relative)
            if relative in expected_static:
                self.assertEqual(text.count(SCRIPT_MARKER), 0, relative)
                self.assertNotIn("<script src=\"/scripts/szl-holo-proof-v2.js\"", text, relative)
                self.assertTrue(STATIC_MARKER in text or ADOPTED_MARKER in text, relative)
            else:
                self.assertEqual(text.count(SCRIPT_MARKER), 1, relative)


if __name__ == "__main__":
    unittest.main(verbosity=2)
