"""Delivery regressions: nested resources rotate URLs, while evidence stays exact."""

from __future__ import annotations

import hashlib
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import fingerprint_frontend_assets as frontend

REVISION = "1" * 40


def fixture(root: pathlib.Path) -> dict[str, bytes]:
    files = {
        "assets/base.css": b":root{--ink:white;--paper:black}",
        "assets/theme.css": b'@import url("./base.css");\nbody{color:var(--ink)}',
        "scripts/szl-flow-proof.js": (
            b'var SPECTRAL_STYLE = "/assets/theme.css";\n'
            b'const runtimeData = {path:"/assets/base.css",count:25};'
        ),
        "scripts/unchanged.js": b'const source = "/assets/theme.css";',
        "index.html": (
            b'<!doctype html>\n<html><head><link rel="stylesheet" href="/assets/theme.css">'
            b'<script data-src="/scripts/unchanged.js" src="/scripts/szl-flow-proof.js" defer></script>'
            b'<script type="application/json">{"source":"/assets/theme.css","count":25}</script>'
            b'<script>const path="/assets/theme.css";</script></head><body>'
            b'<a href="/assets/theme.css">Source</a><p>REPORTED count 25; UNAVAILABLE</p>'
            b'<link rel="stylesheet" href="https://example.org/assets/theme.css">'
            b'</body></html>'
        ),
        "record/index.html": b'<link rel="stylesheet" href="../assets/theme.css?view=record#top"><h1>RECORD</h1>',
        "record.json": b'{"source":"/assets/theme.css","evidence_class":"SNAPSHOT","count":25}',
    }
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return files


def alias(path: str, content: bytes) -> str:
    original = pathlib.PurePosixPath(path)
    return original.with_name(original.stem + "." + hashlib.sha256(content).hexdigest() + original.suffix).as_posix()


class FrontendFingerprintTests(unittest.TestCase):
    def test_nested_import_and_dynamic_loader_bind_exact_derived_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            source = fixture(root)
            manifest = frontend.fingerprint(root, REVISION)
            base_alias = alias("assets/base.css", source["assets/base.css"])
            expected_theme = b'@import url("./' + base_alias.split("/")[-1].encode() + b'");\nbody{color:var(--ink)}'
            theme_alias = alias("assets/theme.css", expected_theme)
            expected_script = source["scripts/szl-flow-proof.js"].replace(
                b'var SPECTRAL_STYLE = "/assets/theme.css"',
                b'var SPECTRAL_STYLE = "/' + theme_alias.encode() + b'"'
            )
            script_alias = alias("scripts/szl-flow-proof.js", expected_script)
            self.assertEqual((root / base_alias).read_bytes(), source["assets/base.css"])
            self.assertEqual((root / theme_alias).read_bytes(), expected_theme)
            self.assertEqual((root / script_alias).read_bytes(), expected_script)
            served = (root / "index.html").read_bytes()
            expected_html = source["index.html"].replace(
                b'rel="stylesheet" href="/assets/theme.css"',
                b'rel="stylesheet" href="/' + theme_alias.encode() + b'"'
            ).replace(b' src="/scripts/szl-flow-proof.js"', b' src="/' + script_alias.encode() + b'"')
            self.assertEqual(served, expected_html)
            self.assertEqual((root / "record/index.html").read_bytes(),
                             b'<link rel="stylesheet" href="../' + theme_alias.encode() + b'?view=record#top"><h1>RECORD</h1>')
            self.assertNotIn(b"<script", (root / "record/index.html").read_bytes())
            # Canonical paths, runtime data, inline scripts, evidence, and source links survive.
            for path in source:
                if not path.endswith(".html"):
                    self.assertEqual((root / path).read_bytes(), source[path])
            self.assertEqual(manifest["source_revision"], REVISION)
            self.assertEqual(manifest["scope"], "STATIC_FRONTEND_ASSET_DELIVERY_ONLY")
            self.assertEqual(manifest["assets"]["scripts/szl-flow-proof.js"]["dependencies"], ["assets/theme.css"])

    def test_same_source_is_deterministic_and_changed_dependency_rotates_parent_urls(self):
        with tempfile.TemporaryDirectory() as temporary:
            roots = [pathlib.Path(temporary) / name for name in ("one", "two", "changed")]
            for root in roots:
                fixture(root)
            (roots[2] / "assets/base.css").write_bytes(b":root{--ink:ivory;--paper:black}")
            first, second, changed = [frontend.fingerprint(root, REVISION) for root in roots]
            self.assertEqual(first, second)
            self.assertEqual({p.relative_to(roots[0]): p.read_bytes() for p in roots[0].rglob("*") if p.is_file()},
                             {p.relative_to(roots[1]): p.read_bytes() for p in roots[1].rglob("*") if p.is_file()})
            for path in ("assets/base.css", "assets/theme.css", "scripts/szl-flow-proof.js"):
                self.assertNotEqual(first["assets"][path]["served_path"], changed["assets"][path]["served_path"])
            self.assertEqual(first["assets"]["scripts/unchanged.js"]["served_path"],
                             changed["assets"]["scripts/unchanged.js"]["served_path"])
            self.assertNotEqual((roots[0] / "index.html").read_bytes(), (roots[2] / "index.html").read_bytes())

    def test_cycles_and_ambiguous_loader_fail_before_any_derived_file_is_written(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            fixture(root)
            (root / "assets/base.css").write_text('@import "./theme.css";', encoding="utf-8")
            before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            with self.assertRaisesRegex(ValueError, "cyclic"):
                frontend.fingerprint(root, REVISION)
            self.assertEqual(before, {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()})
            fixture(root)
            (root / "scripts/szl-flow-proof.js").write_text('var SPECTRAL_STYLE = "/assets/base.css"; var SPECTRAL_STYLE = "/assets/theme.css";', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "ambiguous"):
                frontend.fingerprint(root, REVISION)
            self.assertFalse((root / frontend.MANIFEST).exists())

    def test_existing_manifest_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            fixture(root)
            frontend.fingerprint(root, REVISION)
            before = (root / frontend.MANIFEST).read_bytes()
            with self.assertRaisesRegex(ValueError, "fresh staging"):
                frontend.fingerprint(root, REVISION)
            self.assertEqual((root / frontend.MANIFEST).read_bytes(), before)

    def test_missing_local_dependency_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            fixture(root)
            (root / "assets/base.css").write_text('@import url(./missing.css);', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unresolved frontend asset dependency"):
                frontend.fingerprint(root, REVISION)
            self.assertFalse((root / frontend.MANIFEST).exists())


if __name__ == "__main__":
    unittest.main()
