# SPDX-License-Identifier: Apache-2.0
"""Static contracts for the browser-only Alloy local kernel."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KERNEL = ROOT / "estate" / "alloy-os" / "kernel.js"
INDEX = ROOT / "estate" / "alloy-os" / "index.html"
APP = ROOT / "estate" / "alloy-os" / "app.js"


def test_alloy_kernel_asset_exists_and_is_loaded_before_the_ui() -> None:
    source = KERNEL.read_text(encoding="utf-8")
    page = INDEX.read_text(encoding="utf-8")
    assert source
    assert '<script src="./kernel.js"></script>' in page
    assert page.index('./kernel.js') < page.index('./app.js')
    assert 'typeof Alloy==="undefined"' in APP


def test_kernel_uses_real_local_cryptographic_primitives() -> None:
    source = KERNEL.read_text(encoding="utf-8")
    for contract in (
        'name: "AES-GCM", length: 256',
        'name: "ECDSA", namedCurve: "P-256"',
        'crypto.subtle.digest("SHA-256"',
        'crypto.subtle.sign(',
        'crypto.subtle.verify(',
        'crypto.subtle.encrypt(',
        'crypto.subtle.decrypt(',
        'indexedDB.open(DB_NAME, DB_VERSION)',
        'database.createObjectStore("capsules"',
        'database.createObjectStore("receipts"',
        'database.createObjectStore("snapshots"',
    ):
        assert contract in source


def test_kernel_is_local_only_and_grants_no_provider_authority() -> None:
    source = KERNEL.read_text(encoding="utf-8")
    for prohibited in (
        "fetch(",
        "XMLHttpRequest",
        "WebSocket",
        "sendBeacon",
        "localStorage",
        "sessionStorage",
        "document.cookie",
        "eval(",
        "Function(",
        "api.github.com",
        "huggingface.co",
        "a-11-oy.com",
        "a11oy.com",
    ):
        assert prohibited not in source
    assert 'policyClass !== "private"' in source
    assert 'adapter !== ADAPTER_CURRENT' in source
    assert 'decision: "BLOCK"' in source


def test_receipts_are_hash_chained_signed_and_replay_verified() -> None:
    source = KERNEL.read_text(encoding="utf-8")
    for contract in (
        'prevDigest: previous',
        'payloadDigest: await sha256(canonical(payload))',
        'const digest = await sha256(canonical(core))',
        'receipt.prevDigest !== previous',
        'await verifyReceiptChain()',
        'ledgerReplayable',
    ):
        assert contract in source


def test_one_byte_fault_probe_has_snapshot_and_heal_path() -> None:
    source = KERNEL.read_text(encoding="utf-8")
    for contract in (
        "bytes[0] ^= 1",
        'capsule.status = "TAMPERED"',
        'type="button" id="ktamper"',
        "latestSnapshot(capsule.id)",
        'status: "SEALED", healedAt:',
        'addReceipt("HEAL"',
    ):
        haystack = source + APP.read_text(encoding="utf-8")
        assert contract in haystack


def test_private_key_and_aes_key_are_persisted_nonextractable() -> None:
    source = KERNEL.read_text(encoding="utf-8")
    assert 'name: "AES-GCM", length: 256 },\n      false,' in source
    assert 'privateJwk,\n      { name: "ECDSA", namedCurve: "P-256" },\n      false,' in source
    assert 'await put("meta", { key: "keys", value: created })' in source
    assert "exportKey(\"jwk\", generated.privateKey)" in source
    assert "privateJwk" not in source.split('return {\n      encryptionKey,', 1)[1].split("};", 1)[0]
