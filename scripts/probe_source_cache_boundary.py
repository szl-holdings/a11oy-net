#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Diagnose stale Cloudflare proof-source caching without changing edge state.

A diagnostic only. The existing exact-edge-security gate remains authoritative:
a correct Pages origin or cache-busted response cannot excuse an incorrect
canonical https://a11oy.net/.well-known/szl-source.json response.

No credentials, Cloudflare API, configuration write, cache purge, deployment,
model execution, or provider credential fallback are present in this module.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import http.client
import json
import os
import pathlib
import re
import socket
import ssl
import sys
import urllib.error
import urllib.request
from typing import Any, Callable

# Isolated python -I excludes the script directory from sys.path. Admit only
# the adjacent reviewed source module, never the current working directory.
SCRIPTS_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
from stamp_source_witness import SHA_RE, validate_contract

HOST = "a11oy.net"
WITNESS_PATH = "/.well-known/szl-source.json"
CANONICAL_URL = "https://" + HOST + WITNESS_PATH
# Public GitHub Pages addresses for the canonical custom domain, not a user URL.
# Verified TLS with SNI HOST is mandatory; raw-IP HTTPS without verification
# would not establish that the origin serves the requested hostname.
PAGES_IPV4 = ("185.199.108.153", "185.199.109.153",
              "185.199.110.153", "185.199.111.153")
MAX_JSON = 8192
TIMEOUT = 8
ALLOWED_HEADERS = ("CF-Cache-Status", "Age", "ETag", "Last-Modified",
                   "Cache-Control", "Server", "Content-Type")
SCHEMA = "szl.proof-edge-cache-diagnosis/v1"


class ProbeFailure(RuntimeError):
    """Bounded provider failure; never stores HTTP response body or exceptions."""


class AuthorizationStop(ProbeFailure):
    """An access denial or rate limit stops all further alternative probes."""


def _unique_json(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProbeFailure("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def decode_witness(data: bytes) -> str:
    """Return a validated source SHA; never trust a field without its contract."""
    if len(data) > MAX_JSON:
        raise ProbeFailure("BODY_SIZE_CAP")
    try:
        doc = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_json)
    except (ValueError, UnicodeError) as exc:
        raise ProbeFailure("INVALID_SOURCE_JSON") from exc
    if not isinstance(doc, dict):
        raise ProbeFailure("INVALID_SOURCE_OBJECT")
    sha = doc.get("source_revision")
    if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
        raise ProbeFailure("INVALID_SOURCE_REVISION")
    try:
        validate_contract(doc, sha)
    except ValueError as exc:
        raise ProbeFailure("INVALID_SOURCE_CONTRACT") from exc
    return sha


def _received(status: int, headers: Any, body: bytes) -> dict[str, Any]:
    if status in (401, 403, 429):
        raise AuthorizationStop("AUTH_OR_RATE_DENIED_" + str(status))
    if status != 200:
        raise ProbeFailure("HTTP_" + str(status))
    content_type = headers.get("Content-Type", "")
    if content_type.split(";", 1)[0].strip().lower() != "application/json":
        raise ProbeFailure("UNEXPECTED_CONTENT_TYPE")
    revision = decode_witness(body)
    selected = {k.lower().replace("-", "_"): headers.get(k)
                for k in ALLOWED_HEADERS if headers.get(k) is not None}
    return {"state": "VALID", "source_revision": revision,
            "sha256": hashlib.sha256(body).hexdigest(),
            "bytes": len(body), "headers": selected}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_public(url: str) -> dict[str, Any]:
    """Only the two predetermined public URLs are passed by observe()."""
    if not (url == CANONICAL_URL or
            re.fullmatch(re.escape(CANONICAL_URL) + r"\?szl_probe=[0-9a-f]{40}-[0-9]{14}", url)):
        raise ProbeFailure("UNAPPROVED_PUBLIC_URL")
    opener = urllib.request.build_opener(NoRedirect())
    request = urllib.request.Request(
        url, headers={"Accept": "application/json",
                      "Cache-Control": "no-cache",
                      "User-Agent": "SZL-proof-cache-readonly/1"}, method="GET")
    try:
        with opener.open(request, timeout=TIMEOUT) as response:
            body = response.read(MAX_JSON + 1)
            return _received(response.status, response.headers, body)
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403, 429):
            raise AuthorizationStop("AUTH_OR_RATE_DENIED_" + str(exc.code)) from None
        raise ProbeFailure("PUBLIC_HTTP_" + str(exc.code)) from None
    except (OSError, urllib.error.URLError, ValueError):
        raise ProbeFailure("PUBLIC_TRANSPORT_UNAVAILABLE") from None


