from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "build_estate_release_vector.py"
SPEC = importlib.util.spec_from_file_location("build_estate_release_vector", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


class EstateReleaseVectorTests(unittest.TestCase):
    def test_source_revision_accepts_only_recognized_exact_sha_fields(self) -> None:
        sha = "a" * 40
        self.assertEqual(release.source_revision({"source_revision": sha}), (sha, "source_revision"))
        self.assertEqual(release.source_revision({"build": {"revision": sha}}), (sha, "build.revision"))
        self.assertEqual(release.source_revision({"nested": {"revision": sha}}), (None, None))
        self.assertEqual(release.source_revision({"sha256": "b" * 64}), (None, None))

    def test_build_requires_proof_artifact_and_both_product_witnesses(self) -> None:
        a11oy_sha = "a" * 40
        proof_sha = "b" * 40
        profile_sha = "c" * 40

        def github(repository: str):
            sha = {
                "szl-holdings/a11oy": a11oy_sha,
                "szl-holdings/a11oy-net": proof_sha,
                "szl-holdings/.github": profile_sha,
            }[repository]
            return {"repository": repository, "sha": sha, "observed": True, "protected": True, "status": 200}

        with (
            mock.patch.object(release, "github_main", side_effect=github),
            mock.patch.object(
                release,
                "live_source",
                side_effect=[
                    {"revision": a11oy_sha, "observed": True},
                    {"revision": a11oy_sha, "observed": True},
                ],
            ),
            mock.patch.object(
                release,
                "hf_runtime",
                return_value={"stage": "RUNNING", "sha": "d" * 40, "observed": True},
            ),
        ):
            result = release.build(proof_sha=proof_sha)
        self.assertEqual(result["state"], "ALIGNED")
        self.assertEqual(result["blockers"], [])
        self.assertIs(result["truth"]["provider_writes_performed"], False)
        self.assertEqual(result["truth"]["external_effectors"], [])

        with (
            mock.patch.object(release, "github_main", side_effect=github),
            mock.patch.object(
                release,
                "live_source",
                side_effect=[
                    {"revision": "e" * 40, "observed": True},
                    {"revision": a11oy_sha, "observed": True},
                ],
            ),
            mock.patch.object(
                release,
                "hf_runtime",
                return_value={"stage": "RUNNING", "sha": "d" * 40, "observed": True},
            ),
        ):
            result = release.build(proof_sha=proof_sha)
        self.assertEqual(result["state"], "DIVERGENT")
        self.assertIn("PRODUCT_DOMAIN_SOURCE_MISMATCH", result["blockers"])

    def test_release_id_is_stable_for_one_source_vector(self) -> None:
        value = {"a11oy": "a" * 40, "proof": "b" * 40, "profile": "c" * 40}
        self.assertEqual(release.digest(value), release.digest(value))

    def test_proof_page_is_mobile_accessible_and_local(self) -> None:
        page = (ROOT / "estate" / "alignment" / "index.html").read_text(encoding="utf-8")
        self.assertIn('name="viewport"', page)
        self.assertIn('data-szl-proof-release-vector="1.0.0"', page)
        self.assertIn("min-width:48px", page)
        self.assertIn("prefers-reduced-motion", page)
        self.assertIn("forced-colors", page)
        self.assertIn("/estate/release-vector.json", page)
        self.assertNotIn("https://cdn", page)
        self.assertNotIn("localStorage", page)
        self.assertNotIn("sessionStorage", page)


if __name__ == "__main__":
    unittest.main()
