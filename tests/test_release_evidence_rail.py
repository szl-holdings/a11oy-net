"""Static investor/developer release-chain snapshot remains evidence-honest."""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import unittest
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
FILE=ROOT/"diligence"/"release"/"index.html"
CANONICAL="https://a11oy.net/diligence/release/"


class Document(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids=set()
        self.links=[]
        self.styles=[]
        self.canon=[]
        self.scripts=0
        self.main=0
        self.h1=0
        self.lang=None

    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if attrs.get("id"):self.ids.add(attrs["id"])
        if tag=="html":self.lang=attrs.get("lang")
        elif tag=="a":self.links.append(attrs)
        elif tag=="link":
            if attrs.get("rel")=="canonical":self.canon.append(attrs.get("href"))
            if attrs.get("rel")=="stylesheet":self.styles.append(attrs.get("href"))
        elif tag=="script":self.scripts+=1
        elif tag=="main":self.main+=1
        elif tag=="h1":self.h1+=1


class ReleaseChainContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html=FILE.read_text(encoding="utf-8")
        cls.document=Document()
        cls.document.feed(cls.html)

    def test_scriptless_safe_accessible_diligence(self):
        doc=self.document
        self.assertEqual((doc.main,doc.h1,doc.scripts),(1,1,0))
        self.assertEqual(doc.lang,"en")
        self.assertEqual(doc.canon,[CANONICAL])
        self.assertLessEqual({"main","evidence","methods","limits"},doc.ids)
        self.assertIn("/assets/diligence.css",doc.styles)
        self.assertIn("script-src 'none'",self.html)
        self.assertIn("connect-src 'none'",self.html)

    def test_five_release_rails_are_in_order(self):
        positions=[self.html.index("1. Canonical GitHub"),
                   self.html.index("2. Hugging Face"),
                   self.html.index("3. Cloudflare"),
                   self.html.index("4. Python publication"),
                   self.html.index("5. Research and DOI")]
        self.assertEqual(positions,sorted(positions))
        self.assertEqual(self.html.count("<tbody>"),1)
        self.assertEqual(self.html.count("</tbody>"),1)

    def test_declared_snapshot_scope_and_nonclaims(self):
        for token in ("2026-11-17 19:49 UTC","2026-11-13",
                      "2026-11-17 19:37 UTC","SNAPSHOT","UNAVAILABLE",
                      "not an exhaustive semantic audit","No release was published",
                      "settlement","GitHub-to-Hub","no account data"):
            self.assertIn(token.lower(),self.html.lower())
        self.assertIn("Two unauthenticated GETs",self.html)
        self.assertIn("not established",self.html.lower())
        self.assertNotIn("100% production",self.html.lower())
        self.assertNotIn("revenue earned",self.html.lower())

    def test_external_links_https_and_current_canonical_source(self):
        urls=[a.get("href","") for a in self.document.links]
        required=("https://github.com/szl-holdings/a11oy",
                  "https://github.com/szl-holdings/szl-gov",
                  "https://huggingface.co/spaces/SZLHOLDINGS/a11oy",
                  "https://huggingface.co/spaces/SZLHOLDINGS/anatomy",
                  "https://pypi.org/org/szl-holdings/",
                  "https://github.com/szl-holdings/szl-papers")
        for url in required:self.assertIn(url,urls)
        for url in urls:
            value=urlsplit(url)
            if value.scheme:self.assertEqual(value.scheme,"https",url)
            self.assertNotIn("token=",url.lower())
            self.assertNotIn("key=",url.lower())
        self.assertIn("/diligence/",urls)
        self.assertIn("/record/",urls)

    def test_cross_surface_boundaries_are_not_fake_proofs(self):
        source=self.html.lower()
        for phrase in ("runtime stage running","model training",
                       "post method charging","signed origin payment-context",
                       "package/source parity","peer review"):
            self.assertIn(phrase,source)
        self.assertIn("no account data",source)


    def test_signed_python_supply_chain_does_not_transfer_sdk_provenance(self):
        source=self.html
        for value in ("2026-11-17 21:12", "21:19 UTC",
                      "eight wheel/sdist files", "Fulcio deployment environment",
                      "szl SDK 0.1.7 returned HTTP 404",
                      "signed publisher provenance is unavailable",
                      "No release was published in this review",
                      "full package/source parity"):
            self.assertIn(value.lower(),source.lower())
        urls={row.get("href") for row in self.document.links}
        for link in (
            "https://pypi.org/project/szl-calibration/0.1.1/",
            "https://pypi.org/project/szl-energy-attest/0.3.4/",
            "https://pypi.org/project/szl-evidence-mandate/0.1.2/",
            "https://pypi.org/project/szl-receipts/14.0.2/",
            "https://pypi.org/project/szl/0.1.7/",
            "https://github.com/szl-holdings/szl-gpu-bridge/issues/243",
        ):
            self.assertIn(link,urls)
        self.assertNotIn("five signed PyPI releases",source.lower())
        self.assertNotIn("szl SDK 0.1.7 proven signed",source.lower())
        self.assertNotIn("revenue earned",source.lower())


if __name__=="__main__":
    unittest.main()
