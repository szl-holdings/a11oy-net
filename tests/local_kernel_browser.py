#!/usr/bin/env python3
"""Real Chromium/IndexedDB/Web Locks checks on a disposable loopback origin."""
from __future__ import annotations
import functools
import http.server
import json
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass

def main() -> None:
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(ROOT)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f'http://127.0.0.1:{server.server_port}'
    url = origin + '/estate/alloy-os/'
    evidence: dict = {'schema': 'szl.local-kernel-browser/v1', 'production_mutations': False, 'external_network': False}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
            context = browser.new_context(viewport={'width': 375, 'height': 812}, reduced_motion='reduce')
            outgoing: list[str] = []
            def route(request):
                if request.request.url.startswith(origin + '/'):
                    request.continue_()
                else:
                    outgoing.append(request.request.url)
                    request.abort()
            context.route('**/*', route)
            page = context.new_page()
            errors: list[str] = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(url)
            page.wait_for_function("globalThis.Alloy && Alloy.status === 'LOCAL_READY'")
            page.locator('#ktitle').fill('Browser fixture')
            page.locator('#kbody').fill('Private browser fixture; never transmitted')
            page.locator('#ksubmit').click()
            page.wait_for_function('Alloy.receipts.length === 1 && !document.querySelector("#ksubmit").disabled')
            identity = page.evaluate('Alloy.identity.kid')
            assert page.evaluate('Alloy.capsules[0].status') == 'VERIFIED'
            page.locator('#ksubmit').click()
            page.wait_for_function('Alloy.receipts.length === 2 && !document.querySelector("#ksubmit").disabled')
            assert page.evaluate('Alloy.capsules.length') == 1
            assert page.evaluate('Alloy.receipts[1].type') == 'REUSE'
            page.locator('#ktamper').click()
            page.wait_for_function("Alloy.status === 'DEGRADED' && !document.querySelector('#kheal').disabled")
            page.locator('#kheal').click()
            page.wait_for_function("Alloy.status === 'LOCAL_READY' && Alloy.health.healed === 1 && !document.querySelector('#ksubmit').disabled")
            page.locator('#kadapter').select_option('alloy-local-v0')
            page.locator('#ksubmit').click()
            page.wait_for_function('Alloy.health.blocked === 1 && !document.querySelector("#ksubmit").disabled')
            assert page.locator('#kernel-app [role="status"]').inner_text().startswith('DENY')
            page.reload()
            page.wait_for_function("globalThis.Alloy && Alloy.status === 'LOCAL_READY'")
            assert page.evaluate('Alloy.identity.kid') == identity
            assert page.evaluate('Alloy.receipts.length') == 5
            storage = page.evaluate("""async () => {
              const db = await new Promise((resolve,reject) => {const r=indexedDB.open('szl-alloy-local-v1',1);r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});
              const data = await new Promise((resolve,reject) => {const r=db.transaction('state','readonly').objectStore('state').get('kernel');r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});
              db.close(); return {privateExtractable:data.keys.privateKey.extractable,aesExtractable:data.encryptionKey.extractable,plaintextStored:JSON.stringify(data).includes('Private browser fixture; never transmitted')};
            }""")
            assert storage == {'privateExtractable': False, 'aesExtractable': False, 'plaintextStored': False}
            evidence['storage'] = storage
            other = context.new_page()
            other.goto(url)
            other.wait_for_function("globalThis.Alloy && Alloy.status === 'LOCAL_READY'")
            # Start both browser writers concurrently before awaiting their work.
            for index, tab in enumerate((page, other)):
                tab.evaluate("i => {globalThis.pending = Alloy.govern({title:'Concurrent '+i,body:'Local-only '+i,policyClass:'private',adapter:Alloy.ADAPTER_CURRENT});}", index)
            for tab in (page, other):
                assert tab.evaluate('pending').get('decision') == 'ALLOW'
            page.reload(); page.wait_for_function("globalThis.Alloy && Alloy.status === 'LOCAL_READY'")
            assert page.evaluate('Alloy.receipts.length') == 7
            assert page.evaluate('Alloy.capsules.length') == 3
            measurements = []
            for width, height in ((320,568),(375,812),(768,1024),(1440,900)):
                page.set_viewport_size({'width':width,'height':height})
                metrics = page.evaluate("""() => ({width:innerWidth,documentWidth:document.documentElement.scrollWidth,touchTargets:[...document.querySelectorAll('#kernel-app button')].map(e=>({width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height}))})""")
                assert metrics['documentWidth'] <= width + 1, metrics
                assert all(target['width'] >= 44 and target['height'] >= 44 for target in metrics['touchTargets']), metrics
                measurements.append(metrics)
            evidence['viewport_checks'] = measurements
            evidence['restart_identity_preserved'] = True
            evidence['cross_tab_writes_preserved'] = True
            evidence['fault_detected_and_snapshot_restored'] = True
            evidence['stale_adapter_rejected'] = True
            evidence['console_errors'] = errors
            evidence['external_requests_attempted'] = outgoing
            assert not errors, errors
            assert not outgoing, outgoing
            # Separate disposable context proves absent assets are visibly unavailable.
            broken = browser.new_context()
            broken.route('**/kernel.js', lambda route: route.abort())
            failed = broken.new_page(); failed.goto(url)
            failed.wait_for_function("document.querySelector('#kernel-app').textContent.includes('UNAVAILABLE')")
            evidence['missing_kernel_visible'] = True
            broken.close(); context.close(); browser.close()
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)
    print(json.dumps(evidence, sort_keys=True))

if __name__ == '__main__':
    main()
