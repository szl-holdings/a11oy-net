#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build the static proof-origin witness for the current SZL release vector.

The output is generated inside the existing GitHub Pages build. It observes
protected GitHub tips, the canonical Hugging Face runtime, and the public product
edge. It does not commit dynamic data, mutate a provider, or claim that HTTP 200
alone proves source alignment.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any, Mapping, Sequence
import urllib.error
import urllib.parse
import urllib.request

SCHEMA = "szl.estate-release-vector/v1"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
MAX_BODY = 1_000_000
USER_AGENT = "SZL-Proof-Release-Vector/1.0"
SOURCE_KEYS = ("source_revision", "source_sha", "git_sha", "commit_sha", "revision")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def headers(*, github: bool = False) -> dict[str, str]:
    result = {
        "Accept": "application/json, text/html;q=0.8",
        "Cache-Control": "no-cache, no-store",
        "User-Agent": USER_AGENT,
    }
    if github:
        result["Accept"] = "application/vnd.github+json"
        result["X-GitHub-Api-Version"] = "2022-11-28"
        token = (os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN") or "").strip()
        if token:
            result["Authorization"] = f"Bearer {token}"
    return result


def fetch(url: str, *, github: bool = False, attempts: int = 4) -> dict[str, Any]:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.username or parsed.password:
        raise ValueError(f"refusing noncanonical URL: {url}")
    opener = urllib.request.build_opener(NoRedirect())
    started = time.monotonic()
    for attempt in range(attempts):
        request = urllib.request.Request(url, headers=headers(github=github))
        try:
            with opener.open(request, timeout=35) as response:
                raw = response.read(MAX_BODY + 1)
                if len(raw) > MAX_BODY:
                    raise RuntimeError(f"response exceeded {MAX_BODY} bytes")
                text = raw.decode("utf-8", "replace")
                try:
                    payload: Any = json.loads(text)
                except json.JSONDecodeError:
                    payload = None
                return {
                    "status": response.status,
                    "url": url,
                    "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "json": payload,
                    "elapsed_ms": round((time.monotonic() - started) * 1000, 1),
                    "redirect": None,
                }
        except urllib.error.HTTPError as exc:
            if exc.code in {301, 302, 303, 307, 308}:
                return {
                    "status": exc.code,
                    "url": url,
                    "bytes": 0,
                    "sha256": None,
                    "json": None,
                    "elapsed_ms": round((time.monotonic() - started) * 1000, 1),
                    "redirect": exc.headers.get("Location"),
                }
            if exc.code not in {429, 500, 502, 503, 504} or attempt + 1 == attempts:
                raw = exc.read(4096)
                return {
                    "status": exc.code,
                    "url": url,
                    "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest() if raw else None,
                    "json": None,
                    "elapsed_ms": round((time.monotonic() - started) * 1000, 1),
                    "redirect": None,
                }
            delay = min(2**attempt, 60)
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            try:
                if retry_after is not None:
                    delay = max(delay, min(int(retry_after), 60))
            except ValueError:
                pass
            time.sleep(delay)
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt + 1 == attempts:
                break
            time.sleep(min(2**attempt, 60))
    return {
        "status": None,
        "url": url,
        "bytes": 0,
        "sha256": None,
        "json": None,
        "elapsed_ms": round((time.monotonic() - started) * 1000, 1),
        "redirect": None,
    }


def exact_sha(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    return normalized if SHA40.fullmatch(normalized) else None


def source_revision(payload: Any) -> tuple[str | None, str | None]:
    if not isinstance(payload, Mapping):
        return None, None
    for key in SOURCE_KEYS:
        candidate = exact_sha(payload.get(key))
        if candidate:
            return candidate, key
    for parent in ("build", "source", "git", "deployment", "release"):
        child = payload.get(parent)
        if not isinstance(child, Mapping):
            continue
        for key in SOURCE_KEYS:
            candidate = exact_sha(child.get(key))
            if candidate:
                return candidate, f"{parent}.{key}"
    return None, None


def github_main(repository: str) -> dict[str, Any]:
    response = fetch(
        f"https://api.github.com/repos/{repository}/branches/main",
        github=True,
    )
    payload = response.get("json")
    sha = None
    protected = None
    if isinstance(payload, Mapping):
        commit = payload.get("commit")
        if isinstance(commit, Mapping):
            sha = exact_sha(commit.get("sha"))
        protected = payload.get("protected")
    return {
        "repository": repository,
        "status": response.get("status"),
        "sha": sha,
        "protected": protected,
        "observed": response.get("status") == 200 and sha is not None,
    }


def live_source(origin: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in ("/api/build-info", "/.well-known/szl-source.json", "/api/source"):
        response = fetch(origin.rstrip("/") + path)
        revision, field = source_revision(response.get("json"))
        rows.append(
            {
                "path": path,
                "status": response.get("status"),
                "sha256": response.get("sha256"),
                "revision": revision,
                "revision_field": field,
            }
        )
        if revision:
            return {
                "origin": origin,
                "observed": True,
                "revision": revision,
                "revision_field": field,
                "selected_path": path,
                "probes": rows,
            }
    return {
        "origin": origin,
        "observed": False,
        "revision": None,
        "revision_field": None,
        "selected_path": None,
        "probes": rows,
    }


def hf_runtime(repo_id: str) -> dict[str, Any]:
    encoded = "/".join(urllib.parse.quote(part) for part in repo_id.split("/", 1))
    response = fetch(f"https://huggingface.co/api/spaces/{encoded}")
    payload = response.get("json")
    runtime = payload.get("runtime") if isinstance(payload, Mapping) else None
    runtime = runtime if isinstance(runtime, Mapping) else {}
    return {
        "repo_id": repo_id,
        "status": response.get("status"),
        "sha": payload.get("sha") if isinstance(payload, Mapping) else None,
        "stage": runtime.get("stage"),
        "sdk": payload.get("sdk") if isinstance(payload, Mapping) else None,
        "observed": response.get("status") == 200,
    }


def build(*, proof_sha: str | None = None) -> dict[str, Any]:
    a11oy = github_main("szl-holdings/a11oy")
    proof = github_main("szl-holdings/a11oy-net")
    profile = github_main("szl-holdings/.github")
    domain = live_source("https://a-11-oy.com")
    space_source = live_source("https://szlholdings-a11oy.hf.space")
    space = hf_runtime("SZLHOLDINGS/a11oy")

    supplied_proof = exact_sha(proof_sha or os.getenv("GITHUB_SHA"))
    proof_current = bool(supplied_proof and supplied_proof == proof.get("sha"))
    product_current = bool(
        a11oy.get("observed")
        and domain.get("revision") == a11oy.get("sha")
        and space_source.get("revision") == a11oy.get("sha")
        and str(space.get("stage") or "").upper() == "RUNNING"
    )
    blockers: list[str] = []
    if not proof_current:
        blockers.append("PROOF_ARTIFACT_NOT_CURRENT_MAIN")
    if domain.get("revision") != a11oy.get("sha"):
        blockers.append("PRODUCT_DOMAIN_SOURCE_MISMATCH")
    if space_source.get("revision") != a11oy.get("sha"):
        blockers.append("CANONICAL_SPACE_SOURCE_MISMATCH")
    if str(space.get("stage") or "").upper() != "RUNNING":
        blockers.append(f"CANONICAL_SPACE_STAGE_{str(space.get('stage') or 'UNKNOWN').upper()}")

    source_vector = {
        "a11oy": a11oy.get("sha"),
        "proof": proof.get("sha"),
        "profile": profile.get("sha"),
        "a11oy_hf_revision": space.get("sha"),
    }
    value: dict[str, Any] = {
        "schema": SCHEMA,
        "observed_at": utc_now(),
        "state": "ALIGNED" if proof_current and product_current else "DIVERGENT",
        "release_id": digest(source_vector)[:24],
        "source_vector": source_vector,
        "proof_artifact_sha": supplied_proof,
        "proof_artifact_current": proof_current,
        "product_current": product_current,
        "github": {
            "a11oy": a11oy,
            "proof": proof,
            "profile": profile,
        },
        "public_product": domain,
        "canonical_space_source": space_source,
        "canonical_space": space,
        "blockers": blockers,
        "truth": {
            "http_200_is_production_certificate": False,
            "source_witness_required": True,
            "provider_writes_performed": False,
            "secret_values_recorded": False,
            "external_effectors": [],
            "production_authorization": False,
        },
    }
    value["proof_chain_sha256"] = digest(value)
    return value


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument(
        "--output",
        type=Path,
        default=Path("estate/release-vector.json"),
    )
    result.add_argument("--proof-sha")
    result.add_argument("--soft", action="store_true")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    value = build(proof_sha=args.proof_sha)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "state": value["state"],
                "release_id": value["release_id"],
                "blockers": value["blockers"],
                "proof_chain_sha256": value["proof_chain_sha256"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if value["state"] == "ALIGNED" or args.soft else 1


if __name__ == "__main__":
    raise SystemExit(main())
