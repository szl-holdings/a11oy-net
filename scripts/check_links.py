# SPDX-License-Identifier: Apache-2.0
"""Link & Asset Check: committed HTML parses and local links/assets resolve.

Run from the site root, which is the repository root in CI:

    python3 scripts/check_links.py

Every *.html file below the working directory, outside .git, is parsed. Each
local href, src, poster and srcset reference, and the content of each <meta>
whose property or name ends in "image" (og:image, twitter:image), must resolve
to a file inside the site root. A #fragment into an HTML page must match an id
on that page, and sitemap.xml, when present, must be well-formed XML. URLs on
a11oy.net and www.a11oy.net are treated as local. Other origins and non-http(s)
schemes such as data:, mailto:, tel: and javascript: are not checked.

This is the inline step of .github/workflows/link-check.yml, moved here
unchanged so it can be tested (tests/test_check_links.py).
"""

import html.parser, pathlib, sys, urllib.parse
import xml.etree.ElementTree as ET

root = pathlib.Path(".").resolve()
same_origin = {"a11oy.net", "www.a11oy.net"}
errors = []

class Extractor(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []
        self.anchors = set()

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if d.get("id"):
            self.anchors.add("#" + d["id"])
        for key in ("href", "src", "poster"):
            if d.get(key):
                self.refs.append(d[key])
        if d.get("srcset"):
            self.refs.extend(
                candidate.strip().split()[0]
                for candidate in d["srcset"].split(",")
                if candidate.strip()
            )
        # og:image / twitter:image live in <meta content=...>
        ident = (d.get("property", "") + d.get("name", ""))
        if d.get("content") and ident.endswith("image"):
            self.refs.append(d["content"])

def local_target(htmlfile, ref):
    parsed = urllib.parse.urlparse(ref)
    if parsed.scheme and parsed.scheme not in ("http", "https"):
        return None
    if parsed.netloc and parsed.netloc.lower() not in same_origin:
        return None

    decoded = urllib.parse.unquote(parsed.path)
    if not decoded:
        candidate = root if parsed.netloc else htmlfile
    elif decoded.startswith("/"):
        candidate = root / decoded.lstrip("/")
    else:
        candidate = htmlfile.parent / decoded
    candidate = candidate.resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        errors.append(f"{htmlfile.relative_to(root)}: path escapes site root -> {ref}")
        return None

    candidates = [candidate]
    if decoded.endswith("/") or candidate.is_dir():
        candidates.insert(0, candidate / "index.html")
    elif not candidate.suffix:
        candidates.extend((candidate.with_suffix(".html"), candidate / "index.html"))
    target = next((path for path in candidates if path.is_file()), None)
    if target is None:
        errors.append(f"{htmlfile.relative_to(root)}: local target not found -> {ref}")
        return None
    return target

documents = {}
for htmlfile in sorted(root.rglob("*.html")):
    if ".git" in htmlfile.relative_to(root).parts:
        continue
    ex = Extractor()
    ex.feed(htmlfile.read_text(encoding="utf-8"))
    documents[htmlfile] = ex

for htmlfile, ex in documents.items():
    for ref in ex.refs:
        if not ref or ref.startswith(("data:", "mailto:", "tel:", "javascript:")):
            continue
        target = local_target(htmlfile, ref)
        if target is None:
            continue
        fragment = urllib.parse.unquote(urllib.parse.urlparse(ref).fragment)
        if fragment and target.suffix.lower() == ".html":
            target_document = documents.get(target)
            if target_document is None:
                target_document = Extractor()
                target_document.feed(target.read_text(encoding="utf-8"))
            if "#" + fragment not in target_document.anchors:
                errors.append(
                    f"{htmlfile.relative_to(root)}: fragment has no target -> {ref}"
                )

if (root / "sitemap.xml").exists():
    try:
        ET.parse(root / "sitemap.xml")
    except ET.ParseError as e:
        errors.append(f"sitemap.xml is not valid XML: {e}")

if errors:
    print("Link/asset check FAILED:")
    for e in errors:
        print(" -", e)
    sys.exit(1)
print("OK: HTML parses and all local links/assets resolve.")
