#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Stamp the exact Git source revision into an isolated Pages artifact.

The committed source witness is deliberately an unstamped template because a
Git commit cannot contain its own future object id. The Pages artifact builder
calls this module only after copying the exact Git tree into an isolated output
directory. No deployment, runtime, uptime, or signing claim is added.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any


SHA_RE = re.compile(r"^[0-9a-f]{40}$")
TEMPLATE_REVISION = "UNSTAMPED_BY_PAGES_ARTIFACT_BUILDER"
SCHEMA_VERSION = "a11oy-static-source-witness/v1"
SURFACE = "https://a11oy.net"
SOURCE_REPOSITORY = "https://github.com/szl-holdings/a11oy-net"
EXPECTED_KEYS = {
    "schema_version",
    "surface",
    "source_repository",
    "source_revision",
    "artifact_kind",
    "artifact_binding",
    "witness_semantics",
    "product_runtime_readiness",
    "uptime",
    "dsse_live",
    "generated_at_utc",
}


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_witness(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_keys,
    )
    if not isinstance(value, dict):
        raise ValueError("source witness must be a JSON object")
    return value


def validate_contract(witness: dict[str, Any], expected_revision: str) -> None:
    unexpected = set(witness) - EXPECTED_KEYS
    missing = EXPECTED_KEYS - set(witness)
    if unexpected or missing:
        details = []
        if missing:
            details.append("missing=" + ",".join(sorted(missing)))
        if unexpected:
            details.append("unexpected=" + ",".join(sorted(unexpected)))
        raise ValueError("source witness keys do not match the contract: " + " ".join(details))
    if witness["schema_version"] != SCHEMA_VERSION:
        raise ValueError("source witness schema_version is not canonical")
    if witness["surface"] != SURFACE:
        raise ValueError("source witness surface is not canonical")
    if witness["source_repository"] != SOURCE_REPOSITORY:
        raise ValueError("source witness repository is not canonical")
    if witness["source_revision"] != expected_revision:
        raise ValueError(
            f"source witness revision is {witness['source_revision']!r}, "
            f"expected {expected_revision!r}"
        )
    if witness["artifact_kind"] != "STATIC_GITHUB_PAGES":
        raise ValueError("source witness artifact_kind must remain STATIC_GITHUB_PAGES")
    if witness["artifact_binding"] != "EXACT_SOURCE_REVISION":
        raise ValueError("source witness artifact_binding must remain exact")
    if witness["product_runtime_readiness"] != "NOT_MEASURED":
        raise ValueError("source witness must not claim product runtime readiness")
    if witness["uptime"] != "NOT_MEASURED":
        raise ValueError("source witness must not claim uptime")
    if witness["dsse_live"] != "NOT_CLAIMED":
        raise ValueError("source witness must not claim DSSE-LIVE")
    if witness["generated_at_utc"] is not None:
        raise ValueError("source witness must not invent a generation timestamp")
    semantics = witness["witness_semantics"]
    if not isinstance(semantics, str) or not semantics.strip():
        raise ValueError("source witness semantics must be a non-empty string")


def stamp(path: pathlib.Path, source_revision: str) -> dict[str, Any]:
    source_revision = source_revision.strip().lower()
    if not SHA_RE.fullmatch(source_revision):
        raise ValueError("source revision must be a 40-character lowercase Git SHA")
    witness = load_witness(path)
    validate_contract(witness, TEMPLATE_REVISION)
    witness["source_revision"] = source_revision
    validate_contract(witness, source_revision)
    path.write_text(json.dumps(witness, indent=2) + "\n", encoding="utf-8")
    return witness


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", default=".well-known/szl-source.json")
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    try:
        witness = stamp(pathlib.Path(args.path), args.source_revision)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"stamp_source_witness FAILED: {exc}", file=sys.stderr)
        return 1
    print(
        "OK: stamped exact static source witness "
        f"revision={witness['source_revision']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
