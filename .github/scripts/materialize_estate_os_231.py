#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build the Estate OS monolith from bounded public GitHub and Hugging Face APIs."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

EXPECTED = {
    "github": 117,
    "model": 44,
    "dataset": 33,
    "space": 16,
    "collection": 21,
}
DESIRED_RINGS = {
    "holographic": 6,
    "flagship": 8,
    "vertical": 57,
    "kernel": 50,
    "archive": 38,
    "docs": 64,
    "organ": 8,
}
RETRYABLE = {429, 500, 502, 503, 504}
USER_AGENT = "SZL-Estate-OS-Monolith/1.0"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def request_json(url: str, *, attempts: int = 6) -> Any:
    headers = {
        "Accept": "application/json",
        "Cache-Control": "no-cache",
        "User-Agent": USER_AGENT,
    }
    last: BaseException | None = None
    for attempt in range(attempts):
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code not in RETRYABLE or attempt + 1 == attempts:
                raise
            raw = exc.headers.get("Retry-After") if exc.headers else None
            try:
                delay = float(raw) if raw else float(2**attempt)
            except (TypeError, ValueError):
                delay = float(2**attempt)
            time.sleep(min(max(delay, 1.0), 60.0))
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last = exc
            if attempt + 1 == attempts:
                raise
            time.sleep(min(float(2**attempt), 30.0))
    raise RuntimeError(f"request did not converge: {type(last).__name__ if last else 'unknown'}")


def public_github_repositories() -> list[dict[str, Any]]:
    query = urllib.parse.quote("org:szl-holdings")
    first = request_json(
        f"https://api.github.com/search/repositories?q={query}&per_page=100&page=1"
    )
    if not isinstance(first, dict) or first.get("incomplete_results") is True:
        raise RuntimeError("GitHub public search was incomplete")
    total = int(first.get("total_count", -1))
    items = list(first.get("items", []))
    for page in range(2, math.ceil(total / 100) + 1):
        payload = request_json(
            f"https://api.github.com/search/repositories?q={query}&per_page=100&page={page}"
        )
        if not isinstance(payload, dict) or payload.get("incomplete_results") is True:
            raise RuntimeError(f"GitHub public search page {page} was incomplete")
        items.extend(payload.get("items", []))
    public = [row for row in items if isinstance(row, dict) and row.get("private") is False]
    by_name = {str(row.get("name")): row for row in public}
    if total != EXPECTED["github"] or len(by_name) != EXPECTED["github"]:
        raise RuntimeError(
            "GitHub inventory drift: "
            f"expected {EXPECTED['github']}, total={total}, unique_public={len(by_name)}"
        )
    return [by_name[name] for name in sorted(by_name, key=str.casefold)]


