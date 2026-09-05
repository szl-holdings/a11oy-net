#!/usr/bin/env python3
"""Offline contract checks for the proof-origin Alloy local kernel."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "estate" / "alloy-os" / "index.html"
KERNEL = ROOT / "estate" / "alloy-os" / "kernel.js"
APP = ROOT / "estate" / "alloy-os" / "app.js"


class AlloyLocalKernelContract(unittest.TestCase):
    def setUp(self) -> None:
        self.page = PAGE.read_text(encoding="utf-8")
        self.kernel = KERNEL.read_text(encoding="utf-8")
        self.app = APP.read_text(encoding="utf-8")

    def test_page_loads_real_kernel_before_ui(self) -> None:
        self.assertTrue(KERNEL.is_file())
        self.assertLess(
            self.page.index('<script src="./kernel.js"></script>'),
            self.page.index('<script src="./app.js"></script>'),
        )
        self.assertIn("typeof Alloy", self.app)
        self.assertIn("Alloy.boot()", self.app)

    def test_crypto_and_persistence_are_first_party_and_origin_local(self) -> None:
        for primitive in (
            'name: "AES-GCM"',
            'length: 256',
            'name: "ECDSA"',
            'namedCurve: "P-256"',
            'digest("SHA-256"',
            "indexedDB.open",
            'const SNAPSHOT_KEY = "last-verified"',
        ):
            self.assertIn(primitive, self.kernel)
        self.assertNotRegex(self.kernel, r"\bfetch\s*\(")
        self.assertNotRegex(self.kernel, r"https?://")
        self.assertNotIn("XMLHttpRequest", self.kernel)
        self.assertNotIn("WebSocket", self.kernel)

    def test_receipts_are_signed_and_hash_chained(self) -> None:
        self.assertIn('prevDigest: state.receipts.at(-1)?.digest || "GENESIS"', self.kernel)
        self.assertIn('crypto.subtle.sign(', self.kernel)
        self.assertIn('crypto.subtle.verify(', self.kernel)
        self.assertIn('receipt.prevDigest !== previous', self.kernel)
        self.assertIn('(await sha256(payload)) !== receipt.digest', self.kernel)

    def test_adapter_block_and_tamper_heal_fail_closed(self) -> None:
        for contract in (
            'const ADAPTER_CURRENT = "alloy-local-v1"',
            'return deny(`adapter hard-block: expected ${ADAPTER_CURRENT}`',
            'corrupted[0] ^= 0x01',
            'capsule.status = "TAMPERED"',
            'persist({ verifiedSnapshot: false })',
            'restoreVerifiedSnapshot("watchdog restored last verified snapshot")',
        ):
            self.assertIn(contract, self.kernel)
        self.assertIn('state.health.blocked += 1', self.kernel)
        self.assertIn('state.health.healed += 1', self.kernel)

    def test_public_surface_matches_consumed_api(self) -> None:
        exported = set(re.findall(r"^\s{4}(boot|govern|injectFault|runWatchdog|subscribe|shortHex|snapshot),$", self.kernel, re.MULTILINE))
        self.assertEqual(
            exported,
            {"boot", "govern", "injectFault", "runWatchdog", "subscribe", "shortHex", "snapshot"},
        )
        for member in (
            "Alloy.ADAPTER_CURRENT",
            "Alloy.receipts",
            "Alloy.capsules",
            "Alloy.health",
            "Alloy.identity",
            "Alloy.epoch",
            "Alloy.status",
        ):
            self.assertIn(member, self.app)


if __name__ == "__main__":
    unittest.main()
