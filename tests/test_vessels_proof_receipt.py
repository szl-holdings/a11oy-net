#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KERNEL_SHA = "be143acc1cbb52591a05b56da7b9ae362c315a65cd570087faba08966e339f85"
EXPECTED = {
    "VESSELS-E-ABSTAIN": ("ABSTAINED", "ec8868f29dea05cd9fe94c74fd765a1914d6545c0f11db7f48c3752f9eb86458"),
    "VESSELS-E-AWAIT-01": ("AWAITING_APPROVAL", "ae6e3fc7fdc6fb28e62040926d474848b729f31ef3fda7a4253575880638e5be"),
    "VESSELS-E-DENY-AIS": ("DENIED", "0829bcbcd01154d383dca25ff996a8a4704e3183bbce00b393e0426a91bd9275"),
}


class VesselsProofReceipt(unittest.TestCase):
    def test_receipt_binds_kernel_and_three_states(self) -> None:
        receipt = json.loads((ROOT / "vessels" / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["kernel_version"], "8.0.0")
        self.assertEqual(receipt["kernel_sha256"], KERNEL_SHA)
        self.assertEqual(receipt["formula_authority"], "NONE")
        self.assertFalse(receipt["kernel_run_here"])
        self.assertFalse(receipt["stamps_live"])
        self.assertFalse(receipt["licensed_ais_admitted"])
        self.assertEqual(receipt["sample"]["licensed_ais_queries"], 0)
        self.assertEqual(receipt["sample"]["state_match"], 3)
        self.assertEqual(receipt["lambda"], "Conjecture 1 / ADVISORY_CONJECTURAL")
        self.assertEqual(receipt["boundaries"]["lambda_uniqueness"], "Conjecture 1 OPEN")
        by_id = {row["eval_id"]: row for row in receipt["cases"]}
        self.assertEqual(set(by_id), set(EXPECTED))
        for eval_id, (state, digest) in EXPECTED.items():
            row = by_id[eval_id]
            self.assertEqual(row["expected_state"], state)
            self.assertEqual(row["observed_state"], state)
            self.assertEqual(row["receipt_digest"], digest)
            self.assertTrue(row["match"])
            self.assertTrue(row["replay_hold"])
            self.assertEqual(row["formula_authority"], "NONE")
        self.assertNotIn("X-Amz-Security-Token", json.dumps(receipt))

    def test_html_stays_static_and_points_at_product_desk(self) -> None:
        page = (ROOT / "vessels" / "index.html").read_text(encoding="utf-8")
        self.assertIn("formula authority NONE", page)
        self.assertIn("Never a11oy.com.", page)
        self.assertIn("https://a-11-oy.com/vessels", page)
        self.assertEqual(page.count("https://a-11-oy.com/vessels"), 2)
        self.assertNotIn("https://huggingface.co/spaces/SZLHOLDINGS/killinchu", page)
        furniture = "https://" + "a11oy.com"
        self.assertNotIn(furniture, page)
        self.assertIn("script-src 'none'", page)
        self.assertIn("connect-src 'none'", page)
        self.assertIn("Conjecture 1 OPEN", page)
        self.assertIn(KERNEL_SHA, page)
        self.assertIn("OUTSTANDING", page)
        self.assertIn("Does not stamp LIVE", page)
        self.assertNotIn("production LIVE", page)

    def test_decision_index_lists_vessels(self) -> None:
        page = (ROOT / "decision" / "index.html").read_text(encoding="utf-8")
        self.assertIn("VESSELS-E-DENY-AIS", page)
        self.assertIn("https://a-11-oy.com/vessels", page)
        self.assertIn("/vessels/", page)
        data = json.loads((ROOT / "decision.json").read_text(encoding="utf-8"))
        self.assertEqual(data["permalinks"]["product_vessels"], "https://a-11-oy.com/vessels")
        self.assertEqual(data["permalinks"]["product_aegis"], "https://huggingface.co/spaces/SZLHOLDINGS/killinchu")
        ids = [row["id"] for row in data["verticals"]]
        self.assertIn("vessels", ids)
        self.assertFalse(data["runtime_claimed"])
        self.assertEqual(data["formula_authority"], "NONE")


if __name__ == "__main__":
    unittest.main()
