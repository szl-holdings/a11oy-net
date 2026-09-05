#!/usr/bin/env python3
"""Bind the Web-Locked local kernel to the current proof UI and static contract."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "estate" / "alloy-os" / "app.js"
TEST = ROOT / "tests" / "test_alloy_local_kernel.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    app = APP.read_text(encoding="utf-8")
    app = replace_once(
        app,
        '''      const health = await kernel.runWatchdog();
      state.message = health.ledgerReplayable ? "Watchdog complete — local chain replayable." : "Watchdog complete — degraded state remains.";
      state.tone = health.ledgerReplayable ? "ok" : "bad";
''',
        '''      const outcome = await kernel.runWatchdog();
      const verified = outcome.verified === true && kernel.health.ledgerReplayable === true;
      state.message = verified
        ? `Watchdog complete — restored ${outcome.restored} authenticated local snapshot(s).`
        : "Watchdog complete — degraded state remains.";
      state.tone = verified ? "ok" : "bad";
''',
        "watchdog UI result contract",
    )
    APP.write_text(app, encoding="utf-8")

    test_source = r'''# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "estate" / "alloy-os" / "index.html"
KERNEL = ROOT / "estate" / "alloy-os" / "kernel.js"
APP = ROOT / "estate" / "alloy-os" / "app.js"


class AlloyLocalKernelContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.page = PAGE.read_text(encoding="utf-8")
        cls.kernel = KERNEL.read_text(encoding="utf-8")
        cls.app = APP.read_text(encoding="utf-8")

    def test_page_loads_kernel_before_the_view_controller(self) -> None:
        self.assertTrue(KERNEL.is_file())
        kernel_tag = '<script src="./kernel.js"></script>'
        app_tag = '<script src="./app.js"></script>'
        self.assertIn(kernel_tag, self.page)
        self.assertIn(app_tag, self.page)
        self.assertLess(self.page.index(kernel_tag), self.page.index(app_tag))

    def test_private_keys_are_nonextractable_and_persisted_as_crypto_keys(self) -> None:
        for marker in (
            "generateKey({ name: 'AES-GCM', length: 256 }, false",
            "generateKey({ name: 'ECDSA', namedCurve: 'P-256' }, false",
            "state.keys.privateKey.extractable !== false",
            "state.encryptionKey.extractable !== false",
            "await crypto.subtle.exportKey('spki', keys.publicKey)",
        ):
            self.assertIn(marker, self.kernel)
        for forbidden in ("privateJwk", "signingPrivate", "exportKey('pkcs8'", "exportKey('jwk', keys.privateKey"):
            self.assertNotIn(forbidden, self.kernel)

    def test_cross_tab_writer_serialization_fails_closed_without_web_locks(self) -> None:
        for marker in (
            "root.navigator?.locks",
            "locks.request('szl-alloy-local-v1-writer'",
            "Secure WebCrypto and cross-tab Web Locks are required",
            "const state = await store.load();",
            "const before = await verify(state);",
            "const result = await operation(state, before);",
            "const after = await verify(state);",
            "await store.save(state);",
        ):
            self.assertIn(marker, self.kernel)
        self.assertLess(self.kernel.index("const state = await store.load();"), self.kernel.index("await store.save(state);"))
        self.assertLess(self.kernel.index("await store.save(state);"), self.kernel.index("present(state, after);"))

    def test_local_state_is_hard_bounded_without_silent_eviction(self) -> None:
        for marker in (
            "const MAX_RECEIPTS = 1024;",
            "const MAX_CAPSULES = 128;",
            "state.receipts.length > MAX_RECEIPTS",
            "state.capsules.length > MAX_CAPSULES",
            "state.receipts.length >= MAX_RECEIPTS",
            "state.capsules.length >= MAX_CAPSULES",
            "nothing was evicted",
        ):
            self.assertIn(marker, self.kernel)

    def test_chain_capsules_and_verified_snapshots_are_bound(self) -> None:
        for marker in (
            "state.epoch !== state.receipts.length",
            "receipt.prev !== previous",
            "crypto.subtle.verify({ name: 'ECDSA', hash: 'SHA-256' }",
            "seals.size !== state.capsules.length",
            "await cipherHash(backup) !== checked.seals.get(capsule.digest)",
            "Restored only a verified local ciphertext snapshot",
        ):
            self.assertIn(marker, self.kernel)

    def test_kernel_has_no_network_or_dynamic_code_escape(self) -> None:
        for forbidden in (
            "fetch(",
            "XMLHttpRequest",
            "sendBeacon",
            "WebSocket",
            "EventSource",
            "eval(",
            "new Function",
            "setInterval",
            "localStorage",
            "sessionStorage",
            "document.cookie",
            "http://",
            "https://",
        ):
            self.assertNotIn(forbidden, self.kernel, forbidden)

    def test_current_ui_consumes_the_verified_watchdog_result(self) -> None:
        for marker in (
            "const outcome = await kernel.runWatchdog();",
            "outcome.verified === true",
            "kernel.health.ledgerReplayable === true",
            "authenticated local snapshot(s)",
        ):
            self.assertIn(marker, self.app)


if __name__ == "__main__":
    unittest.main(verbosity=2)
'''
    TEST.write_text(test_source.strip() + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
