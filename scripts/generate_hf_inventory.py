#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate the a11oy.net Hugging Face inventory from the public Hub API.

One generator owns every Hub count this origin publishes. It reads the
unauthenticated public API only, so it never holds or needs a token and it
cannot write to the Hub. Private assets are invisible to it and are reported
as NOT_OBSERVED, never as zero.

Outputs (all deterministic for a given API observation):

  public-inventory.json               szl.public-hf-inventory/v4, full detail
  public-membership.json              canonical GitHub-bound public membership
  estate/canonical-hf-manifest.json    exact immutable canonical manifest bytes
  estate/hf-current.json              szl.hf-current/v1, the compact current
                                      counts that pages render
  live-align/hf_live_inventory.json   szl.live-align/v2, drift against the
                                      dated historical snapshots
  models.json                         generated hub block and per-model
                                      file-presence classification
  spaces.json                         generated hub_presence block only; the
                                      keep/fold policy rows are not rewritten
  index.html, estate/index.html,      elements marked data-hf-current and the
  estate/os/index.html,               generated live-Space rows
  atelier/index.html, notes/index.html

When the observed content is unchanged, the committed observed_at is kept, so
a rerun produces byte-identical files and the refresh workflow opens no PR.

Usage:
  python3 scripts/generate_hf_inventory.py              # live, write files
  python3 scripts/generate_hf_inventory.py --dry-run    # live, report only
  python3 scripts/generate_hf_inventory.py --fixture DIR --observed-at T
