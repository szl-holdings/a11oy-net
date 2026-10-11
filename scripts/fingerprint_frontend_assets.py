#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Give staged frontend resources content-addressed URLs without changing data.

The canonical CSS/JS files remain available. Only stylesheet/script attributes
in staged HTML, CSS imports, and the two reviewed dynamic resource assignments
are rewritten in derived copies. JSON, inline scripts, evidence, and source
files are never rewritten. This module does not change provider cache policy.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from html.parser import HTMLParser
import json
import pathlib
import posixpath
import re
from urllib.parse import unquote, urlsplit, urlunsplit


MANIFEST = "frontend-assets.json"
SCHEMA = "szl.frontend-asset-manifest/v1"
SAME_ORIGIN = {"a11oy.net", "www.a11oy.net"}
# Explicit resource-loader sites, not arbitrary strings in application data.
JS_LOADERS = {
    "scripts/szl-flow-proof.js": (r"\bvar\s+SPECTRAL_STYLE\s*=\s*",),
    "scripts/szl-holo-proof-v2.js": (r"\bscript\.src\s*=\s*",),
}
QUOTED = r"(?P<quote>['\"])(?P<url>[^'\"\r\n]+)(?P=quote)"
CSS_IMPORTS = (
    re.compile(r"@import\s+url\(\s*" + QUOTED + r"\s*\)", re.I),
    re.compile(r"@import\s+" + QUOTED, re.I),
    re.compile(r"@import\s+url\(\s*(?P<url>[^)'\"\s]+)\s*\)", re.I),
)


@dataclass(frozen=True)
class Reference:
    start: int
    end: int
    url: str


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def target(owner: str, url: str, assets: set[str]) -> str | None:
    parsed = urlsplit(url)
    if parsed.scheme and parsed.scheme not in {"http", "https"}:
        return None
    if parsed.netloc and parsed.netloc.lower() not in SAME_ORIGIN:
        return None
    path = unquote(parsed.path)
    relative = path.lstrip("/") if path.startswith("/") else posixpath.join(
        posixpath.dirname(owner), path
    )
    relative = posixpath.normpath(relative)
    return relative if relative in assets else None


def version_url(url: str, alias: str) -> str:
    """Keep the URL's origin, directory, query and fragment; change its filename."""
    parsed = urlsplit(url)
    prefix = parsed.path.rsplit("/", 1)[0] + "/" if "/" in parsed.path else ""
    return urlunsplit((parsed.scheme, parsed.netloc,
                      prefix + pathlib.PurePosixPath(alias).name,
                      parsed.query, parsed.fragment))


def asset_references(owner: str, content: str) -> list[Reference]:
    references = []
    if owner.endswith(".css"):
        patterns = CSS_IMPORTS
    else:
        patterns = tuple(re.compile(prefix + QUOTED) for prefix in JS_LOADERS.get(owner, ()))
    for pattern in patterns:
        matches = list(pattern.finditer(content))
        if owner in JS_LOADERS and len(matches) != 1:
            raise ValueError(f"reviewed frontend loader changed or is ambiguous: {owner}")
        references.extend(Reference(*match.span("url"), match.group("url")) for match in matches)
    return sorted(references, key=lambda ref: ref.start)


class HTMLResources(HTMLParser):
    """Locate actual resource attributes without rewriting scripts, prose or JSON."""

    def __init__(self, content: str):
        super().__init__(convert_charrefs=False)
        self.references: list[Reference] = []
        self.line_offsets = [0]
        for match in re.finditer("\n", content):
            self.line_offsets.append(match.end())
        self.feed(content)
        self.close()

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "script":
            attribute = "src"
        elif tag == "link" and set((attributes.get("rel") or "").lower().split()) & {
            "stylesheet", "preload", "modulepreload"
        }:
            attribute = "href"
        else:
            return
        raw = self.get_starttag_text()
        line, column = self.getpos()
        offset = self.line_offsets[line - 1] + column
        pattern = re.compile(r"(?<![\w:-])" + attribute + r"\s*=\s*" + QUOTED, re.I)
        for match in pattern.finditer(raw):
            self.references.append(Reference(offset + match.start("url"),
                                             offset + match.end("url"), match.group("url")))

    handle_startendtag = handle_starttag


