#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed live readback for the a11oy.net static proof origin.

The readback keeps independent controls independent: exact protected GitHub
source, the deployed static source witness, GitHub Pages settings, HTTPS/TLS,
DNSSEC, and response security headers each receive their own result. A passing
TLS handshake therefore cannot conceal a missing DNSSEC delegation, an
unenforced Pages HTTPS setting, missing headers, or source drift.

The resulting JSON is generated evidence. It is not committed as timeless
truth, and it does not make application-runtime or uptime claims for a static
GitHub Pages surface.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import socket
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

import check_security_headers
from no_redirect_http import open_no_redirect
from stamp_source_witness import SHA_RE, validate_contract


HOSTNAME = "a11oy.net"
PAGES_ORIGIN_HOSTNAME = "szl-holdings.github.io"
SURFACE = "https://a11oy.net"
SOURCE_WITNESS_URL = f"{SURFACE}/.well-known/szl-source.json"
SOURCE_REPOSITORY = "szl-holdings/a11oy-net"
MAX_JSON_BYTES = 64 * 1024
MIN_TLS_REMAINING = dt.timedelta(days=7)
REQUIRED_PAGES_CERTIFICATE_DOMAINS = frozenset({HOSTNAME, f"www.{HOSTNAME}"})
DNSSEC_RESOLVERS = (
    ("cloudflare", "https://cloudflare-dns.com/dns-query"),
    ("google", "https://dns.google/resolve"),
)
HEADER_URLS = (
    f"{SURFACE}/",
    f"{SURFACE}/site.webmanifest",
)


