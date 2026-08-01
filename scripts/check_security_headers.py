#!/usr/bin/env python3
"""Validate the committed edge-header contract and optional live readback."""

from __future__ import annotations

import argparse
import base64
import hashlib
import pathlib
import re
import sys
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parents[1]
REQUIRED_HEADERS = {
    "content-security-policy",
    "strict-transport-security",
    "referrer-policy",
    "x-content-type-options",
    "x-frame-options",
    "permissions-policy",
    "cross-origin-opener-policy",
    "cross-origin-resource-policy",
}
REQUIRED_CSP_DIRECTIVES = {
    "default-src",
    "script-src",
    "style-src",
    "img-src",
    "connect-src",
    "font-src",
    "manifest-src",
    "object-src",
    "base-uri",
    "frame-ancestors",
    "form-action",
    "worker-src",
    "upgrade-insecure-requests",
}
EXPECTED_HEADER_VALUES = {
    "strict-transport-security": "max-age=63072000; includeSubDomains",
    "referrer-policy": "no-referrer",
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "permissions-policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    "cross-origin-opener-policy": "same-origin",
    "cross-origin-resource-policy": "same-origin",
}


def parse_headers(path: pathlib.Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "/*":
        raise ValueError("_headers must begin with the catch-all /* route")
    parsed: dict[str, str] = {}
    for number, line in enumerate(lines[1:], start=2):
        if not line.strip():
            continue
        if not line.startswith((" ", "\t")) or ":" not in line:
            raise ValueError(f"_headers:{number}: expected an indented Header: value")
        name, value = line.strip().split(":", 1)
        key = name.strip().lower()
        if key in parsed:
            raise ValueError(f"_headers:{number}: duplicate header {name}")
        parsed[key] = value.strip()
    return parsed


def inline_script_hashes(html: str) -> set[str]:
    hashes: set[str] = set()
    pattern = re.compile(r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>", re.I | re.S)
    for match in pattern.finditer(html):
        if re.search(r"\bsrc\s*=", match.group("attrs"), re.I):
            continue
        digest = hashlib.sha256(match.group("body").encode("utf-8")).digest()
        hashes.add("'sha256-" + base64.b64encode(digest).decode("ascii") + "'")
    return hashes


def validate_static() -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    try:
        headers = parse_headers(ROOT / "_headers")
    except (OSError, ValueError) as exc:
        return {}, [str(exc)]

    missing_headers = REQUIRED_HEADERS - set(headers)
    if missing_headers:
        errors.append("missing headers: " + ", ".join(sorted(missing_headers)))

    csp = headers.get("content-security-policy", "")
    csp_parts = [part.strip().split() for part in csp.split(";") if part.strip()]
    directives = {part[0] for part in csp_parts}
    missing_directives = REQUIRED_CSP_DIRECTIVES - directives
    if missing_directives:
        errors.append("CSP missing directives: " + ", ".join(sorted(missing_directives)))

    expected_hashes = inline_script_hashes((ROOT / "index.html").read_text(encoding="utf-8"))
    expected_csp = {
        "default-src": {"'self'"},
        "script-src": {"'self'", *expected_hashes},
        "style-src": {"'self'", "'unsafe-inline'"},
        "img-src": {"'self'", "data:"},
        "connect-src": {
            "'self'",
            "https://a-11-oy.com",
            "https://huggingface.co",
            "https://*.hf.space",
        },
        "font-src": {"'self'", "data:"},
        "manifest-src": {"'self'"},
        "object-src": {"'none'"},
        "base-uri": {"'self'"},
        "frame-ancestors": {"'none'"},
        "form-action": {"'none'"},
        "worker-src": {"'none'"},
        "upgrade-insecure-requests": set(),
    }
    observed_csp = {part[0]: set(part[1:]) for part in csp_parts}
    for directive, expected_tokens in expected_csp.items():
        if observed_csp.get(directive) != expected_tokens:
            errors.append(f"CSP {directive} does not match the fail-closed contract")
    unexpected_directives = directives - set(expected_csp)
    if unexpected_directives:
        errors.append("CSP has unreviewed directives: " + ", ".join(sorted(unexpected_directives)))
    for key, expected_value in EXPECTED_HEADER_VALUES.items():
        if normalize(headers.get(key, "")) != normalize(expected_value):
            errors.append(f"{key} does not match the fail-closed contract")
    return headers, errors


def normalize(value: str) -> str:
    return " ".join(value.split())


def validate_live(url: str, expected: dict[str, str]) -> list[str]:
    errors: list[str] = []
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "a11oy-edge-security-readback/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            observed = {key.lower(): value for key, value in response.headers.items()}
            final_url = response.geturl()
            status = response.status
    except Exception as exc:  # pragma: no cover - network/provider dependent
        return [f"{url}: live readback failed: {exc}"]
    if status != 200:
        errors.append(f"{url}: expected HTTP 200, observed {status}")
    if not final_url.lower().startswith("https://"):
        errors.append(f"{url}: final URL is not HTTPS: {final_url}")
    for key in sorted(REQUIRED_HEADERS):
        actual = observed.get(key)
        if actual is None:
            errors.append(f"{url}: missing live {key}")
        elif normalize(actual) != normalize(expected[key]):
            errors.append(f"{url}: live {key} does not match the committed contract")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        action="append",
        default=[],
        help="HTTPS URL to compare with the committed contract; may be repeated",
    )
    args = parser.parse_args()

    expected, errors = validate_static()
    for url in args.url:
        errors.extend(validate_live(url, expected))
    if errors:
        print("Security-header validation FAILED:")
        for error in errors:
            print(" -", error)
        return 1
    mode = "static contract and live readback" if args.url else "static contract"
    print(f"OK: {mode} validated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