"""

from __future__ import annotations

import argparse
import copy
import fnmatch
import hashlib
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
ORG = "SZLHOLDINGS"
API = "https://huggingface.co/api"
GENERATOR = "scripts/generate_hf_inventory.py"
REFRESH_WORKFLOW = ".github/workflows/hf-inventory-refresh.yml"

SCHEMA_INVENTORY = "szl.public-hf-inventory/v4"
SCHEMA_CURRENT = "szl.hf-current/v1"
SCHEMA_LIVE_ALIGN = "szl.live-align/v2"
OBSERVATION_MODE = "UNAUTHENTICATED_PUBLIC_API_SNAPSHOT"
SPECIAL_SPACES = ("README",)
CANONICAL_REPOSITORY = "szl-holdings/a11oy"
CANONICAL_PATH = "docs/huggingface-ecosystem-manifest.json"
MEMBERSHIP_PATH = "public-membership.json"
CANONICAL_COPY_PATH = "estate/canonical-hf-manifest.json"
PUBLIC_SCOPE = {
    "id": "hf-public-author-membership/v1", "authentication": "none",
    "visibility": "public-only", "kinds": ["models", "datasets", "spaces"],
    "include_gated_metadata": True, "include_disabled_metadata": True,
    "include_reserved_readme_if_public": True,
    "kernel_policy": "count-once-as-model-repository-not-a-fourth-kind",
    "collections_and_buckets": "outside-repository-membership-scope",
    "portfolio_and_operational_policy": False,
}

INVENTORY_PATH = "public-inventory.json"
CURRENT_PATH = "estate/hf-current.json"
LIVE_ALIGN_PATH = "live-align/hf_live_inventory.json"
MODELS_PATH = "models.json"
SPACES_PATH = "spaces.json"
HISTORICAL_INVENTORY_PATH = "public-inventory-2026-08-31.json"
HISTORICAL_ESTATE_PATH = "estate.json"
PAGES = (
    "index.html",
    "estate/index.html",
    "estate/os/index.html",
    "atelier/index.html",
    "notes/index.html",
)

# The front door withholds Killinchu-named resources by standing policy; the
# same rule lives in scripts/inventory_cards.js (isWithheld).
WITHHELD = re.compile(r"killinchu", re.IGNORECASE)
# A Hub-authored string that names the foreign storefront outside a guard
# context would fail the org forbidden-domain gate, so it is refused here.
FORBIDDEN_DOMAIN = re.compile(r"(?<!-)a11oy\.com", re.IGNORECASE)

EXPAND = {
    "models": (
        "sha", "lastModified", "cardData", "pipeline_tag", "library_name",
        "siblings", "gated", "private", "tags",
    ),
    "datasets": ("sha", "lastModified", "cardData", "gated", "private", "tags"),
    "spaces": (
        "sha", "lastModified", "cardData", "sdk", "private", "subdomain",
        "runtime", "tags",
    ),
    "kernels": (
        "sha", "lastModified", "tags", "private", "gated",
        "supportedDriverFamilies",
    ),
}

WEIGHT_SUFFIXES = (".safetensors", ".gguf", ".npz")
WEIGHT_BIN = re.compile(r"(^|/)(pytorch_model|adapter_model|model)[^/]*\.bin$")
CARD_ONLY_FILES = re.compile(
    r"^(\.gitattributes|README\.md|LICENSE|bom/model-bom\.cdx\.json|"
    r"provenance\.json|status\.json)$"
)
CLASS_ORDER = (
    "TRAINED_WEIGHTS",
    "ROADMAP_EMPTY",
    "NANO_SYNTHETIC",
    "KERNEL_SOFTWARE",
    "CODE_OR_SCRIPTS",
)


class GenerationError(RuntimeError):
    """Raised when an observation cannot be turned into honest output."""


# --------------------------------------------------------------------------
# Sources: the live public API, or a fixture directory with the same shapes.
# --------------------------------------------------------------------------


# Page sizes requested from the listing endpoints. A listing that comes back
# this full may have been cut by the page size, so it is refused rather than
# published as a complete count.
LISTING_LIMIT = {"models": 1000, "datasets": 1000, "spaces": 1000, "kernels": 1000, "collections": 100}


def list_url(kind: str) -> str:
    query = [("author", ORG), ("limit", str(LISTING_LIMIT[kind]))]
    query += [("expand[]", field) for field in EXPAND[kind]]
    return f"{API}/{kind}?" + urllib.parse.urlencode(query)


def public_list_url(kind: str) -> str:
    """The plain URL a reader can open to repeat the observation."""
    if kind == "collections":
        return f"{API}/collections?owner={ORG}&limit={LISTING_LIMIT['collections']}"
    if kind == "buckets":
        return f"{API}/buckets/{ORG}"
    return f"{API}/{kind}?author={ORG}"


class LiveSource:
    """Unauthenticated GETs against the public Hub API. No token is read."""

    def __init__(self, attempts: int = 3, timeout: float = 30.0) -> None:
        self.attempts = attempts
        self.timeout = timeout

    def _bytes(self, url: str) -> bytes:
        last: Exception | None = None
        for attempt in range(self.attempts):
            request = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "a11oy-net-hf-inventory/1 (+https://a11oy.net/)",
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    return response.read()
            except Exception as exc:  # retried, then surfaced
                last = exc
                time.sleep(2 * (attempt + 1))
        raise GenerationError(f"GET {url} failed: {last}")

    def _get(self, url: str) -> Any:
        try:
            return json.loads(self._bytes(url).decode("utf-8"))
        except (UnicodeError, ValueError) as exc:
            raise GenerationError("public metadata JSON unavailable or malformed") from exc

    def canonical_source(self) -> dict[str, Any]:
        commit = self._get(f"https://api.github.com/repos/{CANONICAL_REPOSITORY}/commits/main")
        revision = commit.get("sha") if isinstance(commit, dict) else None
        verification = commit.get("commit", {}).get("verification", {}) if isinstance(commit, dict) else {}
        if (not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision)
                or not isinstance(verification, dict) or verification.get("verified") is not True):
            raise GenerationError("canonical main revision or valid commit signature unavailable")
        metadata = self._get(
            f"https://api.github.com/repos/{CANONICAL_REPOSITORY}/contents/{CANONICAL_PATH}?ref={revision}"
        )
        if not isinstance(metadata, dict) or metadata.get("type") != "file" or metadata.get("path") != CANONICAL_PATH:
            raise GenerationError("canonical manifest Git blob metadata unavailable")
        raw = self._bytes(f"https://raw.githubusercontent.com/{CANONICAL_REPOSITORY}/{revision}/{CANONICAL_PATH}")
        return canonical_source(raw, revision, metadata.get("sha"))

    def validate_source_head(self, revision: str) -> None:
        current = self._get(f"https://api.github.com/repos/{CANONICAL_REPOSITORY}/commits/main")
        if not isinstance(current, dict) or current.get("sha") != revision:
            raise GenerationError("canonical main advanced during the public observation")

    def listing(self, kind: str) -> list[dict[str, Any]]:
        if kind == "collections":
            payload = self._get(public_list_url("collections"))
        elif kind == "buckets":
            payload = self._get(f"{API}/buckets/{ORG}")
        else:
            payload = self._get(list_url(kind))
        if not isinstance(payload, list):
            raise GenerationError(f"{kind} listing returned {type(payload).__name__}")
        return payload

    def space(self, name: str) -> dict[str, Any]:
        return self._get(f"{API}/spaces/{ORG}/{name}")

    def collection(self, slug: str) -> dict[str, Any]:
        return self._get(f"{API}/collections/{slug}")

    def bucket_tree(self, bucket_id: str) -> list[dict[str, Any]]:
        payload = self._get(f"{API}/buckets/{bucket_id}/tree?recursive=true")
        if not isinstance(payload, list):
            raise GenerationError(f"bucket tree {bucket_id} returned {type(payload).__name__}")
        return payload


def fixture_name(*parts: str) -> str:
    return "__".join(re.sub(r"[^A-Za-z0-9._-]", "_", part) for part in parts) + ".json"


class FixtureSource:
    """Reads API-shaped JSON from a directory; used by tests and dry runs."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def _read(self, name: str) -> Any:
        return json.loads((self.directory / name).read_text(encoding="utf-8"))

    def listing(self, kind: str) -> list[dict[str, Any]]:
        return self._read(fixture_name(kind))

    def space(self, name: str) -> dict[str, Any]:
        return self._read(fixture_name("space", name))

    def collection(self, slug: str) -> dict[str, Any]:
        return self._read(fixture_name("collection", slug))

    def bucket_tree(self, bucket_id: str) -> list[dict[str, Any]]:
        return self._read(fixture_name("bucket_tree", bucket_id))

    def canonical_source(self) -> dict[str, Any]:
        metadata = self._read("canonical_source.json")
        return canonical_source(
            (self.directory / "canonical_manifest.json").read_bytes(),
            metadata.get("source_revision"), metadata.get("source_git_blob"),
        )

    def validate_source_head(self, revision: str) -> None:
        if self._read("canonical_source.json").get("source_revision") != revision:
            raise GenerationError("fixture source advanced during the public observation")


def collect(source: Any) -> dict[str, Any]:
    raw: dict[str, Any] = {"canonical_source": source.canonical_source()}
    for kind in ("models", "datasets", "spaces", "kernels", "collections", "buckets"):
        raw[kind] = source.listing(kind)
        limit = LISTING_LIMIT.get(kind)
        if limit is not None and len(raw[kind]) >= limit:
            raise GenerationError(
                f"{kind} listing returned {len(raw[kind])} rows, the page size; it may be truncated"
            )
    raw["special_spaces"] = {name: source.space(name) for name in SPECIAL_SPACES}
    raw["collection_detail"] = {
        str(item["slug"]): source.collection(str(item["slug"]))
        for item in raw["collections"]
    }
    raw["bucket_tree"] = {
        str(item["id"]): source.bucket_tree(str(item["id"])) for item in raw["buckets"]
    }
    source.validate_source_head(raw["canonical_source"]["record"]["source_revision"])
    return raw


# --------------------------------------------------------------------------
# Normalisation helpers
# --------------------------------------------------------------------------


