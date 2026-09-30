"""Regression checks for isolated, exact-source GitHub Pages artifacts."""

from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_pages_artifact.py"
sys.path.insert(0, str(ROOT / "scripts"))


def load_builder():
    spec = importlib.util.spec_from_file_location("build_pages_artifact", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Pages artifact builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PagesArtifactTests(unittest.TestCase):
    def test_stages_exact_source_without_mutating_committed_health(self) -> None:
        builder = load_builder()
        source_revision = subprocess.check_output(
            ("git", "-C", str(ROOT), "rev-parse", "HEAD"), text=True
        ).strip()
        source_health_before = (ROOT / "health.json").read_bytes()

        with tempfile.TemporaryDirectory() as temporary:
            output = pathlib.Path(temporary) / "site"
            receipt = builder.build(ROOT, output, source_revision)

            self.assertEqual(receipt["status"], "PAGES_ARTIFACT_STAGED")
            self.assertEqual(receipt["source_revision"], source_revision)
            self.assertFalse((output / ".git").exists())
            self.assertFalse((output / ".github").exists())
            self.assertTrue((output / ".well-known" / "security.txt").is_file())
            self.assertTrue((output / ".nojekyll").is_file())
            committed_index = subprocess.check_output(
                ("git", "-C", str(ROOT), "show", f"{source_revision}:index.html")
            )
            self.assertEqual((output / "index.html").read_bytes(), committed_index)

            staged_health = json.loads(
                (output / "health.json").read_text(encoding="utf-8")
            )
            self.assertEqual(staged_health["sha"], source_revision)
            self.assertEqual(staged_health["signer"], "unavailable")
            self.assertEqual(staged_health["probe_contract"], "STATIC_DOCUMENT")
            self.assertEqual(staged_health["uptime"], "NOT_MEASURED")
            self.assertEqual(staged_health["dsse_live"], "NOT_CLAIMED")

        self.assertEqual((ROOT / "health.json").read_bytes(), source_health_before)

    def test_rejects_output_inside_source_tree(self) -> None:
        builder = load_builder()
        source_revision = subprocess.check_output(
            ("git", "-C", str(ROOT), "rev-parse", "HEAD"), text=True
        ).strip()
        with self.assertRaisesRegex(ValueError, "outside the source tree"):
            builder.build(ROOT, ROOT / ".pages-site", source_revision)


if __name__ == "__main__":
    unittest.main()
