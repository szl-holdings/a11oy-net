#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Rewrite health.json sha to a git object id.

Live GitHub Pages for this origin is still legacy branch deploy, so the
committed file cannot contain a future merge SHA. CI may stamp GITHUB_SHA
onto a Pages *artifact* without inventing uptime or claiming DSSE-LIVE.
This origin has no DSSE signer and no local key: signer stays unavailable.
ÑAWI owns the locked-proven formula count; this document does not.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys


ALLOWED_SIGNERS = ("DSSE-LIVE", "UNSIGNED-LOCAL", "unavailable")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
LOCKED_FORMULA_CLAIMS = (
    "exactly 8",
    "exactly eight",
    "locked-proven",
    "hardcoded-8",
)


def stamp(path: pathlib.Path, sha: str) -> dict:
    sha = sha.strip().lower()
    if sha.startswith("refs/"):
        raise ValueError("ref name is not a git object SHA")
    if not SHA_RE.fullmatch(sha):
        raise ValueError(f"sha must be a 40-char lowercase hex git object id, got {sha!r}")

    health = json.loads(path.read_text(encoding="utf-8"))
    signer = health.get("signer")
    if signer not in ALLOWED_SIGNERS:
        raise ValueError(
            "signer must be exactly one of DSSE-LIVE | UNSIGNED-LOCAL | unavailable"
        )
    if signer == "DSSE-LIVE":
        raise ValueError("refusing to stamp DSSE-LIVE; this origin has no DSSE signer")
    if signer == "UNSIGNED-LOCAL":
        raise ValueError("UNSIGNED-LOCAL is wrong here; this origin has no local key")
    if signer != "unavailable":
        raise ValueError("signer must stay unavailable on this origin")
    if health.get("probe_contract") != "STATIC_DOCUMENT":
        raise ValueError("probe_contract must remain STATIC_DOCUMENT")
    if health.get("dsse_live") != "NOT_CLAIMED":
        raise ValueError("dsse_live must remain NOT_CLAIMED")
    if health.get("uptime") != "NOT_MEASURED":
        raise ValueError("refusing to invent uptime")
    blob = json.dumps(health)
    for claim in LOCKED_FORMULA_CLAIMS:
        if claim in blob.lower() or claim in blob:
            raise ValueError("health.json must not carry ÑAWI locked-proven formula claims")

    health["sha"] = sha
    path.write_text(json.dumps(health, indent=2) + "\n", encoding="utf-8")
    return health


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stamp health.json sha to a git revision without inventing uptime"
    )
    parser.add_argument("--path", default="health.json")
    parser.add_argument("--sha", required=True, help="40-char git object id, usually GITHUB_SHA")
    args = parser.parse_args()
    try:
        stamp(pathlib.Path(args.path), args.sha)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"stamp_health_sha FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"OK: stamped sha={args.sha.strip().lower()} signer=unavailable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