class ProbeError(ValueError):
    """A bounded public or provider readback failed its contract."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProbeError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def decode_json(raw: bytes, *, source: str) -> dict[str, Any]:
    if len(raw) > MAX_JSON_BYTES:
        raise ProbeError(f"{source}: JSON body exceeds {MAX_JSON_BYTES} bytes")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProbeError(f"{source}: response is not UTF-8") from exc
    try:
        value = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise ProbeError(f"{source}: response is not valid JSON") from exc
    if not isinstance(value, dict):
        raise ProbeError(f"{source}: expected a JSON object")
    return value


def fetch_json(
    url: str,
    *,
    token: str | None = None,
    accept: str = "application/json",
) -> tuple[dict[str, Any], dict[str, Any]]:
    headers = {
        "Accept": accept,
        "User-Agent": "a11oy-edge-security-readback/2.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    request = urllib.request.Request(url, headers=headers)
    try:
        with open_no_redirect(request, timeout=20) as response:
            status = response.status
            final_url = response.geturl()
            content_type = response.headers.get("Content-Type", "")
            raw = response.read(MAX_JSON_BYTES + 1)
    except (OSError, urllib.error.URLError) as exc:
        raise ProbeError(f"{url}: readback failed: {exc}") from exc
    if status != 200:
        raise ProbeError(f"{url}: expected HTTP 200, observed {status}")
    payload = decode_json(raw, source=url)
    return payload, {
        "status_code": status,
        "final_url": final_url,
        "content_type": content_type,
    }


def _is_exact_canonical_url(observed: str, expected: str) -> bool:
    observed_parts = urllib.parse.urlsplit(observed)
    expected_parts = urllib.parse.urlsplit(expected)
    if observed_parts.username or observed_parts.password:
        return False
    if observed_parts.scheme.lower() != "https":
        return False
    if observed_parts.hostname is None:
        return False
    observed_port = observed_parts.port
    if observed_port not in (None, 443):
        return False
    normalized_observed = (
        observed_parts.scheme.lower(),
        observed_parts.hostname.lower(),
        observed_parts.path,
        observed_parts.query,
        observed_parts.fragment,
    )
    normalized_expected = (
        expected_parts.scheme.lower(),
        (expected_parts.hostname or "").lower(),
        expected_parts.path,
        expected_parts.query,
        expected_parts.fragment,
    )
    return normalized_observed == normalized_expected


def validate_source_control(
    branch: dict[str, Any],
    commit: dict[str, Any],
    expected_revision: str,
) -> dict[str, Any]:
    errors: list[str] = []
    branch_commit = branch.get("commit")
    observed_revision = (
        branch_commit.get("sha") if isinstance(branch_commit, dict) else None
    )
    if observed_revision != expected_revision:
        errors.append(
            f"protected main is {observed_revision!r}, expected {expected_revision!r}"
        )
    if branch.get("protected") is not True:
        errors.append("GitHub does not report main as protected")
    if commit.get("sha") != expected_revision:
        errors.append("commit readback does not match the expected revision")
    # Use GitHub's compact Git-database commit object.  The higher-level
    # /commits/{sha} response includes every changed file and patch, so an
    # otherwise valid large commit can exceed this probe's bounded JSON reader
    # before signature verification is reached.
    verification = commit.get("verification")
    verified = verification.get("verified") if isinstance(verification, dict) else None
    reason = verification.get("reason") if isinstance(verification, dict) else None
    if verified is not True:
        errors.append(f"GitHub commit signature is not verified (reason={reason!r})")
    return {
        "status": "PASS" if not errors else "FAIL",
        "expected_revision": expected_revision,
        "observed_main_revision": observed_revision,
        "branch_protected": branch.get("protected") is True,
        "commit_signature_verified": verified is True,
        "verification_reason": reason,
        "errors": errors,
    }


def _parse_provider_expiry(value: Any) -> dt.datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Pages certificate expiry is missing")
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("Pages certificate expiry is not valid ISO 8601") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def validate_pages_settings(
    pages: dict[str, Any],
    *,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    now = now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Pages validation time must be timezone-aware")
    now = now.astimezone(dt.timezone.utc)
    errors: list[str] = []
    expected = {
        "build_type": "workflow",
        "status": "built",
        "cname": HOSTNAME,
        "https_enforced": True,
    }
    for key, value in expected.items():
        if pages.get(key) != value:
            errors.append(
                f"Pages {key} is {pages.get(key)!r}, expected {value!r}"
            )
    html_url = pages.get("html_url")
    if not isinstance(html_url, str) or not html_url.startswith("https://"):
        errors.append("Pages html_url is not an HTTPS URL")
    protected_domain_state = pages.get("protected_domain_state")
    if protected_domain_state != "verified":
        errors.append(
            "Pages protected_domain_state is "
            f"{protected_domain_state!r}, expected 'verified'"
        )

    certificate = pages.get("https_certificate")
    certificate_state = None
    certificate_domains: list[str] = []
    certificate_expires_at = None
    certificate_remaining_days = None
    if not isinstance(certificate, dict):
        errors.append("Pages https_certificate is not an object")
    else:
        certificate_state = certificate.get("state")
        if certificate_state != "approved":
            errors.append(
                "Pages https_certificate.state is "
                f"{certificate_state!r}, expected 'approved'"
            )
        domains = certificate.get("domains")
        if isinstance(domains, list) and all(isinstance(item, str) for item in domains):
            certificate_domains = domains
            missing_domains = REQUIRED_PAGES_CERTIFICATE_DOMAINS - set(domains)
            if missing_domains:
                errors.append(
                    "Pages certificate does not cover required domains: "
                    + ", ".join(sorted(missing_domains))
                )
        else:
            errors.append("Pages https_certificate.domains is not a string list")
        certificate_expires_at = certificate.get("expires_at")
        try:
            expires_at = _parse_provider_expiry(certificate_expires_at)
        except ValueError as exc:
            errors.append(str(exc))
        else:
            remaining = expires_at - now
            certificate_remaining_days = int(remaining.total_seconds() // 86400)
            if remaining < MIN_TLS_REMAINING:
                errors.append(
                    "Pages origin certificate has less than seven days remaining "
                    "or is expired"
                )
    return {
        "status": "PASS" if not errors else "FAIL",
        "build_type": pages.get("build_type"),
        "provider_status": pages.get("status"),
        "cname": pages.get("cname"),
        "https_enforced": pages.get("https_enforced"),
        "html_url": html_url,
        "protected_domain_state": protected_domain_state,
        "https_certificate": {
            "state": certificate_state,
            "domains": certificate_domains,
            "expires_at": certificate_expires_at,
            "remaining_days": certificate_remaining_days,
        },
        "errors": errors,
    }


def probe_github(
    repository: str,
    expected_revision: str,
    token: str | None,
    *,
    fetcher: Callable[..., tuple[dict[str, Any], dict[str, Any]]] = fetch_json,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if repository != SOURCE_REPOSITORY:
        raise ProbeError(f"repository must be exactly {SOURCE_REPOSITORY}")
    encoded_repository = "/".join(
        urllib.parse.quote(part, safe="") for part in repository.split("/")
    )
    base = f"https://api.github.com/repos/{encoded_repository}"
    branch, _ = fetcher(f"{base}/branches/main", token=token)
    commit, _ = fetcher(f"{base}/git/commits/{expected_revision}", token=token)
    pages, _ = fetcher(f"{base}/pages", token=token)
    return (
        validate_source_control(branch, commit, expected_revision),
        validate_pages_settings(pages),
    )


def probe_current_main(
    repository: str,
    expected_revision: str,
    token: str | None,
    *,
    fetcher: Callable[..., tuple[dict[str, Any], dict[str, Any]]] = fetch_json,
) -> dict[str, Any]:
    """Reauthorize protected main after every slower external edge probe."""

    if repository != SOURCE_REPOSITORY:
        raise ProbeError(f"repository must be exactly {SOURCE_REPOSITORY}")
    encoded_repository = "/".join(
        urllib.parse.quote(part, safe="") for part in repository.split("/")
    )
    branch, _ = fetcher(
        f"https://api.github.com/repos/{encoded_repository}/branches/main",
        token=token,
    )
    branch_commit = branch.get("commit")
    observed_revision = (
        branch_commit.get("sha") if isinstance(branch_commit, dict) else None
    )
    errors: list[str] = []
    if branch.get("protected") is not True:
        errors.append("GitHub does not report main as protected")
    if observed_revision != expected_revision:
        errors.append(
            f"protected main moved to {observed_revision!r}; expected {expected_revision!r}"
        )
    return {
        "status": "PASS" if not errors else "FAIL",
        "expected_revision": expected_revision,
        "observed_main_revision": observed_revision,
        "branch_protected": branch.get("protected") is True,
        "meaning": (
            "Final protected-main readback performed after the source witness, TLS, "
            "DNSSEC, and live-header probes and immediately before receipt admission."
        ),
        "errors": errors,
    }


def probe_source_witness(
    expected_revision: str,
    *,
    fetcher: Callable[..., tuple[dict[str, Any], dict[str, Any]]] = fetch_json,
) -> dict[str, Any]:
    payload, metadata = fetcher(SOURCE_WITNESS_URL)
    final_url = metadata.get("final_url")
    errors: list[str] = []
    if not isinstance(final_url, str) or not _is_exact_canonical_url(
        final_url, SOURCE_WITNESS_URL
    ):
        errors.append(
            f"source witness final URL is {final_url!r}, expected {SOURCE_WITNESS_URL!r}"
        )
    content_type = str(metadata.get("content_type", "")).lower()
    if "application/json" not in content_type:
        errors.append(
            f"source witness content type is {content_type!r}, expected application/json"
        )
    try:
        validate_contract(payload, expected_revision)
    except ValueError as exc:
        errors.append(str(exc))
    return {
        "status": "PASS" if not errors else "FAIL",
        "url": SOURCE_WITNESS_URL,
        "expected_revision": expected_revision,
        "observed_revision": payload.get("source_revision"),
        "artifact_kind": payload.get("artifact_kind"),
        "artifact_binding": payload.get("artifact_binding"),
        "product_runtime_readiness": payload.get("product_runtime_readiness"),
        "uptime": payload.get("uptime"),
        "errors": errors,
    }


def validate_dnssec_response(
    payload: dict[str, Any],
    *,
    resolver: str,
    record_type: int,
) -> dict[str, Any]:
    errors: list[str] = []
    status = payload.get("Status")
    if isinstance(status, bool) or status != 0:
        errors.append(f"{resolver}: DNS status is {status!r}, expected 0")
    authenticated = payload.get("AD") is True
    if not authenticated:
        errors.append(f"{resolver}: authenticated-data flag is not true")
    answers = payload.get("Answer")
    matching = []
    if isinstance(answers, list):
        matching = [
            answer
            for answer in answers
            if isinstance(answer, dict)
            and answer.get("type") == record_type
            and str(answer.get("name", "")).rstrip(".").lower() == HOSTNAME
            and isinstance(answer.get("data"), str)
            and bool(answer["data"].strip())
        ]
    if not matching:
        errors.append(
            f"{resolver}: no authenticated {record_type} answer exists for {HOSTNAME}"
        )
    return {
        "status": "PASS" if not errors else "FAIL",
        "authenticated_data": authenticated,
        "record_present": bool(matching),
        "errors": errors,
    }


def probe_dnssec(
    *,
    fetcher: Callable[..., tuple[dict[str, Any], dict[str, Any]]] = fetch_json,
) -> dict[str, Any]:
    resolvers: list[dict[str, Any]] = []
    errors: list[str] = []
    for resolver_name, base_url in DNSSEC_RESOLVERS:
        result: dict[str, Any] = {"resolver": resolver_name, "records": {}}
        for label, record_type in (("DS", 43), ("DNSKEY", 48)):
            query = urllib.parse.urlencode({"name": HOSTNAME, "type": label})
            try:
                payload, _ = fetcher(
                    f"{base_url}?{query}",
                    accept="application/dns-json",
                )
                validation = validate_dnssec_response(
                    payload,
                    resolver=resolver_name,
                    record_type=record_type,
                )
            except (OSError, ProbeError, ValueError) as exc:
                validation = {
                    "status": "FAIL",
                    "authenticated_data": False,
                    "record_present": False,
                    "errors": [f"{resolver_name}: {label} readback failed: {exc}"],
                }
            result["records"][label] = validation
            errors.extend(validation["errors"])
        result["status"] = (
            "PASS"
            if all(record["status"] == "PASS" for record in result["records"].values())
            else "FAIL"
        )
        resolvers.append(result)
    return {
        "status": "PASS" if not errors else "FAIL",
        "meaning": (
            "Validating recursive-resolver readback; authenticated DS and DNSKEY "
            "answers are required from each configured resolver."
        ),
        "resolvers": resolvers,
        "errors": errors,
    }


def _certificate_name(value: Any) -> str | None:
    if not isinstance(value, tuple):
        return None
    parts = []
    for relative_distinguished_name in value:
        if not isinstance(relative_distinguished_name, tuple):
            continue
        for attribute in relative_distinguished_name:
            if (
                isinstance(attribute, tuple)
                and len(attribute) == 2
                and all(isinstance(item, str) for item in attribute)
            ):
                parts.append(f"{attribute[0]}={attribute[1]}")
    return ", ".join(parts) if parts else None


def probe_tls(
    *,
    connect_hostname: str = HOSTNAME,
    verification_hostname: str = HOSTNAME,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    allowed_targets = {
        (HOSTNAME, HOSTNAME),
        (PAGES_ORIGIN_HOSTNAME, HOSTNAME),
    }
    if (connect_hostname, verification_hostname) not in allowed_targets:
        raise ProbeError("TLS target is not an approved edge or Pages-origin probe")
    now = now or dt.datetime.now(dt.timezone.utc)
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.set_alpn_protocols(["h2", "http/1.1"])
    try:
        with socket.create_connection((connect_hostname, 443), timeout=20) as raw_socket:
            with context.wrap_socket(
                raw_socket,
                server_hostname=verification_hostname,
            ) as tls_socket:
                certificate = tls_socket.getpeercert()
                protocol = tls_socket.version()
                cipher = tls_socket.cipher()
                alpn = tls_socket.selected_alpn_protocol()
    except (OSError, ssl.SSLError) as exc:
        raise ProbeError(f"TLS handshake failed: {exc}") from exc
    if not isinstance(certificate, dict) or not certificate:
        raise ProbeError("TLS peer certificate was unavailable")
    not_after_text = certificate.get("notAfter")
    if not isinstance(not_after_text, str):
        raise ProbeError("TLS peer certificate has no notAfter field")
    try:
        not_after = dt.datetime.fromtimestamp(
            ssl.cert_time_to_seconds(not_after_text),
            tz=dt.timezone.utc,
        )
    except (ValueError, OverflowError) as exc:
        raise ProbeError("TLS certificate expiry could not be parsed") from exc
    errors: list[str] = []
    if protocol not in {"TLSv1.2", "TLSv1.3"}:
        errors.append(f"negotiated TLS protocol is {protocol!r}")
    if not_after - now < MIN_TLS_REMAINING:
        errors.append(
            "TLS certificate has less than seven days remaining or is expired"
        )
    return {
        "status": "PASS" if not errors else "FAIL",
        "connect_hostname": connect_hostname,
        "verification_hostname": verification_hostname,
        "hostname_verified": True,
        "protocol": protocol,
        "cipher": cipher[0] if isinstance(cipher, tuple) and cipher else None,
        "alpn": alpn,
        "issuer": _certificate_name(certificate.get("issuer")),
        "not_after_utc": not_after.isoformat().replace("+00:00", "Z"),
        "minimum_remaining_days": int(MIN_TLS_REMAINING.total_seconds() // 86400),
        "errors": errors,
    }


def probe_headers(
    *,
    static_validator: Callable[[], tuple[dict[str, str], list[str]]] = (
        check_security_headers.validate_static
    ),
    live_validator: Callable[[str, dict[str, str]], list[str]] = (
        check_security_headers.validate_live
    ),
) -> dict[str, Any]:
    expected, static_errors = static_validator()
    urls = []
    errors = [f"committed contract: {error}" for error in static_errors]
    for url in HEADER_URLS:
        live_errors = live_validator(url, expected)
        urls.append(
            {
                "url": url,
                "status": "PASS" if not live_errors else "FAIL",
                "errors": live_errors,
            }
        )
        errors.extend(live_errors)
    return {
        "status": "PASS" if not errors else "FAIL",
        "committed_contract": "PASS" if not static_errors else "FAIL",
        "live": urls,
        "meaning": (
            "The committed _headers file is a policy contract. Only the live "
            "response readback can establish whether an edge actually enforces it."
        ),
        "errors": errors,
    }


def _failed_probe(message: str) -> dict[str, Any]:
    return {"status": "FAIL", "errors": [message]}


def build_receipt(
    expected_revision: str,
    repository: str,
    token: str | None,
) -> dict[str, Any]:
    if not SHA_RE.fullmatch(expected_revision):
        raise ProbeError("expected revision must be a 40-character lowercase Git SHA")
    probes: dict[str, Any] = {}
    try:
        source_control, pages = probe_github(repository, expected_revision, token)
    except (OSError, ProbeError, ValueError) as exc:
        source_control = _failed_probe(f"GitHub readback failed: {exc}")
        pages = _failed_probe(f"GitHub Pages readback failed: {exc}")
    probes["source_control"] = source_control
    probes["pages_control_plane"] = pages

    for key, operation in (
        ("deployed_source_witness", lambda: probe_source_witness(expected_revision)),
        (
            "tls_edge",
            lambda: probe_tls(
                connect_hostname=HOSTNAME,
                verification_hostname=HOSTNAME,
            ),
        ),
        (
            "tls_pages_origin",
            lambda: probe_tls(
                connect_hostname=PAGES_ORIGIN_HOSTNAME,
                verification_hostname=HOSTNAME,
            ),
        ),
        ("dnssec", probe_dnssec),
        ("security_headers", probe_headers),
    ):
        try:
            probes[key] = operation()
        except (OSError, ProbeError, ValueError, ssl.SSLError) as exc:
            probes[key] = _failed_probe(f"{key} readback failed: {exc}")

    # External probes can outlive the source they began observing.  Re-read
    # protected main last so a concurrent merge cannot turn an old deployment
    # into a stale PASS receipt.
    try:
        probes["source_control_reauthorization"] = probe_current_main(
            repository,
            expected_revision,
            token,
        )
    except (OSError, ProbeError, ValueError) as exc:
        probes["source_control_reauthorization"] = _failed_probe(
            f"final GitHub main readback failed: {exc}"
        )

    failures = [key for key, value in probes.items() if value.get("status") != "PASS"]
    observed_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    return {
        "schema_version": "a11oy-edge-security-readback/v1",
        "surface": SURFACE,
        "observed_at_utc": observed_at.isoformat().replace("+00:00", "Z"),
        "expected_protected_source_revision": expected_revision,
        "result": "PASS" if not failures else "FAIL",
        "failed_controls": failures,
        "probes": probes,
        "boundaries": [
            "This receipt is a point-in-time external readback, not an uptime claim.",
            "Edge TLS, Pages-origin TLS, DNSSEC, Pages settings, source binding, and response headers are independent controls.",
            "The static proof origin does not establish a-11-oy.com product-runtime readiness.",
            "A committed _headers file is not evidence that GitHub Pages or Cloudflare enforced those headers.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-revision", required=True)
    parser.add_argument("--github-repository", default=SOURCE_REPOSITORY)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = pathlib.Path(args.output)
    try:
        receipt = build_receipt(
            args.expected_revision.strip().lower(),
            args.github_repository,
            os.environ.get("GITHUB_TOKEN"),
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    except (OSError, ProbeError, ValueError, json.JSONDecodeError) as exc:
        print(f"edge_security_readback FAILED before receipt: {exc}", file=sys.stderr)
        return 1
    print(
        f"Edge-security readback {receipt['result']}; "
        f"receipt={output}; failed_controls={','.join(receipt['failed_controls']) or 'none'}"
    )
    return 0 if receipt["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
