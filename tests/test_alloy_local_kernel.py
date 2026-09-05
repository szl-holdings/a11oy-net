# SPDX-License-Identifier: Apache-2.0
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
SNAPSHOT = ROOT / "estate" / "alloy-os" / "live.json"


def test_local_kernel_files_are_complete_and_ordered() -> None:
    html = PAGE.read_text(encoding="utf-8")
    assert KERNEL.is_file()
    assert APP.is_file()
    assert SNAPSHOT.is_file()
    assert html.count('src="./kernel.js"') == 1
    assert html.count('src="./app.js"') == 1
    assert html.index('src="./kernel.js"') < html.index('src="./app.js"')


def test_kernel_is_browser_local_and_exposes_the_ui_contract() -> None:
    source = KERNEL.read_text(encoding="utf-8")
    for required in (
        'const ADAPTER_CURRENT = "alloy-local-v1"',
        'name: "AES-GCM", length: 256',
        'name: "ECDSA", namedCurve: "P-256"',
        'crypto.subtle.digest("SHA-256"',
        'indexedDB.open(DB_NAME, DB_VERSION)',
        "subscribe(callback)",
        "shortHex(value)",
        "boot,",
        "govern,",
        "injectFault,",
        "runWatchdog,",
        "window.Alloy = Alloy",
    ):
        assert required in source
    for network_primitive in (
        "fetch(",
        "XMLHttpRequest",
        "WebSocket",
        "EventSource",
        "sendBeacon",
        "document.cookie",
        "localStorage",
        "sessionStorage",
        "eval(",
    ):
        assert network_primitive not in source
    assert "privateJwk" not in source.split("return {", 1)[-1].split("};", 1)[0]


def test_kernel_javascript_parses_when_node_is_available() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is unavailable on this runner")
    result = subprocess.run(
        [node, "--check", str(KERNEL)],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr


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


def test_ui_consumes_only_the_bounded_same_origin_snapshot() -> None:
    source = APP.read_text(encoding="utf-8")
    assert 'loadJson("./live.json")' in source
    assert 'loadJson("/estate.json")' not in source
    assert 'loadJson("/spaces.json")' not in source
    assert 'loadJson("/models.json")' not in source
    assert 'credentials: "same-origin"' in source
    assert 'role="status" aria-live="polite"' in source
    assert 'type="button" class="button" id="ktamper"' in source
