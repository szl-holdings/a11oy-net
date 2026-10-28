# SPDX-License-Identifier: Apache-2.0
"""Fixture regressions for scripts/check_links.py (the Link & Asset Check step).

The checker scans every *.html file below its working directory. The fixtures
are therefore written to temporary directories at test time: a deliberately
broken page committed under tests/ would also be scanned by the real site
check and fail it.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_links.py"
OK_LINE = "OK: HTML parses and all local links/assets resolve."

CLEAN_SITE = {
    "index.html": """<!doctype html>
<html lang="en">
<head>
<meta property="og:image" content="https://a11oy.net/assets/social.png">
<meta name="twitter:image" content="/assets/social.png">
<link rel="stylesheet" href="assets/site.css">
</head>
<body id="top">
<a href="#top">self fragment</a>
<a href="/about/">directory page</a>
<a href="about">directory page without a slash</a>
<a href="notes">extensionless page</a>
<a href="notes.html#method">page fragment</a>
<a href="https://www.a11oy.net/notes.html">same origin, absolute</a>
<a href="https://a11oy.net">same origin root</a>
<a href="https://example.org/missing.html">other origins are not followed</a>
<a href="?q=1">query only</a>
<a href="assets/space%20name.txt">percent-encoded path</a>
<a href="mailto:security@a11oy.net">mail</a>
<a href="tel:+10000000000">phone</a>
<a href="javascript:void(0)">script</a>
<img src="data:image/gif;base64,R0lGODlhAQABAAAAACw=" alt="">
<img src="assets/social.png" srcset="assets/social.png 1x, /assets/social@2x.png 2x" alt="">
<video poster="/assets/social.png"></video>
</body>
</html>
""",
    "about/index.html": '<!doctype html><title>About</title><a href="../index.html#top">back</a>\n',
    "notes.html": '<!doctype html><title>Notes</title><h2 id="method">Method</h2>\n',
    "assets/site.css": "body { margin: 0; }\n",
    "assets/social.png": b"\x89PNG\r\n\x1a\n",
    "assets/social@2x.png": b"\x89PNG\r\n\x1a\n",
    "assets/space name.txt": "plain text\n",
    "sitemap.xml": (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        "<url><loc>https://a11oy.net/</loc></url></urlset>\n"
    ),
    # Pages under .git are never scanned, so this broken link must not count.
    ".git/ignored.html": '<a href="/does-not-exist.html">ignored</a>\n',
}

BROKEN_SITE = {
    "index.html": """<!doctype html>
<html lang="en">
<head>
<meta property="og:image" content="https://a11oy.net/assets/missing-social.png">
</head>
<body>
<a href="/missing/">missing directory page</a>
<a href="missing-page">missing extensionless page</a>
<img src="assets/missing.png" alt="">
<a href="about.html#nowhere">missing page fragment</a>
<a href="../outside.html">escapes the site root</a>
<a href="#absent">missing self fragment</a>
</body>
</html>
""",
    "about.html": '<!doctype html><title>About</title><h1 id="here">About</h1>\n',
    "sitemap.xml": "<urlset><url></urlset>\n",
}

BROKEN_ERRORS = [
    "index.html: local target not found -> https://a11oy.net/assets/missing-social.png",
    "index.html: local target not found -> /missing/",
    "index.html: local target not found -> missing-page",
    "index.html: local target not found -> assets/missing.png",
    "index.html: fragment has no target -> about.html#nowhere",
    "index.html: path escapes site root -> ../outside.html",
    "index.html: fragment has no target -> #absent",
]


def write_site(base: pathlib.Path, files: dict) -> pathlib.Path:
    site = base / "site"
    for relative, content in files.items():
        path = site / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
    return site


def run_checker(site: pathlib.Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=site,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )


class CheckLinksTest(unittest.TestCase):
    def test_clean_site_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = write_site(pathlib.Path(tmp), CLEAN_SITE)
            result = run_checker(site)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout, OK_LINE + "\n")
        self.assertEqual(result.stderr, "")

    def test_broken_site_fails_with_every_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            # An existing file outside the site root is still refused.
            (base / "outside.html").write_text("<p>outside</p>\n", encoding="utf-8")
            site = write_site(base, BROKEN_SITE)
            result = run_checker(site)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(result.stderr, "")
        lines = result.stdout.splitlines()
        self.assertEqual(lines[0], "Link/asset check FAILED:")
        self.assertEqual(lines[1:-1], [" - " + error for error in BROKEN_ERRORS])
        self.assertTrue(
            lines[-1].startswith(" - sitemap.xml is not valid XML: "), lines[-1]
        )
        self.assertNotIn(OK_LINE, result.stdout)


if __name__ == "__main__":
    unittest.main()