def list_payload(url: str, *, label: str) -> list[dict[str, Any]]:
    payload = request_json(url)
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = None
        for key in ("items", "collections", "data", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                rows = value
                break
        if rows is None:
            raise RuntimeError(f"{label} endpoint returned an unsupported object")
    else:
        raise RuntimeError(f"{label} endpoint returned {type(payload).__name__}")
    return [row for row in rows if isinstance(row, dict) and row.get("private") is not True]


def public_hf_inventory() -> dict[str, list[dict[str, Any]]]:
    base = "https://huggingface.co/api"
    inventory = {
        "model": list_payload(
            f"{base}/models?author=SZLHOLDINGS&limit=100&full=true",
            label="models",
        ),
        "dataset": list_payload(
            f"{base}/datasets?author=SZLHOLDINGS&limit=100&full=true",
            label="datasets",
        ),
        "space": list_payload(
            f"{base}/spaces?author=SZLHOLDINGS&limit=100&full=true",
            label="spaces",
        ),
        "collection": list_payload(
            f"{base}/collections?owner=SZLHOLDINGS&limit=100",
            label="collections",
        ),
    }
    for lane, expected in EXPECTED.items():
        if lane == "github":
            continue
        rows = inventory[lane]
        ids = {resource_id(row) for row in rows}
        if len(rows) != expected or len(ids) != expected or "" in ids:
            raise RuntimeError(
                f"Hugging Face {lane} drift: expected {expected}, "
                f"rows={len(rows)}, unique_ids={len(ids)}"
            )
    return inventory


def resource_id(row: dict[str, Any]) -> str:
    return str(
        row.get("id")
        or row.get("modelId")
        or row.get("datasetId")
        or row.get("slug")
        or row.get("name")
        or ""
    ).strip()


def slug(value: str) -> str:
    return value.rsplit("/", 1)[-1]


def license_from_tags(tags: list[str]) -> str | None:
    for tag in tags:
        if tag.startswith("license:"):
            return tag.split(":", 1)[1]
    return None


def old_assets() -> dict[tuple[str, str], dict[str, Any]]:
    raw = subprocess.check_output(
        ["git", "show", "origin/main:estate/os/data.json"],
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(raw)
    rows = payload.get("assets", [])
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        lane = str(row.get("lane") or "")
        name = str(row.get("name") or "")
        if lane and name:
            result[(lane, name.casefold())] = row
    return result


def match_old(
    index: dict[tuple[str, str], dict[str, Any]], lane: str, name: str, full_id: str
) -> dict[str, Any] | None:
    return index.get((lane, name.casefold())) or index.get((lane, full_id.casefold()))


def compact_description(value: Any, fallback: str) -> str:
    text = " ".join(str(value or fallback).split())
    return text[:280]


def github_asset(row: dict[str, Any], old: dict[tuple[str, str], dict[str, Any]]) -> dict[str, Any]:
    name = str(row["name"])
    prior = match_old(old, "github", name, str(row.get("full_name") or name))
    topics = [str(value) for value in row.get("topics", [])][:16]
    license_obj = row.get("license") if isinstance(row.get("license"), dict) else {}
    canonical = None
    if prior and isinstance(prior.get("urls"), dict):
        canonical = prior["urls"].get("canonical")
    return {
        "id": str(prior.get("id")) if prior else f"github:{name}",
        "lane": "github",
        "ring": str(prior.get("ring")) if prior else "",
        "name": name,
        "title": name,
        "description": compact_description(row.get("description"), f"Public SZL Holdings repository: {name}."),
        "updatedAt": row.get("pushed_at") or row.get("updated_at"),
        "language": row.get("language"),
        "license": license_obj.get("spdx_id"),
        "stars": int(row.get("stargazers_count") or 0),
        "likes": 0,
        "downloads": 0,
        "issues": int(row.get("open_issues_count") or 0),
        "archived": bool(row.get("archived")),
        "gated": False,
        "pinned": bool(prior.get("pinned")) if prior else False,
        "topics": topics,
        "urls": {
            "github": row.get("html_url"),
            "huggingface": prior.get("urls", {}).get("huggingface") if prior else None,
            "homepage": row.get("homepage") or None,
            "canonical": canonical,
        },
        "sha": None,
        "catalogHonesty": "MEASURED",
        "runtimeHonesty": "UNAVAILABLE",
        "runtimeNote": "Repository inventory only. Runtime was not probed by this static bake.",
    }


def hf_asset(
    lane: str,
    row: dict[str, Any],
    old: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    full_id = resource_id(row)
    name = slug(full_id)
    prior = match_old(old, lane, name, full_id)
    tags = [str(value) for value in row.get("tags", [])][:16]
    title = str(row.get("title") or row.get("name") or name)
    kind = {
        "model": "model",
        "dataset": "dataset",
        "space": "Space",
        "collection": "collection",
    }[lane]
    description = row.get("description")
    if not description and prior:
        description = prior.get("description")
    sdk = row.get("sdk") or row.get("pipeline_tag") or row.get("pipelineTag")
    return {
        "id": str(prior.get("id")) if prior else f"hf:{lane}:{full_id}",
        "lane": lane,
        "ring": str(prior.get("ring")) if prior else "",
        "name": name,
        "title": title,
        "description": compact_description(description, f"Public SZLHOLDINGS {kind}: {name}."),
        "updatedAt": row.get("lastModified") or row.get("last_modified") or row.get("updatedAt"),
        "language": sdk,
        "license": license_from_tags(tags),
        "stars": 0,
        "likes": int(row.get("likes") or 0),
        "downloads": int(row.get("downloads") or 0),
        "issues": 0,
        "archived": bool(row.get("disabled")),
        "gated": bool(row.get("gated")),
        "pinned": bool(prior.get("pinned")) if prior else False,
        "topics": tags,
        "urls": {
            "github": None,
            "huggingface": f"https://huggingface.co/{'spaces/' if lane == 'space' else 'datasets/' if lane == 'dataset' else 'collections/' if lane == 'collection' else ''}{full_id}",
            "homepage": None,
            "canonical": prior.get("urls", {}).get("canonical") if prior else None,
        },
        "sha": row.get("sha") or row.get("repository_sha"),
        "catalogHonesty": "MEASURED",
        "runtimeHonesty": "UNAVAILABLE",
        "runtimeNote": "Public Hub repository observed. Runtime and artifact quality were not inferred.",
    }


def preferred_ring(asset: dict[str, Any]) -> str:
    name = str(asset["name"]).casefold()
    words = " ".join([name, str(asset.get("description") or ""), " ".join(asset.get("topics", []))]).casefold()
    if asset.get("archived"):
        return "archive"
    if name in {
        "a11oy",
        "killinchu",
        "immune",
        "lyte",
        "terra",
        "counsel",
        "finance",
        "szl-khipu",
    }:
        return "flagship"
    if name in {"anatomy", "ayllu", "hatun", "second-brain", "szl-nemo", "szl-ouroboros", "szl-kernels", "szl-trust"}:
        return "organ"
    if any(token in words for token in ("holograph", "cosmos", "constellation", "atelier", "spectral", "threejs")):
        return "holographic"
    if asset["lane"] == "model" or any(token in words for token in ("kernel", "lean", "inference", "receipt", "governance", "provctl", "govsign", "forge")):
        return "kernel"
    if asset["lane"] in {"dataset", "collection"} or any(token in words for token in ("docs", "spec", "paper", "thesis", "readme", "profile", "evidence", "audit")):
        return "docs"
    return "vertical"


def assign_rings(assets: list[dict[str, Any]]) -> None:
    if sum(DESIRED_RINGS.values()) != len(assets):
        raise RuntimeError(
            f"ring capacity {sum(DESIRED_RINGS.values())} does not match assets {len(assets)}"
        )
    pairs: list[tuple[int, str, str, int]] = []
    for index, asset in enumerate(assets):
        old_ring = str(asset.get("ring") or "")
        preferred = preferred_ring(asset)
        words = " ".join(
            [str(asset["name"]), str(asset.get("description") or ""), " ".join(asset.get("topics", []))]
        ).casefold()
        for ring in DESIRED_RINGS:
            score = 0
            if old_ring == ring:
                score += 500
            if preferred == ring:
                score += 260
            if asset.get("archived"):
                score += 1200 if ring == "archive" else -1200
            if str(asset["name"]).casefold() in {
                "a11oy", "killinchu", "immune", "lyte", "terra", "counsel", "finance", "szl-khipu"
            }:
                score += 800 if ring == "flagship" else 0
            if "holograph" in words or "constellation" in words:
                score += 300 if ring == "holographic" else 0
            if asset["lane"] == "model":
                score += 180 if ring == "kernel" else 0
            if asset["lane"] in {"dataset", "collection"}:
                score += 130 if ring == "docs" else 0
            if ring == "vertical":
                score += 5
            pairs.append((score, str(asset["id"]), ring, index))
    pairs.sort(key=lambda row: (-row[0], row[1].casefold(), row[2]))
    remaining = dict(DESIRED_RINGS)
    assigned: dict[int, str] = {}
    for _score, _asset_id, ring, index in pairs:
        if index in assigned or remaining[ring] <= 0:
            continue
        assigned[index] = ring
        remaining[ring] -= 1
    if len(assigned) != len(assets) or any(remaining.values()):
        raise RuntimeError(f"ring allocation failed: assigned={len(assigned)} remaining={remaining}")
    for index, ring in assigned.items():
        assets[index]["ring"] = ring


def main() -> int:
    branch_manifest = json.loads(Path("estate/os/data.json").read_text(encoding="utf-8"))
    old = old_assets()
    github_rows = public_github_repositories()
    hf = public_hf_inventory()

    assets = [github_asset(row, old) for row in github_rows]
    for lane in ("model", "dataset", "space", "collection"):
        rows = sorted(hf[lane], key=lambda row: resource_id(row).casefold())
        assets.extend(hf_asset(lane, row, old) for row in rows)

    ids = [str(asset["id"]) for asset in assets]
    if len(assets) != 231 or len(set(ids)) != 231:
        raise RuntimeError(f"asset identity contract failed: rows={len(assets)} unique={len(set(ids))}")

    assign_rings(assets)
    lane_counts = Counter(str(asset["lane"]) for asset in assets)
    ring_counts = Counter(str(asset["ring"]) for asset in assets)
    if dict(lane_counts) != EXPECTED:
        raise RuntimeError(f"lane counts drifted after materialization: {dict(lane_counts)}")
    if dict(ring_counts) != DESIRED_RINGS:
        raise RuntimeError(f"ring counts drifted after allocation: {dict(ring_counts)}")

    captured = utc_now()
    sources = [
        {
            "id": "github.search.org:szl-holdings",
            "honesty": "MEASURED",
            "itemCount": EXPECTED["github"],
            "note": "Bounded public GitHub repository search; private names withheld.",
        },
        *[
            {
                "id": f"huggingface.{lane}s.author=SZLHOLDINGS" if lane != "collection" else "huggingface.collections.owner=SZLHOLDINGS",
                "honesty": "MEASURED",
                "itemCount": EXPECTED[lane],
                "note": "Bounded public Hub listing; runtime and quality not inferred.",
            }
            for lane in ("model", "dataset", "space", "collection")
        ],
        {
            "id": "estate.json.keep-7",
            "honesty": "MEASURED",
            "itemCount": 48,
            "note": "The 2026-08-31 org-authenticated spaces_public=48 observation remains separately labeled and is not overwritten.",
        },
    ]
    counts = {
        "assets": len(assets),
        "github": lane_counts["github"],
        "githubArchived": sum(
            1 for asset in assets if asset["lane"] == "github" and asset.get("archived")
        ),
        "space": lane_counts["space"],
        "spacePublic": lane_counts["space"],
        "spaceGated": sum(
            1 for asset in assets if asset["lane"] == "space" and asset.get("gated")
        ),
        "model": lane_counts["model"],
        "dataset": lane_counts["dataset"],
        "collection": lane_counts["collection"],
        "rings": dict(ring_counts),
        "githubSearchTotal": lane_counts["github"],
        "privateGithubUnavailable": "UNAVAILABLE",
    }
    data = {
        "contract": "szl.estate-hud.hologram/v1",
        "surface": branch_manifest["surface"],
        "capturedAt": captured,
        "scope": "PUBLIC_PARTIAL",
        "honesty": "UNSIGNED-honest",
        "lambda": "Conjecture 1 OPEN",
        "githubOrg": "szl-holdings",
        "hfOrg": "SZLHOLDINGS",
        "sources": sources,
        "counts": counts,
        "laterRecapture": branch_manifest["laterRecapture"],
        "priorBake": branch_manifest["priorBake"],
        "generation": {
            "state": "MEASURED_PUBLIC_INVENTORY",
            "ringClassification": "DERIVED_DETERMINISTIC_QUOTA",
            "runtimeProbesPerformed": False,
            "providerMutationsPerformed": False,
            "credentialValuesRecorded": False,
        },
        "assets": assets,
    }
    encoded = (json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    if len(encoded) > 200_000:
        raise RuntimeError(f"monolith exceeds bounded source size: {len(encoded)} bytes")
    Path("estate/os/data.json").write_bytes(encoded)

    bake = {key: value for key, value in data.items() if key != "assets"}
    bake["monolith"] = {
        "file": "./data.json",
        "bytes": len(encoded),
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "assetIdsSha256": hashlib.sha256("\n".join(sorted(ids)).encode("utf-8")).hexdigest(),
        "uniqueAssets": len(set(ids)),
    }
    Path("estate/os/bake.json").write_text(
        json.dumps(bake, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    receipt = {
        "schema": "szl.estate-os-materialization/v1",
        "generated_at": captured,
        "source_revision": os.getenv("GITHUB_SHA") or "LOCAL",
        "counts": counts,
        "monolith": bake["monolith"],
        "complete": True,
        "provider_mutations_performed": False,
        "credential_values_recorded": False,
    }
    Path("estate/os/materialization-receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