def fetch_origin(ip: str) -> dict[str, Any]:
    """Get the exact canonical witness from a public Pages origin using TLS SNI."""
    if ip not in PAGES_IPV4:
        raise ProbeFailure("UNAPPROVED_ORIGIN_IP")
    try:
        with socket.create_connection((ip, 443), timeout=TIMEOUT) as conn:
            # Standard trusted CA verification, *not* an insecure direct-IP request.
            with ssl.create_default_context().wrap_socket(conn, server_hostname=HOST) as tls:
                tls.settimeout(TIMEOUT)
                tls.sendall((
                    "GET " + WITNESS_PATH + " HTTP/1.1\r\n"
                    "Host: " + HOST + "\r\n"
                    "Accept: application/json\r\n"
                    "Cache-Control: no-cache\r\n"
                    "User-Agent: SZL-proof-cache-readonly/1\r\n"
                    "Connection: close\r\n\r\n"
                ).encode("ascii"))
                response = http.client.HTTPResponse(tls)
                response.begin()
                return _received(response.status, response.headers,
                                 response.read(MAX_JSON + 1))
    except AuthorizationStop:
        raise
    except ProbeFailure:
        raise
    except (OSError, ssl.SSLError, http.client.HTTPException, ValueError):
        raise ProbeFailure("ORIGIN_TLS_OR_HTTP_UNAVAILABLE") from None


def _safe(call: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    try:
        return call()
    except AuthorizationStop:
        raise
    except ProbeFailure as exc:
        return {"state": "UNOBSERVED", "reason": str(exc)}


def classify(expected: str, canonical: dict[str, Any],
             variants: list[dict[str, Any]],
             origins: list[dict[str, Any]]) -> str:
    """Never promote the diagnostic into production-release authorization."""
    c_match = canonical.get("state") == "VALID" and canonical.get("source_revision") == expected
    origin_ok = len(origins) == len(PAGES_IPV4) and all(
        o.get("state") == "VALID" and o.get("source_revision") == expected for o in origins
    )
    new_variant = any(v.get("state") == "VALID" and v.get("source_revision") == expected
                      for v in variants)
    if any(o.get("state") == "VALID" and o.get("source_revision") != expected
           for o in origins):
        return "ORIGIN_SOURCE_MISMATCH_RELEASE_BLOCKED"
    if c_match and origin_ok:
        # Even an exact witness at both origins is not a signed deployment or uptime proof.
        return "CANONICAL_AND_ORIGIN_MATCH_NOT_PRODUCTION_QUALIFICATION"
    if c_match:
        return "CANONICAL_MATCH_ORIGIN_UNVERIFIED_NOT_RELEASE_QUALIFIED"
    if canonical.get("state") == "VALID" and origin_ok and new_variant:
        return "CDN_STALE_SOURCE_CONFIRMED_RELEASE_BLOCKED"
    if origin_ok and new_variant:
        return "EDGE_RESPONSE_UNAVAILABLE_OR_INVALID_RELEASE_BLOCKED"
    if new_variant:
        return "CACHE_VARIANT_DISAGREEMENT_ORIGIN_UNVERIFIED_RELEASE_BLOCKED"
    return "SOURCE_PARITY_UNOBSERVED_RELEASE_BLOCKED"


def observe(expected: str, *, public=fetch_public, origin=fetch_origin,
            now: Callable[[], dt.datetime] | None = None) -> dict[str, Any]:
    if not isinstance(expected, str) or not SHA_RE.fullmatch(expected):
        raise ValueError("expected source must be an immutable lowercase Git SHA")
    clock = now or (lambda: dt.datetime.now(dt.timezone.utc))
    observed = clock().astimezone(dt.timezone.utc)
    nonce = observed.strftime("%Y%m%d%H%M%S")
    cache_variant_url = CANONICAL_URL + "?szl_probe=" + expected + "-" + nonce
    result = {"schema": SCHEMA, "observed_at_utc": observed.isoformat(),
              "expected_source_revision_supplied": expected,
              "current_protected_main_independently_verified": False,
              "canonical_url": CANONICAL_URL,
              "mode": "READ_ONLY_PUBLIC_DIAGNOSTIC", "provider_mutations": False,
              "provider_credentials_used": False, "production_authorized": False}
    try:
        result["canonical"] = _safe(lambda: public(CANONICAL_URL))
        # If the canonical endpoint denies access, no alternative-path read.
        result["cache_variant"] = _safe(lambda: public(cache_variant_url))
        result["direct_pages_origins"] = [
            {"ip": ip, "result": _safe(lambda ip=ip: origin(ip))}
            for ip in PAGES_IPV4
        ]
        origins = [v["result"] for v in result["direct_pages_origins"]]
        result["diagnosis"] = classify(expected, result["canonical"],
                                       [result["cache_variant"]], origins)
    except AuthorizationStop as exc:
        result["diagnosis"] = "AUTH_OR_RATE_DENIED_STOP"
        result["stop_reason"] = str(exc)
    # This instrument never marks a release ready. Existing edge-security
    # readback must inspect the unchanged canonical URL independently.
    result["canonical_release_gate"] = "NOT_ASSESSED_BY_THIS_DIAGNOSTIC"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-revision", required=True)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        report = observe(args.expected_revision)
        encoded = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode()
        # No overwrite or competing append writers: output path is an owner-chosen
        # new file and parents must already exist.
        with args.output.open("xb") as f:
            f.write(encoded)
            f.flush()
            os.fsync(f.fileno())
    except (OSError, ValueError, ProbeFailure) as exc:
        print("SOURCE_CACHE_DIAG_NOT_RECORDED " + type(exc).__name__, file=sys.stderr)
        return 2
    print("SOURCE_CACHE_DIAG " + report["diagnosis"])
    return 0 if report["diagnosis"] == "CANONICAL_AND_ORIGIN_MATCH_NOT_PRODUCTION_QUALIFICATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
