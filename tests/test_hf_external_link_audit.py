# SPDX-License-Identifier: Apache-2.0
"""Offline anti-overclaim tests for the external Hugging Face link auditor."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import urllib.error

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "audit_hf_external_links.py"
spec = importlib.util.spec_from_file_location("hf_external_links", SOURCE)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class Response:
    status = 200

    def __init__(self, url):
        self.url = url

    def geturl(self):
        return self.url

    def read(self, _max_bytes):
        return b"<html>"

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class Opener:
    def __init__(self, head, get):
        self.head = head
        self.get = get
        self.methods = []

    def open(self, request, timeout):
        self.methods.append(request.get_method())
        code = self.head if request.get_method() == "HEAD" else self.get
        if code != 200:
            raise urllib.error.HTTPError(request.full_url, code, "not public", {}, None)
        return Response(request.full_url)


class ExternalLinks(unittest.TestCase):
    def test_allowlisted_https_only(self):
        for url in ("https://huggingface.co/SZLHOLDINGS/a11oy",
                    "https://szlholdings-a11oy.hf.space/path"):
            self.assertTrue(audit.allowed_url(url))
        for url in ("http://huggingface.co/a", "https://huggingface.co.evil.test/a",
                    "https://evil.test/a", "https://hf.space/a",
                    "https://x:hunter2@huggingface.co/x"):
            self.assertFalse(audit.allowed_url(url))

    def test_signed_or_sensitive_queries_are_withheld(self):
        self.assertEqual(
            audit.public_url("https://huggingface.co/SZLHOLDINGS/a?token=secret"),
            ("https://huggingface.co/SZLHOLDINGS/a", True),
        )
        self.assertEqual(
            audit.probe("https://huggingface.co/a?token=secret")["status"],
            "WITHHELD_UNSAFE_URL",
        )

    def test_head_405_and_404_fallback_to_get(self):
        for head_code in (404, 405, 501):
            opener = Opener(head=head_code, get=200)
            outcome = audit.probe("https://x.hf.space/readyz", opener=opener)
            self.assertEqual(outcome["status"], "HTTP_REACHABLE_UNVERIFIED")
            self.assertEqual(opener.methods, ["HEAD", "GET"])

    def test_actual_denial_not_marked_broken_or_green(self):
        for code, expected in ((401, "ACCESS_REQUIRED"), (403, "ACCESS_REQUIRED"),
                               (404, "RESTRICTED_OR_MISSING")):
            result = audit.probe("https://x.hf.space/elite",
                                 opener=Opener(head=code, get=code))
            self.assertEqual(result["status"], expected)

    def test_rate_limit_not_retried(self):
        opener = Opener(head=429, get=200)
        self.assertEqual(audit.probe("https://x.hf.space/a", opener=opener)["status"],
                         "RATE_LIMITED")
        self.assertEqual(opener.methods, ["HEAD"])

    def test_inventory_dedup_and_only_safe_public_hosts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "index.html").write_text(
                '<a href="https://huggingface.co/spaces/SZLHOLDINGS/a11oy">Space</a>'
                '<a href="https://huggingface.co/spaces/SZLHOLDINGS/a11oy">Duplicate</a>'
                '<img src="https://x.hf.space/logo.png">'
                '<a href="https://evil.test/redirect">Ignore</a>',
                encoding="utf-8",
            )
            entries = audit.inventory(root)
            self.assertEqual(len(entries), 2)
            self.assertFalse(any("evil.test" in item["url"] for item in entries))
            report = audit.evaluate(root, live=False)
            self.assertEqual(report["statuses"], {"NOT_PROBED": 2})
            self.assertEqual(report["release_admission"], "HOLD_UNVERIFIED")
            self.assertEqual(report["unobserved_urls"], 0)


if __name__ == "__main__":
    unittest.main()
