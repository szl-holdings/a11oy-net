#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HUB = "https://huggingface.co/spaces/SZLHOLDINGS/killinchu"
OLD = "https://a-11-oy.com/aegis"


class AegisKillinchuConsolidation(unittest.TestCase):
    def test_aegis_route_is_preserved_as_proof_not_product(self) -> None:
        page = (ROOT / "aegis" / "index.html").read_text(encoding="utf-8")
        self.assertIn("Aegis → Killinchu", page)
        self.assertIn("One current product authority. Preserved historical proof.", page)
        self.assertIn(HUB, page)
        self.assertIn("formula authority NONE", page)
        self.assertIn("exact runtime parity not claimed", page)
        self.assertNotIn(OLD, page)

    def test_decision_contract_points_current_authority_to_killinchu(self) -> None:
        data = json.loads((ROOT / "decision.json").read_text(encoding="utf-8"))
        self.assertEqual(data["permalinks"]["product_aegis"], HUB)
        self.assertEqual(data["formula_authority"], "NONE")
        self.assertFalse(data["runtime_claimed"])
        row = next(item for item in data["verticals"] if item["id"] == "aegis")
        self.assertEqual(row["public_authority"], "killinchu")
        adapter = next(item for item in data["adapters"] if item["id"] == "aegis-assurance")
        self.assertEqual(adapter["consolidated_into"], "SZLHOLDINGS/killinchu")
        self.assertFalse(data["consolidations"]["aegis"]["runtime_readiness_claimed"])

    def test_space_contract_preserves_retirement_gate(self) -> None:
        data = json.loads((ROOT / "spaces.json").read_text(encoding="utf-8"))
        state = data["aegis_killinchu_consolidation"]
        self.assertEqual(state["current_public_authority"], "SZLHOLDINGS/killinchu")
        self.assertEqual(state["status"], "SOURCE_MERGED_PROVIDER_RETIREMENT_GATED")
        self.assertFalse(state["runtime_readiness_claimed"])

    def test_machine_record_is_exact_and_non_promotional(self) -> None:
        record = json.loads((ROOT / "consolidation" / "aegis-killinchu-20260903.json").read_text(encoding="utf-8"))
        self.assertEqual(record["current_public_authority"], "SZLHOLDINGS/killinchu")
        self.assertEqual(record["formula_authority_on_proof_origin"], "NONE")
        self.assertFalse(record["runtime_readiness_claimed"])
        self.assertEqual(len(record["capability_planes"]), 5)

    def test_current_facing_indexes_have_no_obsolete_product_url(self) -> None:
        paths = [
            "README.md", "FRONT_DOOR.md", "llms.txt", "index.html",
            "decision/index.html", "vessels/index.html", "scripts/szl-holo-proof-v2.js",
        ]
        for relative in paths:
            with self.subTest(path=relative):
                self.assertNotIn(OLD, (ROOT / relative).read_text(encoding="utf-8"))
        self.assertIn("https://a11oy.net/aegis/", (ROOT / "sitemap.xml").read_text(encoding="utf-8"))
        checker = (ROOT / "scripts" / "check_proof_surface.py").read_text(encoding="utf-8")
        self.assertIn('("terra", "aegis",', checker)


if __name__ == "__main__":
    unittest.main()
