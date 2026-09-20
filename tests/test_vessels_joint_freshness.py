#!/usr/bin/env python3
"""Offline contracts for min-link joint freshness. Network-free."""
from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "vessels" / "joint-freshness.json"


class VesselsJointFreshnessContract(unittest.TestCase):
    def setUp(self) -> None:
        self.pack = json.loads(PACK.read_text(encoding="utf-8"))

    def test_digest_matches_canonical_bytes_without_digest_field(self) -> None:
        body = dict(self.pack)
        digest = body.pop("digest")
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), digest)
        self.assertTrue(digest.startswith("1cb5b117"))

    def test_honesty_locks(self) -> None:
        self.assertEqual(self.pack["status"], "ROADMAP")
        self.assertEqual(self.pack["data_label"], "SAMPLE")
        self.assertEqual(self.pack["formula_authority"], "NONE")
        self.assertFalse(self.pack["production_ready"])
        self.assertFalse(self.pack["stamps_live"])
        self.assertFalse(self.pack["licensed_ais_admitted"])
        self.assertEqual(self.pack["licensed_ais_queries"], 0)
        self.assertEqual(self.pack["vessels_e01"], "OUTSTANDING")
        self.assertEqual(self.pack["vessels_e03"], "OUTSTANDING")
        self.assertTrue(self.pack["does_not_mutate_world_digest"])
        self.assertEqual(
            self.pack["world_digest_unchanged"],
            "70fd1918fb38791159cfa2c520dc989f32125e4e0de4104b59d0a26fa48e1cb5",
        )
        self.assertEqual(
            self.pack["ais_lattice_digest_unchanged"],
            "f931b48544bcf70b1ca0d1c03b38b6c8e9dbf1933adfb8128316324e82eeb457",
        )

    def test_min_link_names_holes_and_does_not_pick_winners(self) -> None:
        self.assertTrue(self.pack["rule"]["does_not_pick_winners"])
        classes = {row["id"]: row for row in self.pack["authority_classes"]}
        self.assertEqual(len(classes), 7)
        self.assertEqual(classes["OFAC-vessel"]["freshness"], "REACHABLE_FRESH")
        self.assertTrue(classes["KR-MOFA-vessel"]["hole"])
        self.assertEqual(classes["KR-MOFA-vessel"]["maps_to"], "VESSELS-E-ABSTAIN")
        self.assertTrue(classes["Paris-banned"]["hole"])
        disagreements = {row["id"]: row for row in self.pack["disagreements"]}
        self.assertTrue(disagreements["UK-FCDO-vs-OFSI"]["winner_not_picked"])
        self.assertEqual(disagreements["UK-FCDO-vs-OFSI"]["using_stale_as_sole_source"], "VESSELS-E-ABSTAIN")
        holes = {row["id"] for row in self.pack["coverage_holes"]}
        self.assertIn("APAC-official-joint", holes)
        self.assertIn("CN-no-vessel-class", holes)
        ev = self.pack["negative_evidence"]
        self.assertEqual(ev["result"], "SAMPLE_TEXT_MISS")
        self.assertTrue(ev["miss_is_not_clearance"])
        self.assertFalse(ev["is_clearance"])
        self.assertTrue(ev["not_typesafe_jev_call"])
        refused = {row["id"] for row in self.pack["refused_surfaces"]}
        self.assertGreaterEqual(refused, {"MARINETRAFFIC", "pyais", "licensed-AIS-query"})

    def test_human_pages_exist(self) -> None:
        world = (ROOT / "vessels" / "world" / "index.html").read_text(encoding="utf-8")
        self.assertIn("Coverage-hole atlas", world)
        self.assertIn("SAMPLE_TEXT_MISS", world)
        self.assertIn("Does not stamp LIVE", world)
        self.assertIn("Never a11oy.com", world)
        self.assertNotIn("https://a11oy.com", world)
