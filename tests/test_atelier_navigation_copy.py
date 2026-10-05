"""Offline contract for the proof site's Atelier navigation description."""
from html.parser import HTMLParser
from pathlib import Path
import unittest


class CatalogueEntries(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_catalogue = False
        self.current = None
        self.entries = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "ul" and "index-catalog" in attrs.get("class", "").split():
            self.in_catalogue = True
        elif self.in_catalogue and tag == "li":
            self.current = {"links": [], "text": []}
        elif self.current is not None and tag == "a":
            self.current["links"].append(attrs.get("href"))

    def handle_data(self, data):
        if self.current is not None:
            self.current["text"].append(data)

    def handle_endtag(self, tag):
        if tag == "li" and self.current is not None:
            self.entries.append(self.current)
            self.current = None
        elif tag == "ul" and self.in_catalogue:
            self.in_catalogue = False


class AtelierNavigationCopyTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1]
        parser = CatalogueEntries()
        parser.feed((root / "index.html").read_text(encoding="utf-8"))
        parser.close()
        entries = [e for e in parser.entries if "/atelier/" in e["links"]]
        self.assertEqual(len(entries), 1)
        self.entry = entries[0]
        self.text = " ".join("".join(self.entry["text"]).split())

    def test_description_is_independent_of_inventory_count(self):
        self.assertIn("versioned Hub artifact explorer.", self.text)
        self.assertNotIn("forty-model", self.text)

    def test_canonical_space_identity_is_preserved(self):
        self.assertIn("Canonical playable Space is SZLHOLDINGS/szl-atelier.", self.text)
        self.assertEqual(self.entry["links"], ["/atelier/"])

    def test_lab_boundary_is_preserved(self):
        self.assertIn("Not product runtime.", self.text)


if __name__ == "__main__":
    unittest.main()