def replace_references(content: str, replacements: list[tuple[Reference, str]]) -> str:
    for reference, url in sorted(replacements, key=lambda item: item[0].start, reverse=True):
        content = content[:reference.start] + url + content[reference.end:]
    return content


def fingerprint(root: pathlib.Path, source_revision: str) -> dict:
    """Derive aliases and resource URLs in an already isolated Pages artifact."""
    if not re.fullmatch(r"[0-9a-f]{40}", source_revision):
        raise ValueError("frontend source revision must be an exact lowercase git SHA")
    root = root.resolve()
    if (root / MANIFEST).exists():
        raise ValueError("frontend manifest already exists; build in a fresh staging directory")
    originals = {
        path.relative_to(root).as_posix(): path.read_bytes()
        for directory in ("assets", "scripts")
        for path in sorted((root / directory).rglob("*"))
        if path.is_file() and path.suffix in {".css", ".js"}
    }
    assets = set(originals)
    resolved: dict[str, dict] = {}
    derived: dict[str, bytes] = {}
    visiting: set[str] = set()

    def resolve(owner: str) -> dict:
        if owner in resolved:
            return resolved[owner]
        if owner in visiting:
            raise ValueError(f"cyclic frontend asset dependency: {owner}")
        visiting.add(owner)
        content = originals[owner].decode("utf-8")
        replacements = []
        dependencies = []
        for reference in asset_references(owner, content):
            dependency = target(owner, reference.url, assets)
            if dependency is None:
                parsed = urlsplit(reference.url)
                local = not parsed.scheme and not parsed.netloc or parsed.netloc.lower() in SAME_ORIGIN
                if local and pathlib.PurePosixPath(parsed.path).suffix in {".css", ".js"}:
                    raise ValueError(f"unresolved frontend asset dependency: {owner} -> {reference.url}")
                continue
            bound = resolve(dependency)
            replacements.append((reference, version_url(reference.url, bound["served_path"])))
            dependencies.append(dependency)
        rendered = replace_references(content, replacements).encode("utf-8")
        sha256 = digest(rendered)
        path = pathlib.PurePosixPath(owner)
        alias = path.with_name(f"{path.stem}.{sha256}{path.suffix}").as_posix()
        if (root / alias).exists():
            raise ValueError(f"frontend alias collides with a tracked path: {alias}")
        entry = {"source_path": owner, "source_sha256": digest(originals[owner]),
                 "served_path": alias, "served_sha256": sha256,
                 "dependencies": sorted(set(dependencies))}
        derived[alias] = rendered
        resolved[owner] = entry
        visiting.remove(owner)
        return entry

    for owner in sorted(assets):
        resolve(owner)

    documents = {}
    rendered_documents = {}
    for path in sorted(root.rglob("*.html")):
        owner = path.relative_to(root).as_posix()
        original = path.read_bytes()
        content = original.decode("utf-8")
        replacements = []
        for reference in HTMLResources(content).references:
            dependency = target(owner, reference.url, assets)
            if dependency is not None:
                replacements.append((reference, version_url(reference.url, resolved[dependency]["served_path"])))
        if not replacements:
            continue
        rendered = replace_references(content, replacements).encode("utf-8")
        rendered_documents[owner] = rendered
        documents[owner] = {"source_sha256": digest(original), "served_sha256": digest(rendered),
                            "resource_references": len(replacements)}

    # Validate the whole dependency graph before writing any derived output.
    for alias, content in sorted(derived.items()):
        (root / alias).write_bytes(content)
    for owner, content in sorted(rendered_documents.items()):
        (root / owner).write_bytes(content)
    manifest = {"schema": SCHEMA, "source_revision": source_revision,
                "scope": "STATIC_FRONTEND_ASSET_DELIVERY_ONLY",
                "canonical_assets_preserved": True,
                "assets": {path: resolved[path] for path in sorted(resolved)},
                "documents": documents}
    (root / MANIFEST).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest
