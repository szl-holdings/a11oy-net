#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail closed on unbound measurement labels in the historical proof records.

This checks publication integrity, not whether an external probe was honest.
Only a reviewed source-bound witness can support a future MEASURED label.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = ("evidence.json", "atlas.json", "estate.json", "origin.json")
LABEL_KEYS = frozenset({"evidence_class", "honesty", "class", "evidence"})
DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")


def _walk(value: Any, path: str = "$"):
    if isinstance(value, dict):
        yield path, value
        for key, child in value.items():
            yield from _walk(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, f"{path}[{index}]")


def _witness_path(root: Path, uri: str) -> Path | None:
    """Accept only a local, published evidence path; reject mutable remote URLs."""
    parsed = urlsplit(uri)
    if parsed.scheme or parsed.netloc:
        if parsed.scheme != "https" or parsed.netloc != "a11oy.net":
            return None
    if parsed.query or parsed.fragment or not parsed.path.startswith("/evidence/"):
        return None
    if "%" in parsed.path or "\\" in parsed.path:
        return None
    parts = parsed.path.split("/")
    if any(part in ("", ".", "..") for part in parts[1:]):
        return None
    root = root.resolve()
    target = (root / parsed.path.lstrip("/")).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        return None
    return target


def validate_binding(root: Path, node: dict[str, Any], path: str) -> list[str]:
    labels = [node.get(key) for key in LABEL_KEYS]
    measured = any(
        isinstance(value, str) and value.startswith("MEASURED") for value in labels
    )
    uri = node.get("evidence_uri")
    digest = node.get("evidence_digest")
    if not measured and uri is None and digest is None:
        return []
    if not isinstance(uri, str) or not uri:
        return [f"{path}: evidence_uri is required for a MEASURED/bound claim"]
    if not isinstance(digest, str) or not DIGEST.fullmatch(digest):
        return [f"{path}: evidence_digest must be sha256:<64 lowercase hex>"]
    target = _witness_path(root, uri)
    if target is None:
        return [f"{path}: evidence_uri must resolve to a local /evidence/ witness"]
    actual = hashlib.sha256(target.read_bytes()).hexdigest()
    if actual != digest.removeprefix("sha256:"):
        return [f"{path}: evidence_digest does not match witness bytes"]
    return []


def validate_documents(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    docs = {
        name: json.loads((root / name).read_text(encoding="utf-8"))
        for name in DOCUMENTS
    }
    for name, doc in docs.items():
        for path, node in _walk(doc):
            errors.extend(validate_binding(root, node, f"{name}{path[1:]}"))

    evidence, atlas, estate, origin = (docs[name] for name in DOCUMENTS)
    binding_status = evidence["measurement_binding"]
    if binding_status["state"] != "PARTIAL" or not binding_status["known_exceptions"]:
        errors.append("evidence.json: uncovered measurement surfaces must remain explicit")
    entrypoints = {item["name"]: item for item in evidence["entrypoints"]}
    for name in ("estate_snapshot", "estate_contract", "origin_lock_record", "origin_lock_contract"):
        if entrypoints[name]["evidence_class"] != "SNAPSHOT":
            errors.append(f"evidence.json: {name} must advertise the dated SNAPSHOT")
    for name, doc in (("atlas.json", atlas), ("estate.json", estate), ("origin.json", origin)):
        if doc["status"]["state"] != "HISTORICAL" or doc["status"]["current_state"] != "UNKNOWN":
            errors.append(f"{name}: old observation must be HISTORICAL with current_state UNKNOWN")
    if atlas["status"]["authenticated_state"] != "AUTH_REQUIRED":
        errors.append("atlas.json: current authenticated estate state requires authentication")
    if estate["status"]["authenticated_state"] != "AUTH_REQUIRED":
        errors.append("estate.json: current authenticated estate state requires authentication")
    for name, doc in (("atlas.json", atlas), ("estate.json", estate)):
        if doc["boundaries"]["spaces_deleted"] is not None:
            errors.append(f"{name}: public 401/listing cannot establish deletion")
        if doc["boundaries"]["current_spaces_deleted"] != "AUTH_REQUIRED":
            errors.append(f"{name}: current deletion state needs authenticated evidence")
    if estate["keys"]["complete_public_git_scan"] is not False:
        errors.append("estate.json: historical key scan must retain limited scope")
    for name in ("private_keys_in_public_git", "hmac_keys_in_public_git"):
        if estate["keys"][name] is not None:
            errors.append(f"estate.json: {name} cannot claim an estate-wide zero")
    origin_html = (root / "origin" / "index.html") if (root / "origin" / "index.html").is_file() else None
    if origin_html is not None:
        page = origin_html.read_text(encoding="utf-8")
        if origin["observed_at_utc"] not in page:
            errors.append("origin/index.html: latest machine-record timestamp must be visible")
        if "CLOSED-as-MEASURED" in page:
            errors.append("origin/index.html: unbound closure must not claim MEASURED")
    estate_html = (root / "estate" / "index.html") if (root / "estate" / "index.html").is_file() else None
    if estate_html is not None:
        page = estate_html.read_text(encoding="utf-8")
        if f"later {estate['captured_at'][:10]} machine snapshot" not in page:
            errors.append("estate/index.html: machine-link date must distinguish the later JSON snapshot")
    llms = (root / "llms.txt") if (root / "llms.txt").is_file() else None
    if llms is not None and "CLOSED-as-MEASURED" in llms.read_text(encoding="utf-8"):
        errors.append("llms.txt: unbound closure must not claim MEASURED")
    return errors


def main() -> int:
    try:
        errors = validate_documents()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Evidence binding contract FAILED: {exc}")
        return 1
    if errors:
        print("Evidence binding contract FAILED:")
        for error in errors:
            print(f" - {error}")
        return 1
    print("OK: historical evidence labels are bounded; MEASURED requires exact witness bytes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
