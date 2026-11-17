#!/usr/bin/env python3
"""Measured proof-registry mobile touch geometry, from the actual checked-out HTML.

This uses a disposable loopback HTTP server and blocks every off-origin fetch.
No claims, credentials, or production services are modified.
"""
from __future__ import annotations

import functools
import http.server
import json
import os
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(os.environ.get("SZL_PROOF_TOUCH_ROOT") or Path(__file__).resolve().parents[1]).resolve()
SELECTOR = ".index-catalog li > a, .foot-links > a, .stack-card > a.stack-link"
MIN_TARGET = 44

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args) -> None:
        pass

def inspect(page):
    return page.eval_on_selector_all(SELECTOR, """nodes => nodes.map(e => {
      const r=e.getBoundingClientRect(),s=getComputedStyle(e);
      return {name:(e.textContent||'').trim().slice(0,40), width:r.width,
        height:r.height, display:s.display, visibility:s.visibility};
    }).filter(e=>e.width>0 && e.height>0 && e.display!=='none' && e.visibility!=='hidden')""")

def main() -> None:
    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(ROOT)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
            try:
                for width, height in ((320, 740), (390, 844), (430, 932), (1440, 900)):
                    context = browser.new_context(
                        viewport={"width": width, "height": height}, reduced_motion="reduce")
                    context.route("**/*", lambda route: (
                        route.continue_() if route.request.url.startswith(origin + "/")
                        else route.abort()))
                    page = context.new_page()
                    response = page.goto(origin + "/", wait_until="domcontentloaded", timeout=20000)
                    assert response is not None and response.status == 200, "source unavailable"
                    page.wait_for_timeout(100)
                    assert page.locator('#stack a[href="https://huggingface.co/spaces/SZLHOLDINGS/anatomy"]').count() == 0
                    assert page.locator('#stack a[href="https://github.com/szl-holdings/anatomy/commit/02d9dbbac66993015005e423f2123dde3dc3b4a7"]').count() == 1
                    assert page.locator('#stack a[href="https://szlholdings-a11oy.hf.space/holographic"]').count() == 1
                    assert page.locator("#stack .stack-card").filter(has_text="Living anatomy").locator(".stack-truth").inner_text() == "REPORTED"
                    assert page.locator("#stack .stack-card").filter(has_text="Holographic operations").locator(".stack-truth").inner_text() == "REPORTED"
                    assert "ANATOMY V5" not in page.locator("#stack").inner_text()
                    body_width = page.evaluate(
                        "() => Math.max(document.documentElement.scrollWidth, document.body.scrollWidth)")
                    assert body_width <= width + 1, f"horizontal overflow at {width}px: {body_width}"
                    links = inspect(page)
                    assert len(links) >= 30, f"not enough actionable links in source: {len(links)}"
                    if width <= 430:
                        failures = [r for r in links
                                    if r["width"] + .5 < MIN_TARGET or r["height"] + .5 < MIN_TARGET]
                        assert not failures, f"undersized targets at {width}px: {json.dumps(failures[:8])}"
                    else:
                        assert any(r["height"] < MIN_TARGET for r in links), (
                            "desktop density unintentionally expanded")
                    print(json.dumps({"viewport": width, "targets": len(links),
                                      "horizontal_overflow": max(0, body_width-width),
                                      "minimum_height": round(min(x["height"] for x in links),1)}))
                    context.close()
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)

if __name__ == "__main__":
    main()
