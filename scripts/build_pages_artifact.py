#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build the exact-source GitHub Pages artifact in an isolated directory.

Only files tracked by the checked-out commit are admitted. GitHub control-plane
files are excluded, and ``health.json`` is stamped in the staging copy only.
The committed source tree is never rewritten by this builder.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

from stamp_health_sha import SHA_RE, stamp


EXCLUDED_TOP_LEVEL = {".git", ".github"}
REQUIRED_FILES = (
    ".nojekyll",
    ".well-known/security.txt",
    "404.html",
    "_headers",
    "api/build-info/index.html",
    "assets/a11oy-mark.svg",
    "assets/a11oy-net-social.png",
    "assets/diligence.css",
    "assets/kanchay.css",
    "atlas.json",
    "CHANGELOG.md",
    "chat/index.html",
    "code/index.html",
    "diligence/index.html",
    "estate-current.json",
    "estate-observed-2026-09-19.json",
    "evidence.json",
    "health.json",
    "index.html",
    "llms.txt",
    "manifest.webmanifest",
    "notes/index.html",
    "readyz/index.html",
    "record.json",
    "record/index.html",
    "robots.txt",
    "scripts/atlas_policy.js",
    "scripts/check_probe_policy.mjs",
    "scripts/estate_snapshot.js",
    "scripts/honest_kernel_bind.js",
    "scripts/probe_policy.js",
    "site.webmanifest",
    "sitemap.xml",
)


def _git(root: pathlib.Path, *args: str) -> bytes:
    return subprocess.check_output(("git", "-C", str(root), *args))


def _tracked_entries(
    root: pathlib.Path, source_revision: str
) -> list[tuple[pathlib.PurePosixPath, str, str]]:
    raw = _git(root, "ls-tree", "-rz", "--full-tree", source_revision)
    entries: list[tuple[pathlib.PurePosixPath, str, str]] = []
    for encoded_entry in raw.split(b"\0"):
        if not encoded_entry:
            continue
        metadata, encoded_path = encoded_entry.split(b"\t", 1)
        mode, object_type, object_id = metadata.decode("ascii").split()
        path = pathlib.PurePosixPath(encoded_path.decode("utf-8"))
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"unsafe tracked path: {path}")
        if path.parts[0] in EXCLUDED_TOP_LEVEL:
            continue
        if object_type != "blob":
            raise ValueError(f"non-file git object is not admitted: {path} ({object_type})")
        if mode == "120000":
            raise ValueError(f"symlinks are not admitted to the Pages artifact: {path}")
        if mode not in {"100644", "100755"}:
            raise ValueError(f"unsupported git mode for Pages artifact: {path} ({mode})")
        entries.append((path, mode, object_id))
    return entries


def _write_blobs(
    root: pathlib.Path,
    output: pathlib.Path,
    entries: list[tuple[pathlib.PurePosixPath, str, str]],
) -> None:
    process = subprocess.Popen(
        ("git", "-C", str(root), "cat-file", "--batch"),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    if process.stdin is None or process.stdout is None:
        raise OSError("unable to open git cat-file batch pipes")
    try:
        for relative, mode, object_id in entries:
            process.stdin.write(object_id.encode("ascii") + b"\n")
            process.stdin.flush()
            header = process.stdout.readline().decode("ascii").strip().split()
            if len(header) != 3 or header[1] != "blob":
                raise ValueError(f"unable to read source blob for {relative}: {header}")
            size = int(header[2])
            content = process.stdout.read(size)
            separator = process.stdout.read(1)
            if len(content) != size or separator != b"\n":
                raise ValueError(f"truncated source blob for {relative}")
            destination = output.joinpath(*relative.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            if mode == "100755":
                destination.chmod(destination.stat().st_mode | 0o111)
    finally:
        process.stdin.close()
        return_code = process.wait()
        process.stdout.close()
    if return_code:
        raise subprocess.CalledProcessError(return_code, process.args)


def build(root: pathlib.Path, output: pathlib.Path, source_revision: str) -> dict:
    root = root.resolve()
    output = output.resolve()
    source_revision = source_revision.strip().lower()

    if not SHA_RE.fullmatch(source_revision):
        raise ValueError("source revision must be a 40-character lowercase git SHA")
    actual = _git(root, "rev-parse", "HEAD").decode("ascii").strip().lower()
    if actual != source_revision:
        raise ValueError(f"checked-out source is {actual}, expected {source_revision}")
    if output == root or root in output.parents:
        raise ValueError("artifact output must be outside the source tree")
    if output.exists():
        raise ValueError(f"artifact output already exists: {output}")

    output.mkdir(parents=True)
    entries = _tracked_entries(root, source_revision)
    _write_blobs(root, output, entries)
    copied = len(entries)

    if any((output / excluded).exists() for excluded in EXCLUDED_TOP_LEVEL):
        raise ValueError("artifact contains a forbidden control-plane directory")
    missing = [path for path in REQUIRED_FILES if not (output / path).is_file()]
    if missing:
        raise ValueError("artifact is missing required files: " + ", ".join(missing))

    health = stamp(output / "health.json", source_revision)
    if health.get("sha") != source_revision:
        raise ValueError("staged health.json does not bind the exact source revision")
    if health.get("signer") != "unavailable":
        raise ValueError("staged health.json must preserve signer=unavailable")
    if health.get("probe_contract") != "STATIC_DOCUMENT":
        raise ValueError("staged health.json must preserve STATIC_DOCUMENT")
    if health.get("uptime") != "NOT_MEASURED":
        raise ValueError("staged health.json must not claim uptime")
    if health.get("dsse_live") != "NOT_CLAIMED":
        raise ValueError("staged health.json must not claim DSSE-LIVE")

    return {
        "status": "PAGES_ARTIFACT_STAGED",
        "source_revision": source_revision,
        "tracked_files_copied": copied,
        "excluded_top_level": sorted(EXCLUDED_TOP_LEVEL),
        "health_contract": {
            "sha": health["sha"],
            "signer": health["signer"],
            "probe_contract": health["probe_contract"],
            "uptime": health["uptime"],
            "dsse_live": health["dsse_live"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    try:
        receipt = build(
            pathlib.Path(args.root),
            pathlib.Path(args.output),
            args.source_revision,
        )
    except (OSError, ValueError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"build_pages_artifact FAILED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
