"""Offline regressions for the catch-all header policy across secondary pages."""
from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_security_headers as headers


class GlobalScriptCoverageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = pathlib.Path(self.temporary.name)
        (self.root / "index.html").write_text("<title>Proof</title>", encoding="utf-8")
        self.policy = {"content-security-policy": "default-src 'self'; script-src 'self'"}

    def page(self, relative, html):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")

    def check(self):
        return headers.validate_global_script_coverage(self.root, self.policy)

    def test_secondary_inline_script_is_not_hidden_by_clean_homepage(self):
        self.page("ayllu/index.html", "<script>window.roster = 11;</script>")
        self.assertEqual(len(self.check()), 1)
        self.assertIn("ayllu/index.html: inline script hashes", self.check()[0])

    def test_data_src_does_not_hide_inline_script(self):
        self.page("secondary/index.html", '<script data-src="/safe.js">window.blocked=true;</script>')
        self.assertIn("inline script hashes", self.check()[0])

    def test_src_text_inside_another_attribute_does_not_hide_inline_script(self):
        self.page("secondary/index.html", '<script data-info="src=/safe.js">window.blocked=true;</script>')
        self.assertIn("inline script hashes", self.check()[0])

    def test_duplicate_src_attributes_fail_in_both_orders(self):
        for attrs in ('src="https://example.invalid/x.js" src="/safe.js"', 'src="/safe.js" src="https://example.invalid/x.js"'):
            with self.subTest(attrs=attrs):
                self.page("secondary/index.html", f'<script {attrs}></script>')
                self.assertTrue(any("duplicate HTML attributes" in error for error in self.check()))

    def test_first_duplicate_attribute_matches_browser_semantics(self):
        surface = headers.HtmlSecuritySurface()
        surface.feed('<script src="https://example.invalid/x.js" src="/safe.js"></script>')
        self.assertEqual(surface.script_sources, ["https://example.invalid/x.js"])

    def test_backslash_or_control_script_urls_fail_closed(self):
        for source in (r"\\example.invalid/x.js", "/scripts/\tx.js", ""):
            with self.subTest(source=source):
                self.page("secondary/index.html", f'<script src="{source}"></script>')
                self.assertTrue(any("ambiguous script source" in error for error in self.check()))

    def test_iframe_srcdoc_is_not_silently_excluded_from_script_coverage(self):
        self.page("secondary/index.html", '<iframe srcdoc="&lt;script&gt;window.blocked=true;&lt;/script&gt;"></iframe>')
        self.assertTrue(any("iframe srcdoc" in error for error in self.check()))

    def test_self_closing_or_unclosed_script_fails_closed(self):
        for html in ('<script/>window.blocked=true;</script>', '<script>window.blocked=true;'):
            with self.subTest(html=html):
                self.page("secondary/index.html", html)
                self.assertTrue(any("ambiguous script markup" in error for error in self.check()))

    def test_abrupt_or_bang_comment_closures_fail_closed(self):
        for html in ('<!--><script>window.blocked=true;</script>-->', '<!---><script>window.blocked=true;</script>-->', '<!--><img src=x onerror="window.blocked=true;">-->', '<!-- comment --!><script>window.blocked=true;</script>'):
            with self.subTest(html=html):
                self.page("secondary/index.html", html)
                self.assertTrue(any("ambiguous HTML comment syntax" in error for error in self.check()))

    def test_cross_origin_base_is_not_silently_ignored(self):
        self.page("secondary/index.html", '<base href="https://example.invalid/"><script src="script.js"></script>')
        self.assertTrue(any("base href is not admitted" in error for error in self.check()))

    def test_html_cdata_cannot_hide_script(self):
        self.page("secondary/index.html", '<![CDATA[><script>window.blocked=true;</script>]]>')
        self.assertTrue(any("unsupported HTML declaration" in error for error in self.check()))

    def test_html_cdata_cannot_hide_event_handler(self):
        self.page("secondary/index.html", '<![CDATA[><img src=x onerror="window.blocked=true;">]]>')
        self.assertTrue(any("unsupported HTML declaration" in error for error in self.check()))

    def test_unknown_declarations_fail_closed(self):
        for html in ('<!bogus><script>window.blocked=true;</script>', '<![INVALID[><script>window.blocked=true;</script>]]>'):
            with self.subTest(html=html):
                self.page("secondary/index.html", html)
                self.assertTrue(any("unsupported HTML declaration" in error for error in self.check()))

    def test_svg_raw_text_cannot_hide_event_handler(self):
        self.page("secondary/index.html", '<svg><style><img src=x onerror="window.blocked=true;"></style></svg>')
        self.assertTrue(any("inline SVG/MathML" in error for error in self.check()))

    def test_mathml_raw_text_cannot_hide_event_handler(self):
        self.page("secondary/index.html", '<math><style><img src=x onerror="window.blocked=true;"></style></math>')
        self.assertTrue(any("inline SVG/MathML" in error for error in self.check()))

    def test_same_origin_base_keeps_script_origin_admitted(self):
        self.page("secondary/index.html", '<base href="/scripts/"><script src="app.js"></script>')
        self.assertEqual(self.check(), [])

    def test_future_nested_html_is_included(self):
        self.page("new/nested/index.html", "<script>window.value = 1;</script>")
        self.assertIn("new/nested/index.html", self.check()[0])

    def test_exact_hash_is_admitted_but_a_changed_body_is_rejected(self):
        html = "<script>window.value = 1;</script>"
        digest = next(iter(headers.inline_script_hashes(html)))
        self.policy["content-security-policy"] += " " + digest
        self.page("record/index.html", html)
        self.assertEqual(self.check(), [])
        self.page("record/index.html", html.replace("1", "2"))
        self.assertIn("record/index.html: inline script hashes", self.check()[0])

    def test_uppercase_and_htm_extensions_are_included(self):
        self.page("new/page.HTML", "<script>window.value = 1;</script>")
        self.page("new/page.htm", "<script>window.value = 1;</script>")
        errors = self.check()
        self.assertEqual(len(errors), 2)
        self.assertTrue(any("new/page.HTML" in error for error in errors))
        self.assertTrue(any("new/page.htm" in error for error in errors))

    def test_same_origin_script_paths_are_admitted(self):
        self.page("ayllu/index.html", '<script src="/scripts/ayllu-showcase.js"></script>')
        self.page("khipu/index.html", '<script src="../scripts/khipu-showcase.js"></script>')
        self.page("other/index.html", '<script src="https://a11oy.net:443/scripts/app.js"></script>')
        self.assertEqual(self.check(), [])

    def test_cross_origin_and_credentialed_script_sources_are_rejected(self):
        for source in ("https://example.invalid/script.js", "//example.invalid/x.js", "https://user@a11oy.net/script.js", "data:text/javascript,void(0)"):
            with self.subTest(source=source):
                self.page("secondary/index.html", f'<script src="{source}"></script>')
                self.assertIn("script source is not admitted", self.check()[0])

    def test_same_origin_still_requires_self_permission(self):
        self.policy["content-security-policy"] = "default-src 'none'"
        self.page("secondary/index.html", '<script src="/scripts/app.js"></script>')
        self.assertIn("script source is not admitted", self.check()[0])

    def test_malformed_script_url_fails_closed(self):
        self.page("secondary/index.html", '<script src="https://a11oy.net:invalid/app.js"></script>')
        self.assertIn("script source is not admitted", self.check()[0])

    def test_inline_event_handler_is_rejected(self):
        self.page("secondary/index.html", '<button onclick="void(0)">Action</button>')
        self.assertIn("inline event attributes", self.check()[0])

    def test_javascript_url_is_rejected_after_html_attribute_decoding(self):
        self.page("secondary/index.html", '<a href="java&#9;script:void(0)">Action</a>')
        self.assertIn("JavaScript URL attributes", self.check()[0])

    def test_unpublished_github_control_html_is_excluded(self):
        self.page(".github/template.html", "<script>window.value = 1;</script>")
        self.assertEqual(self.check(), [])

    def test_empty_scope_fails(self):
        (self.root / "index.html").unlink()
        self.assertIn("no HTML pages found", self.check()[0])

    def test_symlinked_html_fails(self):
        (self.root / "linked.html").symlink_to(self.root / "index.html")
        self.assertIn("symlinked HTML is not admitted", self.check()[0])

    def test_duplicate_policy_directives_fail(self):
        self.policy["content-security-policy"] += "; script-src 'none'"
        self.assertIn("duplicate CSP directive", self.check()[0])


if __name__ == "__main__":
    unittest.main()
