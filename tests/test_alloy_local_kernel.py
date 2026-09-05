# SPDX-License-Identifier: Apache-2.0
"""Contracts for the browser-local kernel; none grants remote or provider authority."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "estate" / "alloy-os" / "index.html"
APP = ROOT / "estate" / "alloy-os" / "app.js"
KERNEL = ROOT / "estate" / "alloy-os" / "kernel.js"
CSS = ROOT / "estate" / "alloy-os" / "alloy.css"
SNAPSHOT = ROOT / "estate" / "alloy-os" / "live.json"
NODE_TEST = ROOT / "tests" / "local-kernel.test.cjs"
BROWSER_TEST = ROOT / "tests" / "local_kernel_browser.py"
WORKFLOW = ROOT / ".github" / "workflows" / "local-kernel-contract.yml"


def test_local_kernel_assets_are_complete_and_ordered() -> None:
    html = PAGE.read_text(encoding="utf-8")
    for path in (APP, KERNEL, CSS, SNAPSHOT, NODE_TEST, BROWSER_TEST, WORKFLOW):
        assert path.is_file(), path
    assert html.count('src="./kernel.js"') == 1
    assert html.count('src="./app.js"') == 1
    assert html.index('src="./kernel.js"') < html.index('src="./app.js"')
    assert "script-src 'self'" in html
    assert "connect-src 'self'" in html
    assert "cross-tab Web Locks" in html
    assert "This page does not observe product runtime health" in html


def test_kernel_is_local_bounded_and_fail_closed() -> None:
    source = KERNEL.read_text(encoding="utf-8")
    for required in (
        "const ADAPTER = 'alloy-local-v1'",
        "const MAX_RECEIPTS = 1024",
        "const MAX_CAPSULES = 128",
        "name: 'AES-GCM', length: 256",
        "name: 'ECDSA', namedCurve: 'P-256'",
        "crypto.subtle.digest('SHA-256'",
        "root.indexedDB.open('szl-alloy-local-v1', 1)",
        "root.navigator?.locks",
        "extractable !== false",
        "Local ledger capacity reached",
        "Local capsule capacity reached",
        "else root.Alloy = createKernel",
    ):
        assert required in source
    for prohibited in (
        "fetch(",
        "XMLHttpRequest",
        "WebSocket",
        "EventSource",
        "sendBeacon",
        "document.cookie",
        "localStorage",
        "sessionStorage",
        "eval(",
        "new Function",
        "setInterval",
    ):
        assert prohibited not in source


def test_javascript_parses_and_node_contract_is_present() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is unavailable on this runner")
    for path in (KERNEL, APP):
        result = subprocess.run(
            [node, "--check", str(path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
        assert result.returncode == 0, result.stderr
    node_test = NODE_TEST.read_text(encoding="utf-8")
    assert "two local instances serialize writes" in node_test
    assert "missing Web Locks is unavailable" in node_test
    assert "receipt tampering is rejected" in node_test


def test_alignment_snapshot_is_measured_and_non_mutating() -> None:
    value = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert value["schema"] == "szl.alloy-local-alignment/v1"
    assert value["truth_label"] == "MEASURED_PUBLIC_INVENTORY"
    assert value["scope"] == "PUBLIC_PARTIAL"
    assert value["runtime_probes_performed"] is False
    assert value["provider_mutations_performed"] is False
    assert value["credential_values_recorded"] is False
    assert value["product_runtime_probe"]["state"] == "UNAVAILABLE"
    assert value["lambda"] == "Conjecture 1 OPEN"
    assert value["inventory"] == {
        "github_archived_repositories": 34,
        "github_public_repositories": 117,
        "huggingface_collections": 21,
        "huggingface_datasets": 33,
        "huggingface_models": 44,
        "huggingface_spaces": 16,
        "private_github_inventory": "UNAVAILABLE",
    }
    assert [row["url"] for row in value["alignment"]] == [
        "https://a-11-oy.com",
        "https://a11oy.net",
        "https://github.com/szl-holdings",
        "https://huggingface.co/SZLHOLDINGS",
    ]


def test_ui_and_browser_contract_respect_csp_and_same_origin() -> None:
    source = APP.read_text(encoding="utf-8")
    assert 'loadJson("./live.json")' in source
    for stale in ('loadJson("/estate.json")', 'loadJson("/spaces.json")', 'loadJson("/models.json")'):
        assert stale not in source
    assert 'credentials: "omit"' in source
    assert 'role="status" aria-live="polite"' in source
    assert 'maxlength="32768"' in source
    browser = BROWSER_TEST.read_text(encoding="utf-8")
    assert "wait_for_function" not in browser
    assert "wait_until(page" in browser
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "sha256:640d578aae63cfb632461d1b0aecb01414e4e020864ac3dd45a868dc0eff3078" in workflow
    assert "node --test tests/local-kernel.test.cjs" in workflow
    assert "python tests/local_kernel_browser.py" in workflow
