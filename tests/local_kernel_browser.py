#!/usr/bin/env python3
"""Real Chromium, IndexedDB and Web Locks checks on a disposable loopback origin."""
from __future__ import annotations

import functools
import http.server
import json
import threading
import time
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args: object) -> None:
        pass


def wait_until(page: Page, expression: str, *, timeout_s: float = 8.0) -> None:
    """Poll through CDP without Playwright's CSP-sensitive waitForFunction eval."""
    deadline = time.monotonic() + timeout_s
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            if page.evaluate(expression):
                return
        except Exception as exc:  # page may still be installing its scripts
            last_error = exc
        page.wait_for_timeout(50)
    detail = f"; last evaluation error: {last_error}" if last_error else ""
    raise AssertionError(f"condition did not become true: {expression}{detail}")


def main() -> None:
    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0),
        functools.partial(Handler, directory=str(ROOT)),
    )
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    url = origin + "/estate/alloy-os/"
    evidence: dict[str, object] = {
        "schema": "szl.local-kernel-browser/v1",
        "production_mutations": False,
        "external_network": False,
    }
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
            context = browser.new_context(
                viewport={"width": 375, "height": 812},
                reduced_motion="reduce",
            )
            outgoing: list[str] = []

            def route(request: object) -> None:
                route_url = request.request.url
                if route_url.startswith(origin + "/"):
                    request.continue_()
                else:
                    outgoing.append(route_url)
                    request.abort()

            context.route("**/*", route)
            page = context.new_page()
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(url, wait_until="domcontentloaded")
            wait_until(page, "() => globalThis.Alloy && Alloy.status === 'LOCAL_READY'")

            page.locator("#ktitle").fill("Browser fixture")
            page.locator("#kbody").fill("Private browser fixture; never transmitted")
            page.locator("#ksubmit").click()
            wait_until(
                page,
                "() => Alloy.receipts.length === 1 && !document.querySelector('#ksubmit').disabled",
            )
            identity = page.evaluate("() => Alloy.identity.kid")
            assert page.evaluate("() => Alloy.capsules[0].status") == "VERIFIED"

            page.locator("#ksubmit").click()
            wait_until(
                page,
                "() => Alloy.receipts.length === 2 && !document.querySelector('#ksubmit').disabled",
            )
            assert page.evaluate("() => Alloy.capsules.length") == 1
            assert page.evaluate("() => Alloy.receipts[1].type") == "REUSE"

            page.locator("#ktamper").click()
            wait_until(
                page,
                "() => Alloy.status === 'DEGRADED' && !document.querySelector('#kheal').disabled",
            )
            page.locator("#kheal").click()
            wait_until(
                page,
                "() => Alloy.status === 'LOCAL_READY' && Alloy.health.healed === 1 && !document.querySelector('#ksubmit').disabled",
            )

            page.locator("#kadapter").select_option("alloy-local-v0")
            page.locator("#ksubmit").click()
            wait_until(
                page,
                "() => Alloy.health.blocked === 1 && !document.querySelector('#ksubmit').disabled",
            )
            assert page.locator('#kernel-app [role="status"]').inner_text().startswith("DENY")

            page.reload(wait_until="domcontentloaded")
            wait_until(page, "() => globalThis.Alloy && Alloy.status === 'LOCAL_READY'")
            assert page.evaluate("() => Alloy.identity.kid") == identity
            assert page.evaluate("() => Alloy.receipts.length") == 5
            storage = page.evaluate(
                """async () => {
                  const db = await new Promise((resolve, reject) => {
                    const request = indexedDB.open('szl-alloy-local-v1', 1);
                    request.onsuccess = () => resolve(request.result);
                    request.onerror = () => reject(request.error);
                  });
                  const data = await new Promise((resolve, reject) => {
                    const request = db.transaction('state', 'readonly')
                      .objectStore('state').get('kernel');
                    request.onsuccess = () => resolve(request.result);
                    request.onerror = () => reject(request.error);
                  });
                  db.close();
                  return {
                    privateExtractable: data.keys.privateKey.extractable,
                    aesExtractable: data.encryptionKey.extractable,
                    plaintextStored: JSON.stringify(data).includes(
                      'Private browser fixture; never transmitted'
                    ),
                  };
                }"""
            )
            assert storage == {
                "privateExtractable": False,
                "aesExtractable": False,
                "plaintextStored": False,
            }
            evidence["storage"] = storage

            other = context.new_page()
            other.goto(url, wait_until="domcontentloaded")
            wait_until(other, "() => globalThis.Alloy && Alloy.status === 'LOCAL_READY'")
            for index, tab in enumerate((page, other)):
                tab.evaluate(
                    """index => {
                      globalThis.pending = Alloy.govern({
                        title: 'Concurrent ' + index,
                        body: 'Local-only ' + index,
                        policyClass: 'private',
                        adapter: Alloy.ADAPTER_CURRENT,
                      });
                    }""",
                    index,
                )
            for tab in (page, other):
                assert tab.evaluate("() => pending")["decision"] == "ALLOW"

            page.reload(wait_until="domcontentloaded")
            wait_until(page, "() => globalThis.Alloy && Alloy.status === 'LOCAL_READY'")
            assert page.evaluate("() => Alloy.receipts.length") == 7
            assert page.evaluate("() => Alloy.capsules.length") == 3

            measurements: list[dict[str, object]] = []
            for width, height in ((320, 568), (375, 812), (768, 1024), (1440, 900)):
                page.set_viewport_size({"width": width, "height": height})
                metrics = page.evaluate(
                    """() => ({
                      width: innerWidth,
                      documentWidth: document.documentElement.scrollWidth,
                      touchTargets: [...document.querySelectorAll('#kernel-app button')]
                        .map(element => ({
                          width: element.getBoundingClientRect().width,
                          height: element.getBoundingClientRect().height,
                        })),
                    })"""
                )
                assert metrics["documentWidth"] <= width + 1, metrics
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

            broken = browser.new_context()
            broken.route("**/kernel.js", lambda route: route.abort())
            failed = broken.new_page()
            failed.goto(url, wait_until="domcontentloaded")
            wait_until(
                failed,
                "() => document.querySelector('#kernel-app')?.textContent.includes('UNAVAILABLE')",
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
