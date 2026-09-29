#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build a GraphQL createCommitOnBranch request from the working-tree changes.

main requires verified commit signatures, and a pull request that carries an
unsigned commit cannot be merged into it. A commit made with a local
`git commit` and pushed with a workflow token is unsigned. A commit created
through the GraphQL createCommitOnBranch mutation is signed by GitHub, so
.github/workflows/hf-inventory-refresh.yml sends the regenerated files that way.

Usage (from the repository root):
  python3 scripts/verified_commit_payload.py OWNER/REPO BRANCH BASE_OID HEADLINE BODY > request.json
  gh api graphql --input request.json
"""

from __future__ import annotations

import base64
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

MUTATION = (
    "mutation($input: CreateCommitOnBranchInput!) {"
    " createCommitOnBranch(input: $input) { commit { oid url } } }"
)


def changed_paths(porcelain_z: bytes) -> tuple[list[str], list[str]]:
    """Split `git status --porcelain -z --untracked-files=all` into (write, delete)."""
    writes: list[str] = []
    deletes: list[str] = []
    for entry in porcelain_z.decode("utf-8").split("\0"):
        if not entry:
            continue
        code, path = entry[:2], entry[3:]
        if "R" in code or "C" in code:
            raise ValueError(f"rename or copy is not expected from the generator: {entry!r}")
        (deletes if "D" in code else writes).append(path)
    return sorted(writes), sorted(deletes)


def build_request(
    root: Path,
    repository: str,
    branch: str,
    base_oid: str,
    headline: str,
    body: str,
    porcelain_z: bytes,
) -> dict[str, Any]:
    writes, deletes = changed_paths(porcelain_z)
    if not writes and not deletes:
        raise ValueError("no working-tree change to commit")
    additions = [
        {"path": path, "contents": base64.b64encode((root / path).read_bytes()).decode("ascii")}
        for path in writes
    ]
    return {
        "query": MUTATION,
        "variables": {
            "input": {
                "branch": {"repositoryNameWithOwner": repository, "branchName": branch},
                "expectedHeadOid": base_oid,
                "message": {"headline": headline, "body": body},
                "fileChanges": {"additions": additions, "deletions": [{"path": p} for p in deletes]},
            }
        },
    }


def main(argv: list[str]) -> int:
    if len(argv) != 5:
        print(__doc__, file=sys.stderr)
        return 2
    repository, branch, base_oid, headline, body = argv
    porcelain = subprocess.run(
        ["git", "status", "--porcelain", "-z", "--untracked-files=all"],
        check=True,
        capture_output=True,
    ).stdout
    request = build_request(Path.cwd(), repository, branch, base_oid, headline, body, porcelain)
    json.dump(request, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
