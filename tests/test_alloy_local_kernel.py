# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "estate" / "alloy-os" / "index.html"
KERNEL = ROOT / "estate" / "alloy-os" / "kernel.js"
APP = ROOT / "estate" / "alloy-os" / "app.js"


class AlloyLocalKernelContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = INDEX.read_text(encoding="utf-8")
        cls.kernel = KERNEL.read_text(encoding="utf-8")
        cls.app = APP.read_text(encoding="utf-8")

    def test_page_loads_real_kernel_before_view_controller(self) -> None:
        kernel_tag = '<script src="./kernel.js"></script>'
        app_tag = '<script src="./app.js"></script>'
        self.assertIn(kernel_tag, self.index)
        self.assertIn(app_tag, self.index)
        self.assertLess(self.index.index(kernel_tag), self.index.index(app_tag))
        self.assertIn("script-src 'self'", self.index)

    def test_kernel_is_bounded_first_party_and_network_silent(self) -> None:
        self.assertLess(KERNEL.stat().st_size, 25_000)
        for forbidden in (
            "fetch(",
            "XMLHttpRequest",
            "WebSocket",
            "EventSource",
            "sendBeacon",
            "localStorage",
            "sessionStorage",
            "eval(",
            "new Function",
        ):
            self.assertNotIn(forbidden, self.kernel, forbidden)
        self.assertIn('"use strict";', self.kernel)
        self.assertIn('Object.defineProperty(globalThis, "Alloy"', self.kernel)

    def test_non_extractable_webcrypto_keys_and_algorithms_are_explicit(self) -> None:
        self.assertRegex(
            self.kernel,
            re.compile(
                r'generateKey\(\s*\{\s*name:\s*"ECDSA",\s*namedCurve:\s*"P-256"\s*\},\s*false,',
                re.DOTALL,
            ),
        )
        self.assertRegex(
            self.kernel,
            re.compile(
                r'generateKey\(\s*\{\s*name:\s*"AES-GCM",\s*length:\s*256\s*\},\s*false,',
                re.DOTALL,
            ),
        )
        for marker in (
            '"SHA-256"',
            '"ECDSA-P256-SHA256"',
            '"AES-256-GCM"',
            "additionalData:",
            "tagLength: 128",
        ):
            self.assertIn(marker, self.kernel)

    def test_receipts_are_hash_chained_signed_and_reverified(self) -> None:
        for marker in (
            'const GENESIS = "sha256:" + "0".repeat(64)',
            "prev_digest:",
            "payload_digest:",
            "crypto.subtle.sign(",
            "crypto.subtle.verify(",
            "verifyLedger",
            "receipt.seq !== index",
            "receipt.prev_digest !== previousDigest",
        ):
            self.assertIn(marker, self.kernel)

    def test_indexeddb_snapshot_fault_and_heal_contract_is_real(self) -> None:
        for marker in (
            "indexedDB.open(",
            "structuredClone",
            "last_good",
            "sealSnapshot",
            "injectFault",
            "^= 0x01",
            "runWatchdog",
            "restoreSnapshot",
            '"LOCAL_SNAPSHOT_HEAL"',
        ):
            self.assertIn(marker, self.kernel)

    def test_adapter_and_policy_fail_closed_before_encryption(self) -> None:
        self.assertIn('const ADAPTER_CURRENT = "alloy-local-v1"', self.kernel)
        self.assertIn('return block("ADAPTER_NOT_PINNED"', self.kernel)
        self.assertIn('return block("POLICY_CLASS_NOT_LOCAL_PRIVATE"', self.kernel)
        self.assertLess(
            self.kernel.index("if (adapter !== ADAPTER_CURRENT)"),
            self.kernel.index("const capsule = await makeCapsule"),
        )
        self.assertIn("Alloy.ADAPTER_CURRENT", self.app)
        self.assertIn("Alloy.govern(", self.app)
        self.assertIn("Alloy.runWatchdog()", self.app)


if __name__ == "__main__":
    unittest.main(verbosity=2)
