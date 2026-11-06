"""The Estate OS plane hologram links every Hub card into its own namespace.

The 2026-08-29 bake wrote https://huggingface.co/<id> (the model namespace) for
its Space and dataset cards, so /estate/plane/#/hub sent those rows to the
wrong repository type. The bake's observations stay as captured; only the
derived href is rebuilt, and the correction is recorded in the bake itself.
"""

from __future__ import annotations

import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "estate" / "plane" / "data.json"
NAMESPACE = {
    "model": "https://huggingface.co/",
    "dataset": "https://huggingface.co/datasets/",
    "space": "https://huggingface.co/spaces/",
}


class PlaneHubLinkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = json.loads(DATA.read_text(encoding="utf-8"))

    def test_every_hub_card_links_into_its_own_namespace(self) -> None:
        for card in self.data["hub"]:
            with self.subTest(card=f"{card['kind']}:{card['id']}"):
                self.assertIn(card["kind"], NAMESPACE)
                self.assertTrue(card["id"].startswith("SZLHOLDINGS/"))
                self.assertEqual(card["href"], NAMESPACE[card["kind"]] + card["id"])

    def test_correction_is_recorded_without_relabelling_the_bake(self) -> None:
        corrections = self.data["linkCorrections"]
        self.assertEqual(self.data["capturedAt"], "2026-08-29T16:49:00Z")
        self.assertEqual(corrections["field"], "hub[].href")
        self.assertIn("does not assert that the repository is public now", corrections["rule"])
        cards = {f"{card['kind']}:{card['id']}" for card in self.data["hub"]}
        corrected = corrections["corrected"]
        self.assertEqual(len(corrected), len(set(corrected)))
        self.assertLessEqual(set(corrected), cards)
        self.assertFalse([entry for entry in corrected if entry.startswith("model:")])


if __name__ == "__main__":
    unittest.main()
