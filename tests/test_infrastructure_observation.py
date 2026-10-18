"""Public observer declarations are not hardware or execution qualification."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
OBSERVATION = ROOT / "estate/living-souls-infrastructure/observation.json"
RAW_SOURCE = OBSERVATION.with_name("source-observation.json")
RAW_SHA256 = "2ad5512e38779bf10959e48bca2b83cd72d22d6c05f4a6ccb6d1f3aca9ac8d9a"


class InfrastructureObservationContract(unittest.TestCase):
    def setUp(self) -> None:
        self.projection = json.loads(OBSERVATION.read_text(encoding="utf-8"))
        # Only Git's text-checkout CRLF translation is normalized. The canonical
        # LF bytes are pinned to the original immutable Git blob, not new claims.
        self.raw = RAW_SOURCE.read_bytes().replace(b"\r\n", b"\n")
        self.original = json.loads(self.raw)

    def test_original_observer_bytes_and_source_binding_are_preserved(self) -> None:
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), RAW_SHA256)
        source = self.projection["source_observation"]
        self.assertEqual(source["sha256"], RAW_SHA256)
        self.assertEqual(source["git_blob"], "8818cbadd449893f1a53ea8b288e7eff632cebee")
        self.assertEqual(source["source_revision"], "c6779337195f0336b761e5599312e4b454ee3702")
        self.assertEqual(source["original_path"], "estate/living-souls-infrastructure/observation.json")
        self.assertEqual(source["path"], "/estate/living-souls-infrastructure/source-observation.json")

    def test_public_projection_copies_are_identical(self) -> None:
        mirror = ROOT / "estate/living-souls-infrastructure-2026-10-17.json"
        self.assertEqual(mirror.read_text(encoding="utf-8"), OBSERVATION.read_text(encoding="utf-8"))

    def test_unverified_observations_never_authorize_execution_or_spend(self) -> None:
        self.assertEqual(self.projection["evidence_class"], "DECLARED")
        self.assertEqual(self.projection["cloudflare_api_control"], "UNKNOWN")
        boundary = self.projection["claim_boundaries"]
        self.assertEqual(boundary["independent_verification"], "UNKNOWN")
        for field in ("execution_authorized", "training_authorized", "spend_authorized"):
            self.assertIs(boundary[field], False, field)
        for section in ("domains", "ha_alternatives", "nodes"):
            for name, current in self.projection[section].items():
                self.assertEqual(current["status"], "DECLARED", name)
                original = dict(self.original[section][name])
                original["status"] = "DECLARED"
                self.assertEqual(current, original, name)
        for field in ("hf_public_counts_api", "networking", "observed_at", "observer", "organization"):
            self.assertEqual(self.projection[field], self.original[field], field)

    def test_public_page_does_not_promote_the_preserved_report(self) -> None:
        page = OBSERVATION.with_name("index.html").read_text(encoding="utf-8")
        self.assertIn("Evidence class: DECLARED", page)
        self.assertIn("Independent verification: UNKNOWN", page)
        self.assertIn('href="./source-observation.json"', page)
        self.assertNotIn("GitHub measured audit", page)
        for label in (">LIVE<", ">EVALUATION_ONLY<", "Evidence class: SNAPSHOT"):
            self.assertNotIn(label, page)


if __name__ == "__main__":
    unittest.main()