def hub_text(value: Any) -> str | None:
    """A Hub-authored string, cleaned for publication, or None."""
    if not isinstance(value, str):
        return None
    text = value.encode("utf-8", "replace").decode("utf-8").strip()
    text = re.sub(r"\s+", " ", text)
    if not text:
        return None
    if FORBIDDEN_DOMAIN.search(text):
        raise GenerationError(
            "Hub metadata names the foreign storefront domain; refusing to publish it: "
            + text[:80]
        )
    return text


def license_of(item: dict[str, Any]) -> str | None:
    card = item.get("cardData") if isinstance(item.get("cardData"), dict) else {}
    value = card.get("license")
    if isinstance(value, list):
        value = value[0] if value else None
    if isinstance(value, str) and value.strip():
        return value.strip()
    for tag in item.get("tags") or []:
        if isinstance(tag, str) and tag.startswith("license:"):
            return tag.split(":", 1)[1] or None
    return None


def siblings_of(item: dict[str, Any]) -> list[str]:
    return sorted(
        str(entry["rfilename"])
        for entry in item.get("siblings") or []
        if isinstance(entry, dict) and entry.get("rfilename")
    )


def by_id(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    ordered = []
    for item in sorted(items, key=lambda entry: str(entry.get("id"))):
        ident = str(item.get("id") or "")
        if not ident.startswith(ORG + "/"):
            raise GenerationError(f"listing row outside {ORG}: {ident!r}")
        if ident in seen:
            raise GenerationError(f"duplicate listing row: {ident}")
        if item.get("private") is not False:
            raise GenerationError("unauthenticated listing lacks an explicit public disposition")
        seen.add(ident)
        ordered.append(item)
    return ordered


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def canonical_source(raw: bytes, revision: str, blob: str) -> dict[str, Any]:
    """Bind exact GitHub bytes; ambiguity, privacy, or malformed scope denies output."""
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise GenerationError("duplicate canonical manifest key")
            value[key] = item
        return value

    def nonfinite(_value: str) -> Any:
        raise GenerationError("nonfinite canonical manifest value")

    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise GenerationError("canonical source revision must be an immutable Git SHA")
    actual_blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if not isinstance(blob, str) or blob != actual_blob:
        raise GenerationError("canonical source Git blob does not bind the retained bytes")
    try:
        text = raw.decode("utf-8")
        manifest = json.loads(text, object_pairs_hook=unique_object, parse_constant=nonfinite)
        canonical(manifest)  # Reject numeric overflow as well as NaN/Infinity literals.
    except (UnicodeError, ValueError) as exc:
        raise GenerationError("canonical manifest is unavailable or malformed") from exc
    scope = manifest.get("inventoryScope") if isinstance(manifest, dict) else None
    counts = manifest.get("counts") if isinstance(manifest, dict) else None
    inventory = manifest.get("inventory") if isinstance(manifest, dict) else None
    if not (
        isinstance(manifest, dict) and manifest.get("schemaVersion") == 2
        and manifest.get("org") == ORG and isinstance(scope, dict)
        and scope.get("visibility") == "public-only"
        and scope.get("authenticated") is False and scope.get("privateAssetsIncluded") is False
        and isinstance(counts, dict) and set(counts) == set(PUBLIC_SCOPE["kinds"])
        and all(type(counts[kind]) is int and counts[kind] >= 0 for kind in PUBLIC_SCOPE["kinds"])
        and isinstance(inventory, dict) and valid_timestamp(manifest.get("observedAt", ""))
    ):
        raise GenerationError("canonical public membership schema or scope is unavailable")
    ids: dict[str, list[str]] = {}
    for kind in PUBLIC_SCOPE["kinds"]:
        rows = inventory.get(kind)
        if not isinstance(rows, list) or any(not isinstance(row, dict) or row.get("private") is not False for row in rows):
            raise GenerationError(f"canonical {kind} public disposition unavailable")
        ids[kind] = [row["id"] for row in by_id(rows)]
        if counts[kind] != len(ids[kind]):
            raise GenerationError(f"canonical {kind} count does not bind its complete membership")
    record = {
        "schema": "szl.public-profile-inventory/v1", "scope": PUBLIC_SCOPE,
        "scope_sha256": hashlib.sha256(canonical(PUBLIC_SCOPE)).hexdigest(),
        "counts": counts, "observed_at": manifest["observedAt"],
        "source_repository": CANONICAL_REPOSITORY, "source_path": CANONICAL_PATH,
        "source_revision": revision, "source_git_blob": blob,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "production_authorization": False, "runtime_readiness_inferred": False,
        "model_quality_inferred": False, "historical_portfolio_contract_replaced": False,
        "retained_source_path": "/" + CANONICAL_COPY_PATH,
        "historical_snapshots": [{"path": "/public-membership.observed-2026-09-10.json",
                                  "observed_at": "2026-09-10T03:20:41Z"}],
    }
    return {"record": record, "ids": ids, "manifest_text": text}


def space_live_url(ident: str, sdk: str | None, subdomain: str | None) -> str:
    host = subdomain or ("szlholdings-" + ident.split("/", 1)[1].lower().replace(".", "-"))
    suffix = ".static.hf.space" if sdk == "static" else ".hf.space"
    return f"https://{host}{suffix}/"


# --------------------------------------------------------------------------
# public-inventory.json
# --------------------------------------------------------------------------


def model_row(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "gated": item.get("gated") not in (None, False),
        "id": item["id"],
        "last_modified": item.get("lastModified"),
        "library_name": item.get("library_name"),
        "license": license_of(item),
        "pipeline_tag": item.get("pipeline_tag"),
        "repository_sha": item.get("sha"),
        "source_observation": "PUBLIC_HF_REPOSITORY_OBSERVED",
    }


def dataset_row(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "gated": item.get("gated") not in (None, False),
        "id": item["id"],
        "last_modified": item.get("lastModified"),
        "license": license_of(item),
        "repository_sha": item.get("sha"),
        "source_observation": "PUBLIC_HF_REPOSITORY_OBSERVED",
    }


def space_row(item: dict[str, Any], special: bool) -> dict[str, Any]:
    ident = str(item["id"])
    card = item.get("cardData") if isinstance(item.get("cardData"), dict) else {}
    sdk = item.get("sdk") or card.get("sdk")
    runtime = item.get("runtime") if isinstance(item.get("runtime"), dict) else {}
    stage = runtime.get("stage") if isinstance(runtime.get("stage"), str) else None
    runtime_sha = runtime.get("sha") if isinstance(runtime.get("sha"), str) else None
    if runtime_sha is None:
        revision = "RUNTIME_SHA_NOT_REPORTED"
    elif runtime_sha == item.get("sha"):
        revision = "MATCHES_REPOSITORY_HEAD"
    else:
        revision = "DIFFERS_FROM_REPOSITORY_HEAD"
    hardware = runtime.get("hardware") if isinstance(runtime.get("hardware"), dict) else {}
    return {
        "canonical_live_url": space_live_url(ident, sdk, item.get("subdomain")),
        "hub_url": f"https://huggingface.co/spaces/{ident}",
        "id": ident,
        "last_modified": item.get("lastModified"),
        "license": license_of(item),
        "listing": "SPECIAL_SPACE_OUTSIDE_LIST_API" if special else "AUTHOR_LIST_API",
        "repository_sha": item.get("sha"),
        "runtime": {
            "evidence_url": f"{API}/spaces/{ident}",
            "hardware": hardware.get("current") if isinstance(hardware.get("current"), str) else None,
            "interpretation": "PROVIDER_REPORTED_STAGE_NOT_QUALITY_OR_FRESHNESS",
            "observation_state": "SPACE_API_OBSERVED" if stage else "STAGE_NOT_REPORTED",
            "repository_revision_state": revision,
            "runtime_sha": runtime_sha,
            "stage": stage,
        },
        "sdk": sdk,
        "title": hub_text(card.get("title")),
    }


def kernel_row(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "gated": item.get("gated") not in (None, False),
        "hub_url": f"https://huggingface.co/kernels/{item['id']}",
        "id": item["id"],
        "last_modified": item.get("lastModified"),
        "license": license_of(item),
        "repository_sha": item.get("sha"),
        "source_observation": "PUBLIC_HF_KERNEL_REPOSITORY_OBSERVED",
        "supported_driver_families": sorted(item.get("supportedDriverFamilies") or []),
    }


def collection_row(summary: dict[str, Any], detail: dict[str, Any]) -> dict[str, Any]:
    items = detail.get("items") if isinstance(detail.get("items"), list) else []
    rows = sorted(
        (
            {"id": str(entry.get("id")), "position": entry.get("position"), "type": entry.get("type")}
            for entry in items
            if isinstance(entry, dict) and entry.get("id")
        ),
        key=lambda row: (row["position"] if isinstance(row["position"], int) else 10**9, row["type"] or "", row["id"]),
    )
    return {
        "item_count": len(rows),
        "items": rows,
        "last_updated": detail.get("lastUpdated") or summary.get("lastUpdated"),
        "slug": str(summary["slug"]),
        "title": hub_text(detail.get("title") or summary.get("title")),
    }


def bucket_row(item: dict[str, Any], tree: list[dict[str, Any]]) -> dict[str, Any]:
    files = [entry for entry in tree if isinstance(entry, dict) and entry.get("type") == "file"]
    return {
        "created_at": item.get("createdAt"),
        "id": item["id"],
        "observed_object_count": len(files),
        "observed_size_bytes": sum(int(entry.get("size") or 0) for entry in files),
        "provider_reported_object_count": item.get("totalFiles"),
        "provider_reported_size_bytes": item.get("size"),
        "source_observation": "PUBLIC_HF_BUCKET_OBSERVED",
        "tree_evidence_url": f"{API}/buckets/{item['id']}/tree?recursive=true",
        "updated_at": item.get("updatedAt"),
        "visibility": "PRIVATE" if item.get("private") else "PUBLIC",
    }


def coverage(ids: list[str], covered: set[str]) -> dict[str, Any]:
    missing = sorted(set(ids) - covered)
    total = len(ids)
    hit = total - len(missing)
    return {
        "covered": hit,
        "interpretation": "MEMBERSHIP_IN_AT_LEAST_ONE_PUBLIC_COLLECTION",
        "missing_ids": missing,
        "state": "COMPLETE" if not missing else ("NONE" if hit == 0 else "PARTIAL"),
        "total": total,
    }


def inventory_content_sha(inventory: dict[str, Any]) -> str:
    body = {k: v for k, v in inventory.items() if k not in ("observed_at", "content_sha256")}
    return hashlib.sha256(canonical(body)).hexdigest()


def build_inventory(raw: dict[str, Any], observed_at: str) -> dict[str, Any]:
    models = [model_row(item) for item in by_id(raw["models"])]
    datasets = [dataset_row(item) for item in by_id(raw["datasets"])]
    listed_spaces = by_id(raw["spaces"])
    listed_ids = {str(item["id"]) for item in listed_spaces}
    specials = []
    for name, payload in sorted(raw["special_spaces"].items()):
        ident = f"{ORG}/{name}"
        if not isinstance(payload, dict) or payload.get("id") != ident:
            raise GenerationError("reserved Space metadata does not bind the requested repository")
        if ident in listed_ids or payload.get("private") is True:
            continue
        if payload.get("private") is not False:
            raise GenerationError("reserved Space public disposition unavailable")
        specials.append(payload)
    spaces = sorted(
        [space_row(item, False) for item in listed_spaces]
        + [space_row(item, True) for item in specials],
        key=lambda row: row["id"],
    )
    kernels = [kernel_row(item) for item in by_id(raw["kernels"])]
    model_ids = {row["id"] for row in models}
    if {row["id"] for row in kernels} - model_ids:
        raise GenerationError("kernel subset has repositories absent from the public model membership")
    binding = raw.get("canonical_source")
    if not isinstance(binding, dict) or not isinstance(binding.get("record"), dict):
        raise GenerationError("canonical public membership source binding unavailable")
    for kind, rows in (("models", models), ("datasets", datasets), ("spaces", spaces)):
        if sorted(row["id"] for row in rows) != binding.get("ids", {}).get(kind):
            raise GenerationError(f"observed {kind} membership differs from immutable canonical GitHub source")
    collections = sorted(
        (
            collection_row(item, raw["collection_detail"].get(str(item["slug"]), item))
            for item in raw["collections"]
            if item.get("private") is not True
        ),
        key=lambda row: row["slug"],
    )
    buckets = sorted(
        (
            bucket_row(item, raw["bucket_tree"].get(str(item["id"]), []))
            for item in raw["buckets"]
            if item.get("private") is not True
        ),
        key=lambda row: row["id"],
    )
    members: dict[str, set[str]] = {"model": set(), "dataset": set(), "space": set(), "bucket": set()}
    for row in collections:
        for entry in row["items"]:
            if entry["type"] in members:
                members[entry["type"]].add(entry["id"])
    repository_membership = len(models) + len(datasets) + len(spaces)
    hub_artifacts = repository_membership + len(collections)
    counts = {
        "buckets": len(buckets),
        "collections": len(collections),
        "datasets": len(datasets),
        "hub_artifacts_total": hub_artifacts,
        "kernels": len(kernels),
        "models": len(models),
        "public_resources_total": hub_artifacts + len(buckets),
        "repository_membership_total": repository_membership,
        "spaces": len(spaces),
        "spaces_list_api_rows": len(listed_spaces),
        "special_spaces_added": len(specials),
    }
    stages = Counter(row["runtime"]["stage"] or "NOT_REPORTED" for row in spaces)
    inventory = {
        "claim_boundaries": {
            "github_alignment": "EXACT_IMMUTABLE_MANIFEST_MEMBERSHIP_ONLY_NOT_RUNTIME_PARITY",
            "kernel_membership": "MODEL_SUBSET_COUNTED_ONCE_IN_TOTALS",
            "collections_and_buckets": "OUTSIDE_REPOSITORY_MEMBERSHIP_SCOPE",
            "license": "HUB_CARD_OR_TAG_METADATA_ONLY_NOT_LEGAL_REVIEW",
            "private_assets": "NOT_OBSERVED",
            "runtime_quality": "NOT_INFERRED_FROM_STAGE",
            "source_metadata": "REPORTED_OR_FILE_PRESENCE_ONLY_NOT_BUILD_PROVENANCE",
        },
        "collection_coverage": {
            "buckets": coverage([row["id"] for row in buckets], members["bucket"]),
            "datasets": coverage([row["id"] for row in datasets], members["dataset"]),
            "models": coverage([row["id"] for row in models], members["model"]),
            "spaces": coverage([row["id"] for row in spaces], members["space"]),
        },
        "counts": counts,
        "endpoints": {
            "buckets": public_list_url("buckets"),
            "collections": public_list_url("collections"),
            "datasets": public_list_url("datasets"),
            "kernels": public_list_url("kernels"),
            "models": public_list_url("models"),
            "spaces": public_list_url("spaces"),
            "special_spaces": [f"{API}/spaces/{ORG}/{name}" for name in SPECIAL_SPACES],
        },
        "generated_by": GENERATOR,
        "historical_snapshots": [
            {"observed_at": "2026-08-31T18:59:11Z", "path": "/" + HISTORICAL_INVENTORY_PATH, "schema": "szl.public-hf-inventory/v3"},
        ],
        "observation_mode": OBSERVATION_MODE,
        "observed_at": observed_at,
        "organization": ORG,
        "private_assets": "NOT_OBSERVED",
        "resources": {
            "buckets": buckets,
            "collections": collections,
            "datasets": datasets,
            "kernels": kernels,
            "models": models,
            "spaces": spaces,
        },
        "schema": SCHEMA_INVENTORY,
        "canonical_membership_source": binding["record"],
        "spaces_by_runtime_stage": dict(sorted(stages.items())),
        "special_spaces": sorted(row["id"] for row in spaces if row["listing"] != "AUTHOR_LIST_API"),
    }
    inventory["content_sha256"] = inventory_content_sha(inventory)
    return inventory


# --------------------------------------------------------------------------
# models.json: generated hub block and file-presence classification
# --------------------------------------------------------------------------


def weight_files(files: list[str]) -> list[str]:
    return sorted(
        name for name in files if name.endswith(WEIGHT_SUFFIXES) or WEIGHT_BIN.search(name)
    )


def classify_model(item: dict[str, Any]) -> str:
    """Deterministic class from the public listing (tags, library, files).

    The rules restate the class definitions carried in models.json "classes":
    a roadmap-tagged card is ROADMAP_EMPTY whatever placeholder bytes it
    carries; kernel repositories (library "kernels", or bench receipts with
    source and no weights) are KERNEL_SOFTWARE; any safetensors, GGUF or PEFT
    bytes make TRAINED_WEIGHTS; numpy npz alone is NANO_SYNTHETIC; the org
    profile and any other code or payload is CODE_OR_SCRIPTS; a card with
    nothing past README, licence and provenance stubs is ROADMAP_EMPTY.
    """
    ident = str(item["id"])
    tags = {str(tag).lower() for tag in item.get("tags") or []}
    files = siblings_of(item)
    weights = weight_files(files)
    dense = [name for name in weights if not name.endswith(".npz")]
    has_bench = any(re.search(r"(^|/)BENCH[^/]*\.json$", name) for name in files)
    has_code = any(name.endswith(".py") for name in files)
    if "roadmap" in tags:
        return "ROADMAP_EMPTY"
    if item.get("library_name") == "kernels" or (has_bench and has_code and not dense):
        return "KERNEL_SOFTWARE"
    if dense:
        return "TRAINED_WEIGHTS"
    if weights:
        return "NANO_SYNTHETIC"
    if ident == f"{ORG}/{ORG}":
        return "CODE_OR_SCRIPTS"
    if all(CARD_ONLY_FILES.match(name) for name in files):
        return "ROADMAP_EMPTY"
    return "CODE_OR_SCRIPTS"


def bench_still_bound(bench: Any, files: list[str]) -> bool:
    if not isinstance(bench, dict):
        return False
    source = bench.get("source")
    if not isinstance(source, str) or not source:
        return False
    return any(fnmatch.fnmatchcase(name, source) for name in files)


def build_models_contract(prior: dict[str, Any], raw_models: list[dict[str, Any]], inventory: dict[str, Any]) -> dict[str, Any]:
    contract = copy.deepcopy(prior)
    prior_rows = {str(row.get("id")): row for row in prior.get("models", []) if isinstance(row, dict)}
    rows = []
    for item in by_id(raw_models):
        ident = str(item["id"])
        files = siblings_of(item)
        klass = classify_model(item)
        earlier = prior_rows.get(ident, {})
        bench = earlier.get("bench")
        keep_bench = earlier.get("class") == klass and bench_still_bound(bench, files)
        carried_bench = copy.deepcopy(bench) if keep_bench else None
        if carried_bench is not None:
            # A listed filename does not bind the prior benchmark file bytes.
            # Never promote a carried assertion to MEASURED on an API refresh.
            carried_bench["evidence_class"] = "REPORTED"
        rows.append(
            {
                "id": ident,
                "class": klass,
                "pipeline": item.get("pipeline_tag"),
                "library": item.get("library_name"),
                "files": len(files),
                "weights": weight_files(files),
                "bench": carried_bench,
                "operational": False,
                "trained": klass in ("TRAINED_WEIGHTS", "NANO_SYNTHETIC"),
            }
        )
    counts = inventory["counts"]
    class_counts = Counter(row["class"] for row in rows)
    unknown = set(class_counts) - set(contract.get("classes", {}))
    if unknown:
        raise GenerationError(f"classifier produced undefined classes: {sorted(unknown)}")
    surface = contract.setdefault("surface", {})
    surface["meaning"] = (
        "Generated file-presence classification of every public Hub model card. TRAINED means weight "
        "files exist. KERNEL-SOFTWARE means source/tests, not a LoRA. ROADMAP means an empty or "
        "roadmap-tagged card. NANO means synthetic npz. A listed URL is location only. Reachability is "
        "never quality. This origin does not train, bench, or serve weights."
    )
    contract["reader_guide"] = (
        "Every public Hub model card is classified here by " + GENERATOR + " from the unauthenticated "
        "author listing; counts live in the hub block and in /estate/hf-current.json, never in prose. "
        "Private repositories are NOT_OBSERVED. A bench block is carried forward from the prior curated "
        "record only while its source file is still listed and the class is unchanged; otherwise it is "
        "null and remains REPORTED without the benchmark bytes. The KEEP / fold cut stays /spaces.json "
        "policy, not a Hub count. This file does not stamp "
        "OPERATIONAL or LIVE. Energy is UNAVAILABLE until RAPL/NVML is MEASURED. GPU train is UNAVAILABLE "
        "from this runtime. Evaluate kernels and adapters on a-11-oy.com; this origin only indexes the cards."
    )
    contract["captured_at"] = inventory["observed_at"]
    contract["evidence_class"] = "SNAPSHOT"
    contract["generated_by"] = GENERATOR
    contract["method"] = (
        "Unauthenticated Hugging Face API GET /api/models?author=" + ORG + " with expanded sibling file "
        "lists; class rules in " + GENERATOR + " classify_model(). File presence only: no weight is "
        "downloaded, loaded, or evaluated."
    )
    contract["trained_all"] = all(row["trained"] for row in rows)
    contract["hub"] = {
        "org": ORG,
        "models": counts["models"],
        "datasets": counts["datasets"],
        "spaces": counts["spaces"],
        "kernels": counts["kernels"],
        "private": "NOT_OBSERVED",
        "listing": f"https://huggingface.co/{ORG}",
        "source": "/" + INVENTORY_PATH,
    }
    contract["counts"] = {name: class_counts.get(name, 0) for name in CLASS_ORDER}
    contract["models"] = rows
    return contract


# --------------------------------------------------------------------------
# spaces.json hub_presence, estate/hf-current.json, live-align
# --------------------------------------------------------------------------


def build_spaces_contract(prior: dict[str, Any], inventory: dict[str, Any]) -> dict[str, Any]:
    contract = copy.deepcopy(prior)
    listed = {row["id"].split("/", 1)[1] for row in inventory["resources"]["spaces"]}

    def split(section: str) -> dict[str, list[str]]:
        ids = [str(row["id"]) for row in prior.get(section, []) if isinstance(row, dict)]
        return {
            "listed": sorted(i for i in ids if i in listed),
            "not_listed": sorted(i for i in ids if i not in listed),
        }

    contract["hub_presence"] = {
        "evidence_class": "SNAPSHOT",
        "fold": split("fold"),
        "generated_by": GENERATOR,
        "interpretation": (
            "NOT_LISTED means the Space id is absent from the unauthenticated public listing at "
            "observed_at: deleted, renamed, or private. The keep and fold rows are policy and are not "
            "rewritten by this block."
        ),
        "keep": split("keep"),
        "observed_at": inventory["observed_at"],
        "source": "/" + INVENTORY_PATH,
    }
    return contract


def live_space_cards(inventory: dict[str, Any], spaces_policy: dict[str, Any]) -> list[dict[str, Any]]:
    rows = {row["id"]: row for row in inventory["resources"]["spaces"]}
    cards = []
    for entry in spaces_policy.get("keep", []):
        ident = f"{ORG}/{entry['id']}"
        row = rows.get(ident)
        if row is None or WITHHELD.search(ident):
            continue
        cards.append(
            {
                "api": f"{API}/spaces/{ident}",
                "href": row["hub_url"],
                "id": ident,
                "policy": "spaces.json keep",
                "sdk": row["sdk"],
                "title": row["title"] or ident.split("/", 1)[1],
            }
        )
    return cards


def load_json(root: Path, relative: str) -> Any:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def historical_rows(root: Path) -> list[dict[str, Any]]:
    estate = load_json(root, HISTORICAL_ESTATE_PATH)
    old = load_json(root, HISTORICAL_INVENTORY_PATH)
    return [
        {
            "captured_at": estate.get("captured_at"),
            "evidence_class": estate.get("evidence_class"),
            "path": "/" + HISTORICAL_ESTATE_PATH,
            "role": "dated estate snapshot; historical, not rewritten",
        },
        {
            "captured_at": old.get("observed_at"),
            "evidence_class": "SNAPSHOT",
            "path": "/" + HISTORICAL_INVENTORY_PATH,
            "role": "prior public-inventory.json (" + str(old.get("schema")) + "); historical, not rewritten",
        },
    ]


def build_current(inventory: dict[str, Any], spaces_policy: dict[str, Any], history: list[dict[str, Any]]) -> dict[str, Any]:
    counts = inventory["counts"]
    return {
        "claim_boundaries": {
            "counts": "PUBLIC_LISTING_ONLY_NOT_QUALITY_SAFETY_OR_READINESS",
            "kernel_membership": "MODEL_SUBSET_COUNTED_ONCE_IN_TOTALS",
            "collections_and_buckets": "OUTSIDE_REPOSITORY_MEMBERSHIP_SCOPE",
            "private_assets": "NOT_OBSERVED",
            "runtime_stage": "HUB_REPORTED_STAGE_ONLY_NOT_A_HEALTH_PROBE",
        },
        "counts": {
            "buckets": counts["buckets"],
            "collections": counts["collections"],
            "datasets_public": counts["datasets"],
            "kernels": counts["kernels"],
            "models": counts["models"],
            "public_resources_total": counts["public_resources_total"],
            "repository_membership_total": counts["repository_membership_total"],
            "spaces_public": counts["spaces"],
        },
        "evidence_class": "SNAPSHOT",
        "freshness": {
            "badge_stale_after_hours": 24,
            "refresh_workflow": REFRESH_WORKFLOW,
            "rule": (
                "observed_at is when this exact content was first observed; a later observation of "
                "identical content keeps it. Pages print it beside every count"
            ),
        },
        "generated_by": GENERATOR,
        "historical_snapshots": history,
        "live_space_cards": live_space_cards(inventory, spaces_policy),
        "observation_mode": OBSERVATION_MODE,
        "observed_at": inventory["observed_at"],
        "observed_date": inventory["observed_at"][:10],
        "organization": ORG,
        "private_assets": "NOT_OBSERVED",
        "schema": SCHEMA_CURRENT,
        "source": "/" + INVENTORY_PATH,
        "source_content_sha256": inventory["content_sha256"],
        "canonical_membership_source": inventory["canonical_membership_source"],
        "spaces_by_runtime_stage": inventory["spaces_by_runtime_stage"],
    }


def build_live_align(inventory: dict[str, Any], root: Path) -> dict[str, Any]:
    estate = load_json(root, HISTORICAL_ESTATE_PATH).get("huggingface", {})
    old = load_json(root, HISTORICAL_INVENTORY_PATH)
    counts = inventory["counts"]
    drift = []
    for source, captured, field, site, live in (
        (HISTORICAL_ESTATE_PATH, "2026-08-31T18:59:11Z", "models", estate.get("models"), counts["models"]),
        (HISTORICAL_ESTATE_PATH, "2026-08-31T18:59:11Z", "datasets", estate.get("datasets"), counts["datasets"]),
        (HISTORICAL_ESTATE_PATH, "2026-08-31T18:59:11Z", "spaces_public", estate.get("spaces_public"), counts["spaces"]),
        (HISTORICAL_INVENTORY_PATH, old.get("observed_at"), "models", old.get("counts", {}).get("models"), counts["models"]),
        (HISTORICAL_INVENTORY_PATH, old.get("observed_at"), "datasets", old.get("counts", {}).get("datasets"), counts["datasets"]),
        (HISTORICAL_INVENTORY_PATH, old.get("observed_at"), "spaces", old.get("counts", {}).get("spaces"), counts["spaces"]),
    ):
        drift.append(
            {"field": field, "live_public": live, "site": site, "site_captured_at": captured, "source": source}
        )
    spaces = inventory["resources"]["spaces"]
    return {
        "assets_missing_license": sorted(
            f"{kind[:-1]}:{row['id']}"
            for kind in ("models", "datasets", "spaces", "kernels")
            for row in inventory["resources"][kind]
            if not row.get("license")
        ),
        "claim_boundaries": {
            "estate_json": "HISTORICAL_NOT_MODIFIED",
            "license": "HUB_TAG_OR_CARD_METADATA_ONLY_NOT_LEGAL_REVIEW",
            "private_assets": "NOT_OBSERVED",
            "runtime_stage": "HUB_REPORTED_STAGE_ONLY_NOT_A_HEALTH_PROBE",
        },
        "counts": {
            "datasets": counts["datasets"],
            "kernels": counts["kernels"],
            "models": counts["models"],
            "spaces": counts["spaces"],
        },
        "drift_vs_committed_snapshots": drift,
        "endpoints": inventory["endpoints"],
        "generated_by": GENERATOR,
        "kernel_ids": [row["id"] for row in inventory["resources"]["kernels"]],
        "observation_mode": OBSERVATION_MODE,
        "observed_at": inventory["observed_at"],
        "organization": ORG,
        "running_spaces": [row["id"] for row in spaces if row["runtime"]["stage"] == "RUNNING"],
        "schema": SCHEMA_LIVE_ALIGN,
        "source": "/" + INVENTORY_PATH,
        "spaces_by_runtime_stage": inventory["spaces_by_runtime_stage"],
    }


# --------------------------------------------------------------------------
# Pages: data-hf-current fields and the generated live-Space rows
# --------------------------------------------------------------------------

FIELD = re.compile(
    r'(?P<open><(?P<tag>[a-zA-Z][a-zA-Z0-9]*)\b[^<>]*?\sdata-hf-current="(?P<key>[a-z0-9_.]+)"[^<>]*>)'
    r"(?P<body>[^<]*)"
    r"(?P<close></(?P=tag)>)"
)
LIVE_ROWS = re.compile(
    r"(?P<open><!-- hf-current:live-space-rows begin[^>]*-->)(?P<body>.*?)(?P<close>[ \t]*<!-- hf-current:live-space-rows end -->)",
    re.DOTALL,
)


def lookup(current: dict[str, Any], key: str) -> Any:
    value: Any = current
    for part in key.split("."):
        if not isinstance(value, dict) or part not in value:
            raise GenerationError(f"data-hf-current key {key!r} is not in {CURRENT_PATH}")
        value = value[part]
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise GenerationError(f"data-hf-current key {key!r} is not a scalar")
    return value


def live_row(card: dict[str, Any]) -> str:
    esc = lambda value: html.escape(str(value), quote=True)  # noqa: E731
    shown = card["href"].split("://", 1)[1]
    return (
        f'    <li><a class="live is-empty" data-empty-kind="unavailable" data-space="{esc(card["id"])}" '
        f'data-api="{esc(card["api"])}" href="{esc(card["href"])}" target="_blank" rel="noopener">'
        f'<span class="dot down"></span><span class="meta"><b>{esc(card["title"])}</b>'
        f'<span class="u">{esc(shown)}</span></span>'
        f'<span class="st" data-state="unavailable">NOT OBSERVED · UNAVAILABLE</span></a></li>\n'
    )


def render_page(text: str, current: dict[str, Any]) -> str:
    def fill(match: re.Match[str]) -> str:
        value = lookup(current, match.group("key"))
        return match.group("open") + html.escape(str(value), quote=False) + match.group("close")

    text = FIELD.sub(fill, text)

    def rows(match: re.Match[str]) -> str:
        body = "".join(live_row(card) for card in current["live_space_cards"])
        return match.group("open") + "\n" + body + match.group("close")

    return LIVE_ROWS.sub(rows, text)


def page_fields(text: str) -> list[tuple[str, str]]:
    return [(m.group("key"), m.group("body")) for m in FIELD.finditer(text)]


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------


def dump(value: Any, *, sort_keys: bool = True, ensure_ascii: bool = True) -> str:
    return json.dumps(value, indent=2, sort_keys=sort_keys, ensure_ascii=ensure_ascii) + "\n"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def valid_timestamp(value: str) -> bool:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return False
    return True


def generate(root: Path, raw: dict[str, Any], observed_at: str) -> dict[str, str]:
    """Return {relative path: new text} for every generated file."""
    if not valid_timestamp(observed_at):
        raise GenerationError(f"observed_at must be a UTC second timestamp, got {observed_at!r}")
    inventory = build_inventory(raw, observed_at)
    committed_path = root / INVENTORY_PATH
    if committed_path.is_file():
        committed = json.loads(committed_path.read_text(encoding="utf-8"))
        if (
            committed.get("schema") == SCHEMA_INVENTORY
            and committed.get("content_sha256") == inventory["content_sha256"]
            and valid_timestamp(str(committed.get("observed_at")))
        ):
            # Unchanged content keeps its original observation time, so a rerun
            # is byte-identical and the refresh workflow has nothing to propose.
            inventory = build_inventory(raw, str(committed["observed_at"]))
    spaces_prior = load_json(root, SPACES_PATH)
    models_prior = load_json(root, MODELS_PATH)
    current = build_current(inventory, spaces_prior, historical_rows(root))
    outputs = {
        INVENTORY_PATH: dump(inventory),
        MEMBERSHIP_PATH: dump(raw["canonical_source"]["record"]),
        CANONICAL_COPY_PATH: raw["canonical_source"]["manifest_text"],
        CURRENT_PATH: dump(current),
        LIVE_ALIGN_PATH: dump(build_live_align(inventory, root)),
        MODELS_PATH: dump(build_models_contract(models_prior, raw["models"], inventory), sort_keys=False),
        SPACES_PATH: dump(build_spaces_contract(spaces_prior, inventory), sort_keys=False, ensure_ascii=False),
    }
    for page in PAGES:
        text = (root / page).read_text(encoding="utf-8")
        outputs[page] = render_page(text, current)
    return outputs


def write(root: Path, outputs: dict[str, str], dry_run: bool, log: Callable[[str], None]) -> list[str]:
    changed = []
    for relative, text in sorted(outputs.items()):
        path = root / relative
        before = path.read_text(encoding="utf-8") if path.is_file() else None
        if before == text:
            continue
        changed.append(relative)
        if not dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
    log(("would change: " if dry_run else "changed: ") + (", ".join(changed) or "nothing"))
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=ROOT, help="site root (default: this repository)")
    parser.add_argument("--fixture", type=Path, help="read API-shaped JSON from this directory instead of the Hub")
    parser.add_argument("--observed-at", help="UTC timestamp to stamp (default: now)")
    parser.add_argument("--dry-run", action="store_true", help="report which files would change; write nothing")
    args = parser.parse_args(argv)
    source = FixtureSource(args.fixture) if args.fixture else LiveSource()
    try:
        raw = collect(source)
        outputs = generate(args.root.resolve(), raw, args.observed_at or utc_now())
    except GenerationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    current = json.loads(outputs[CURRENT_PATH])
    print(
        "observed_at={observed_at} models={models} datasets_public={datasets_public} "
        "spaces_public={spaces_public} kernels={kernels} collections={collections} buckets={buckets} "
        "private=NOT_OBSERVED".format(observed_at=current["observed_at"], **current["counts"])
    )
    write(args.root.resolve(), outputs, args.dry_run, print)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
