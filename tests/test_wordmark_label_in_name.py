"""WCAG 2.5.3 Label in Name for the A11oy.net home wordmark.

A link whose aria-label replaces its visible text must contain that visible text,
so speech-input users can activate it by saying what they see ("A11OY Proof Registry").
"""
import html.parser
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class _Wordmarks(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.found = []  # (aria_label, visible_text)
        self._depth = 0
        self._hidden = 0
        self._label = None
        self._text = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in VOID:
            return
        if self._depth:
            self._depth += 1
            if a.get("aria-hidden") == "true" or self._hidden:
                self._hidden += 1
            return
        if tag == "a" and "wordmark" in (a.get("class") or "").split() and a.get("aria-label"):
            self._depth, self._label, self._text = 1, a["aria-label"], []

    def handle_endtag(self, tag):
        # HTMLParser also fires this for self-closing void tags such as <img />,
        # which handle_starttag ignored; they must not unbalance the depth.
        if tag in VOID or not self._depth:
            return
        if self._hidden:
            self._hidden -= 1
        self._depth -= 1
        if not self._depth:
            self.found.append((self._label, "".join(self._text)))

    def handle_data(self, data):
        if self._depth and not self._hidden:
            self._text.append(data)


def _words(text):
    return re.findall(r"[a-z0-9]+", text.casefold())


class WordmarkLabelInNameTest(unittest.TestCase):
    def test_every_wordmark_label_contains_its_visible_text(self):
        pages = 0
        for page in sorted(ROOT.rglob("*.html")):
            if "node_modules" in page.parts:
                continue
            parser = _Wordmarks()
            parser.feed(page.read_text(encoding="utf-8", errors="replace"))
            for label, visible in parser.found:
                seen, name = _words(visible), _words(label)
                if not seen:  # image-only wordmark: aria-label is its only name (2.5.3 n/a)
                    continue
                pages += 1
                joined = " ".join(name)
                self.assertIn(" ".join(seen), joined,
                              f"{page.relative_to(ROOT)}: aria-label {label!r} omits visible text {visible!r}")
        self.assertGreater(pages, 0, "no labelled wordmark links found")


if __name__ == "__main__":
    unittest.main()
