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
        source_witness_before = (
            ROOT / ".well-known" / "szl-source.json"
        ).read_bytes()

        with tempfile.TemporaryDirectory() as temporary:
            output = pathlib.Path(temporary) / "site"
            receipt = builder.build(ROOT, output, source_revision)

            self.assertEqual(receipt["status"], "PAGES_ARTIFACT_STAGED")
            self.assertEqual(receipt["source_revision"], source_revision)
            self.assertFalse((output / ".git").exists())
            self.assertFalse((output / ".github").exists())
            self.assertTrue((output / ".well-known" / "security.txt").is_file())
            self.assertTrue(
                (output / ".well-known" / "szl-source.json").is_file()
            )
            self.assertTrue((output / ".nojekyll").is_file())
            self.assertTrue((output / "oac" / "index.html").is_file())
            self.assertTrue((output / "oac" / "release.json").is_file())
            committed_index = subprocess.check_output(
                ("git", "-C", str(ROOT), "show", f"{source_revision}:index.html")
            )
            self.assertEqual((output / "index.html").read_bytes(), committed_index)
            for relative in ("public-membership.json", "estate/canonical-hf-manifest.json",
                             "public-membership.observed-2026-09-10.json"):
                committed = subprocess.check_output(
                    ("git", "-C", str(ROOT), "show", f"{source_revision}:{relative}")
                )
                self.assertEqual((output / relative).read_bytes(), committed)

            staged_health = json.loads(
                (output / "health.json").read_text(encoding="utf-8")
            )
            self.assertEqual(staged_health["sha"], source_revision)
            self.assertEqual(staged_health["signer"], "unavailable")
            self.assertEqual(staged_health["probe_contract"], "STATIC_DOCUMENT")
            self.assertEqual(staged_health["uptime"], "NOT_MEASURED")
            self.assertEqual(staged_health["dsse_live"], "NOT_CLAIMED")

            staged_source_witness = json.loads(
                (output / ".well-known" / "szl-source.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                staged_source_witness["source_revision"], source_revision
            )
            self.assertEqual(
                staged_source_witness["artifact_kind"], "STATIC_GITHUB_PAGES"
            )
            self.assertEqual(
                staged_source_witness["artifact_binding"], "EXACT_SOURCE_REVISION"
            )
            self.assertEqual(
                staged_source_witness["product_runtime_readiness"], "UNAVAILABLE"
            )
            self.assertEqual(staged_source_witness["uptime"], "UNAVAILABLE")
            self.assertEqual(staged_source_witness["dsse_live"], "UNAVAILABLE")
            self.assertEqual(
                receipt["source_witness_contract"]["source_revision"],
                source_revision,
            )

        self.assertEqual((ROOT / "health.json").read_bytes(), source_health_before)
        self.assertEqual(
            (ROOT / ".well-known" / "szl-source.json").read_bytes(),
            source_witness_before,
        )

    def test_rejects_output_inside_source_tree(self) -> None:
        builder = load_builder()
        source_revision = subprocess.check_output(
            ("git", "-C", str(ROOT), "rev-parse", "HEAD"), text=True
        ).strip()
        with self.assertRaisesRegex(ValueError, "outside the source tree"):
            builder.build(ROOT, ROOT / ".pages-site", source_revision)


if __name__ == "__main__":
    unittest.main()
