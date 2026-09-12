#!/usr/bin/env python3
"""Real Chromium/IndexedDB/Web Locks checks on a disposable loopback origin."""
from __future__ import annotations

import functools
import http.server
import json
import threading
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args: Any) -> None:
        pass


def wait_for_js(page: Page, callback: str, *, timeout_seconds: float = 15.0) -> None:
    """Poll a page-owned predicate without weakening the document CSP."""

    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            if page.evaluate(callback) is True:
                return
        except Exception as exc:  # Page boot can briefly race script loading.
            last_error = exc
        page.wait_for_timeout(50)
    detail = f"; last error: {last_error}" if last_error else ""
    raise AssertionError(f"browser predicate did not converge: {callback}{detail}")


def main() -> None:
    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(Handler, directory=str(ROOT))
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    url = origin + "/estate/alloy-os/"
    evidence: dict[str, Any] = {
        "schema": "szl.local-kernel-browser/v1",
        "production_mutations": False,
        "external_network": False,
        "production_csp_weakened": False,
    }
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
            context = browser.new_context(
                viewport={"width": 375, "height": 812}, reduced_motion="reduce"
            )
            outgoing: list[str] = []

            def route(request: Any) -> None:
                if request.request.url.startswith(origin + "/"):
                    request.continue_()
                else:
                    outgoing.append(request.request.url)
                    request.abort()

            context.route("**/*", route)
            page = context.new_page()
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(url)
            wait_for_js(
                page,
                "() => Boolean(globalThis.Alloy && Alloy.status === 'LOCAL_READY' && document.querySelector('#kproof'))",
            )
            assert not errors, errors
            page.locator('.osdock [data-open="kernel"]').click()
            page.locator("#ktitle").fill("Browser fixture")
            page.locator("#kbody").fill(
                "Private browser fixture; never transmitted"
            )
            # Navigation and the busy render must preserve the user's draft.
            page.locator('.osdock [data-open="ledger"]').click()
            page.locator('.osdock [data-open="kernel"]').click()
            assert page.locator("#ktitle").input_value() == "Browser fixture"
            assert page.locator("#kbody").input_value() == "Private browser fixture; never transmitted"
            page.locator("#ksubmit").click()
            wait_for_js(
                page,
                "() => Alloy.receipts.length === 1 && !document.querySelector('#ksubmit').disabled",
            )
            identity = page.evaluate("Alloy.identity.kid")
            assert page.evaluate("Alloy.capsules[0].status") == "VERIFIED"
            assert page.evaluate("Alloy.capsules[0].title") == "Browser fixture"
            page.locator("#ksubmit").click()
            wait_for_js(
                page,
                "() => Alloy.receipts.length === 2 && !document.querySelector('#ksubmit').disabled",
            )
            assert page.evaluate("Alloy.capsules.length") == 1
            assert page.evaluate("Alloy.receipts[1].type") == "REUSE"
            page.locator("#ktamper").click()
            wait_for_js(
                page,
                "() => Alloy.status === 'DEGRADED' && !document.querySelector('#kheal').disabled",
            )
            page.locator("#kheal").click()
            wait_for_js(
                page,
                "() => Alloy.status === 'LOCAL_READY' && Alloy.health.healed === 1 && !document.querySelector('#ksubmit').disabled",
            )

            # Measure a real denial transition from the current verified state.
            # The counter is cumulative by contract, so assuming an absolute
            # starting value makes the browser test order-dependent.
            blocked_before = int(page.evaluate("Alloy.health.blocked"))
            receipts_before_denial = int(page.evaluate("Alloy.receipts.length"))
            page.locator("#kadapter").select_option("alloy-local-v0")
            page.locator('.osdock [data-open="mesh"]').click()
            assert page.locator("#kadapter").input_value() == "alloy-local-v0"
            page.locator("#ksubmit").click()
            wait_for_js(
                page,
                "() => !document.querySelector('#ksubmit').disabled",
            )
            assert page.evaluate("Alloy.health.blocked") == blocked_before + 1
            assert page.evaluate("Alloy.receipts.length") == receipts_before_denial + 1
            assert page.evaluate("Alloy.receipts.at(-1).type") == "DENY"
            assert page.locator('#kernel-app [role="status"]').inner_text().startswith(
                "DENY"
            )

            page.reload()
            wait_for_js(
                page,
                "() => Boolean(globalThis.Alloy && Alloy.status === 'LOCAL_READY')",
            )
            assert page.evaluate("Alloy.identity.kid") == identity
            assert page.evaluate("Alloy.receipts.length") == 5
            storage = page.evaluate(
                """async () => {
                  const db = await new Promise((resolve,reject) => {
                    const request=indexedDB.open('szl-alloy-local-v1',1);
                    request.onsuccess=()=>resolve(request.result);
                    request.onerror=()=>reject(request.error);
                  });
                  const data = await new Promise((resolve,reject) => {
                    const request=db.transaction('state','readonly').objectStore('state').get('kernel');
                    request.onsuccess=()=>resolve(request.result);
                    request.onerror=()=>reject(request.error);
                  });
                  db.close();
                  const capsule = data.capsules[0];
                  const unhex = value => Uint8Array.from(value.match(/../g), byte => parseInt(byte, 16));
                  const plain = await crypto.subtle.decrypt({
                    name:'AES-GCM', iv:unhex(capsule.iv),
                    additionalData:new TextEncoder().encode(capsule.digest), tagLength:128
                  }, data.encryptionKey, unhex(capsule.ciphertext));
                  const payload = JSON.parse(new TextDecoder().decode(plain));
                  return {
                    privateExtractable:data.keys.privateKey.extractable,
                    aesExtractable:data.encryptionKey.extractable,
                    plaintextStored:JSON.stringify(data).includes('Private browser fixture; never transmitted'),
                    submittedPayloadPreserved:payload.title === 'Browser fixture' && payload.body === 'Private browser fixture; never transmitted'
                  };
                }"""
            )
            assert storage == {
                "privateExtractable": False,
                "aesExtractable": False,
                "plaintextStored": False,
                "submittedPayloadPreserved": True,
            }
            evidence["storage"] = storage
            other = context.new_page()
            other.goto(url)
            wait_for_js(
                other,
                "() => Boolean(globalThis.Alloy && Alloy.status === 'LOCAL_READY')",
            )
            # Start both browser writers concurrently before awaiting their work.
            for index, tab in enumerate((page, other)):
                tab.evaluate(
                    """index => {
                      globalThis.pending = Alloy.govern({
                        title:'Concurrent '+index,
                        body:'Local-only '+index,
                        policyClass:'private',
                        adapter:Alloy.ADAPTER_CURRENT
                      });
                    }""",
                    index,
                )
            for tab in (page, other):
                assert tab.evaluate("pending").get("decision") == "ALLOW"
            page.reload()
            wait_for_js(
                page,
                "() => Boolean(globalThis.Alloy && Alloy.status === 'LOCAL_READY')",
            )
            assert page.evaluate("Alloy.receipts.length") == 7
            assert page.evaluate("Alloy.capsules.length") == 3
            # Exercise the new Command path as well as individual kernel controls.
            page.locator("#kproof").click()
            wait_for_js(page, "() => Alloy.receipts.length === 12 && !document.querySelector('#kproof').disabled")
            assert page.evaluate("Alloy.receipts.slice(-5).map(receipt => receipt.type)") == [
                "SEAL", "REUSE", "DENY", "FAULT_TEST", "RESTORE"
            ]
            assert page.evaluate("Alloy.stages.length === 8 && Alloy.stages.every(stage => stage.fired)")
            assert page.evaluate("Alloy.energy.label") == "MODELED"
            assert page.evaluate("Alloy.status") == "LOCAL_READY"
            evidence["command_proof_completed"] = True
            # Measure every app's controls, including the new close buttons.
            for app in ("ledger", "capsules", "energy", "alignment", "kernel", "honesty"):
                page.locator(f'.osdock [data-open="{app}"]').click()
            measurements = []
            for width, height in ((320, 568), (375, 812), (768, 1024), (1440, 900)):
                page.set_viewport_size({"width": width, "height": height})
                metrics = page.evaluate(
                    """() => ({
                      width:innerWidth,
                      documentWidth:document.documentElement.scrollWidth,
                      windows:[...document.querySelectorAll('.oswin')].map(element=>({
                        left:element.getBoundingClientRect().left,
                        right:element.getBoundingClientRect().right,
                        clientWidth:element.clientWidth,
                        scrollWidth:element.scrollWidth
                      })),
                      touchTargets:[...document.querySelectorAll('#kernel-app button')].map(element=>({
                        width:element.getBoundingClientRect().width,
                        height:element.getBoundingClientRect().height
                      }))
                    })"""
                )
                assert metrics["documentWidth"] <= width + 1, metrics
                assert all(
                    window["left"] >= -1 and window["right"] <= width + 1
                    and window["scrollWidth"] <= window["clientWidth"] + 1
                    for window in metrics["windows"]
                ), metrics
                assert all(
                    target["width"] >= 44 and target["height"] >= 44
                    for target in metrics["touchTargets"]
                ), metrics
                measurements.append(metrics)
            evidence["viewport_checks"] = measurements
            evidence["restart_identity_preserved"] = True
            evidence["cross_tab_writes_preserved"] = True
            evidence["fault_detected_and_snapshot_restored"] = True
            evidence["stale_adapter_rejected"] = True
            evidence["console_errors"] = errors
            evidence["external_requests_attempted"] = outgoing
            assert not errors, errors
            assert not outgoing, outgoing
            # Separate disposable context proves absent assets are visibly unavailable.
            broken = browser.new_context()
            broken.route("**/kernel.js", lambda route: route.abort())
            failed = broken.new_page()
            failed.goto(url)
            wait_for_js(
                failed,
                "() => Boolean(document.querySelector('#kernel-app') && document.querySelector('#kernel-app').textContent.includes('UNAVAILABLE'))",
            )
            evidence["missing_kernel_visible"] = True
            broken.close()
            context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    print(json.dumps(evidence, sort_keys=True))


if __name__ == "__main__":
    main()
