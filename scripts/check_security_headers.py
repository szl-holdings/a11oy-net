#!/usr/bin/env python3
"""Validate the committed edge-header contract and optional live readback."""

from __future__ import annotations

import argparse
import base64
import hashlib
import pathlib
import re
import sys
import urllib.parse
import urllib.request
from html.parser import HTMLParser


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
SCRIPTLESS_GATEWAY_META_CSP_CONTRACT = {
    "default-src": {"'self'"},
    "script-src": {"'none'"},
    "style-src": {"'self'"},
    "img-src": {"'self'", "data:"},
    "font-src": {"'self'"},
    "connect-src": {"'none'"},
    "object-src": {"'none'"},
    "base-uri": {"'self'"},
    "form-action": {"'none'"},
    "worker-src": {"'none'"},
    "upgrade-insecure-requests": set(),
}
SCRIPTLESS_GATEWAY_PAGES = (
    "chat/index.html",
    "code/index.html",
)
PAGE_META_CSP_CONTRACTS = {
    "chat/index.html": SCRIPTLESS_GATEWAY_META_CSP_CONTRACT,
    "code/index.html": SCRIPTLESS_GATEWAY_META_CSP_CONTRACT,
    "diligence/index.html": {
        "default-src": {"'self'"},
        "script-src": {"'none'"},
        "style-src": {"'self'"},
        "img-src": {"'self'", "data:"},
        "font-src": {"'self'"},
        "connect-src": {"'none'"},
        "object-src": {"'none'"},
        "base-uri": {"'self'"},
        "form-action": {"'none'"},
        "worker-src": {"'none'"},
        "upgrade-insecure-requests": set(),
    },
    "record/index.html": {
        "default-src": {"'self'"},
        "script-src": {"'none'"},
        "style-src": {"'self'"},
        "img-src": {"'self'", "data:"},
        "font-src": {"'self'"},
        "connect-src": {"'none'"},
        "object-src": {"'none'"},
        "base-uri": {"'self'"},
        "form-action": {"'none'"},
        "worker-src": {"'none'"},
        "upgrade-insecure-requests": set(),
    },
    "notes/index.html": {
        "default-src": {"'self'"},
        "script-src": {"'none'"},
        "style-src": {"'self'"},
        "img-src": {"'self'", "data:"},
        "font-src": {"'self'"},
        "connect-src": {"'none'"},
        "object-src": {"'none'"},
        "base-uri": {"'self'"},
        "form-action": {"'none'"},
        "worker-src": {"'none'"},
        "upgrade-insecure-requests": set(),
    },
    "404.html": {
        "default-src": {"'none'"},
        "script-src": {"'none'"},
        "style-src": {"'self'"},
        "img-src": {"'self'", "data:"},
        "font-src": {"'self'"},
        "connect-src": {"'none'"},
        "manifest-src": {"'none'"},
        "object-src": {"'none'"},
        "base-uri": {"'none'"},
        "form-action": {"'none'"},
        "worker-src": {"'none'"},
        "upgrade-insecure-requests": set(),
    },
    "api/build-info/index.html": {
        "default-src": {"'none'"},
        "style-src": {"'unsafe-inline'"},
        "base-uri": {"'none'"},
        "form-action": {"'none'"},
    },
    "readyz/index.html": {
        "default-src": {"'none'"},
        "style-src": {"'unsafe-inline'"},
        "base-uri": {"'none'"},
        "form-action": {"'none'"},
    },
}


class HtmlSecuritySurface(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta_csps: list[str] = []
        self.inline_style_blocks = 0
        self.inline_style_attributes = 0
        self.stylesheet_links = 0
        self.external_scripts = 0

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        item = dict(attrs)
        if (
            tag.lower() == "meta"
            and str(item.get("http-equiv") or "").lower()
            == "content-security-policy"
            and item.get("content") is not None
        ):
            self.meta_csps.append(str(item["content"]))
        if tag.lower() == "style":
            self.inline_style_blocks += 1
        if item.get("style") is not None:
            self.inline_style_attributes += 1
        if tag.lower() == "link" and "stylesheet" in str(
            item.get("rel") or ""
        ).lower().split():
            self.stylesheet_links += 1
        if tag.lower() == "script" and item.get("src"):
            self.external_scripts += 1


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


def parse_csp(value: str) -> dict[str, set[str]]:
    parsed: dict[str, set[str]] = {}
    for raw_part in value.split(";"):
        part = raw_part.strip().split()
        if not part:
            continue
        directive = part[0].lower()
        if directive in parsed:
            raise ValueError(f"duplicate CSP directive: {directive}")
        parsed[directive] = set(part[1:])
    return parsed


def meta_csp_exactly_matches(
    html: str, expected: dict[str, set[str]]
) -> bool:
    surface = HtmlSecuritySurface()
    surface.feed(html)
    if len(surface.meta_csps) != 1:
        return False
    try:
        return parse_csp(surface.meta_csps[0]) == expected
    except ValueError:
        return False


def validate_scriptless_gateway_csp_regressions() -> list[str]:
    errors: list[str] = []
    tamper_cases = (
        ("connect-src", "connect-src 'none'", "connect-src 'self'"),
        ("base-uri", "base-uri 'self'", "base-uri *"),
        ("form-action", "form-action 'none'", "form-action 'self'"),
    )
    for relative_path in SCRIPTLESS_GATEWAY_PAGES:
        expected = PAGE_META_CSP_CONTRACTS.get(relative_path)
        if expected != SCRIPTLESS_GATEWAY_META_CSP_CONTRACT:
            errors.append(
                f"{relative_path}: missing the exact scriptless gateway meta CSP contract"
            )
            continue
        try:
            page_html = (ROOT / relative_path).read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(
                f"{relative_path}: cannot read gateway CSP regression fixture: {exc}"
            )
            continue
        for label, original, replacement in tamper_cases:
            tampered_html = page_html.replace(original, replacement, 1)
            if tampered_html == page_html:
                errors.append(
                    f"{relative_path}: {label} regression fixture is missing"
                )
            elif meta_csp_exactly_matches(tampered_html, expected):
                errors.append(
                    f"{relative_path}: exact meta CSP validation accepted {label} drift"
                )
    return errors


def canonical_readback_url(value: str) -> str:
    if value != value.strip():
        raise ValueError("readback URL has surrounding whitespace")
    try:
        parsed = urllib.parse.urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise ValueError(f"invalid readback URL: {exc}") from exc
    if parsed.scheme.lower() != "https":
        raise ValueError("readback URL must use HTTPS")
    if not parsed.hostname:
        raise ValueError("readback URL must include a host")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("readback URL must not contain credentials")
    if parsed.fragment:
        raise ValueError("readback URL must not contain a fragment")
    host = parsed.hostname.lower()
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    netloc = host if port in (None, 443) else f"{host}:{port}"
    return urllib.parse.urlunsplit(
        ("https", netloc, parsed.path or "/", parsed.query, "")
    )


def readback_target_matches(requested_url: str, final_url: str) -> bool:
    return canonical_readback_url(requested_url) == canonical_readback_url(final_url)


def validate_static() -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    try:
        headers = parse_headers(ROOT / "_headers")
    except (OSError, ValueError) as exc:
        return {}, [str(exc)]

    try:
        parse_csp("default-src 'self'; default-src 'none'")
    except ValueError:
        pass
    else:
        errors.append("CSP parser accepted a duplicate directive")
    errors.extend(validate_scriptless_gateway_csp_regressions())
    try:
        if not readback_target_matches(
            "https://A11OY.net:443", "https://a11oy.net/"
        ):
            errors.append("equivalent HTTPS readback targets did not normalize")
        for drifted in (
            "https://attacker.example/",
            "https://a11oy.net/other",
            "https://a11oy.net/?unexpected=1",
        ):
            if readback_target_matches("https://a11oy.net/", drifted):
                errors.append(f"readback target drift was accepted: {drifted}")
        for invalid in (
            "http://a11oy.net/",
            "https://user@a11oy.net/",
            "https://a11oy.net/#fragment",
        ):
            try:
                canonical_readback_url(invalid)
            except ValueError:
                continue
            errors.append(f"invalid readback URL was accepted: {invalid}")
    except ValueError as exc:
        errors.append(f"readback URL regression contract failed: {exc}")

    missing_headers = REQUIRED_HEADERS - set(headers)
    if missing_headers:
        errors.append("missing headers: " + ", ".join(sorted(missing_headers)))

    csp = headers.get("content-security-policy", "")
    try:
        observed_csp = parse_csp(csp)
    except ValueError as exc:
        observed_csp = {}
        errors.append(str(exc))
    directives = set(observed_csp)
    missing_directives = REQUIRED_CSP_DIRECTIVES - directives
    if missing_directives:
        errors.append("CSP missing directives: " + ", ".join(sorted(missing_directives)))

    html = (ROOT / "index.html").read_text(encoding="utf-8")
    expected_hashes = inline_script_hashes(html)
    expected_csp = {
        "default-src": {"'self'"},
        "script-src": {"'self'", *expected_hashes},
        "style-src": {"'self'", "'unsafe-inline'"},
        "img-src": {"'self'", "data:"},
        "connect-src": {
            "'self'",
            "https://huggingface.co",
            "https://a-11-oy.com",
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
    for directive, expected_tokens in expected_csp.items():
        if observed_csp.get(directive) != expected_tokens:
            errors.append(f"CSP {directive} does not match the fail-closed contract")
    unexpected_directives = directives - set(expected_csp)
    if unexpected_directives:
        errors.append("CSP has unreviewed directives: " + ", ".join(sorted(unexpected_directives)))

    expected_root_meta_csp = {
        directive: tokens
        for directive, tokens in expected_csp.items()
        if directive != "frame-ancestors"
    }
    page_contracts = {
        "index.html": expected_root_meta_csp,
        **PAGE_META_CSP_CONTRACTS,
    }
    for relative_path, expected_meta_csp in page_contracts.items():
        path = ROOT / relative_path
        try:
            page_html = path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"{relative_path}: cannot read page for CSP validation: {exc}")
            continue
        surface = HtmlSecuritySurface()
        surface.feed(page_html)
        if len(surface.meta_csps) != 1:
            errors.append(
                f"{relative_path}: expected exactly one fallback meta CSP, "
                f"observed {len(surface.meta_csps)}"
            )
            continue
        try:
            observed_meta_csp = parse_csp(surface.meta_csps[0])
        except ValueError as exc:
            errors.append(f"{relative_path}: {exc}")
            continue
        if observed_meta_csp != expected_meta_csp:
            errors.append(
                f"{relative_path}: meta CSP does not exactly match its "
                "reviewed fail-closed contract"
            )
        if "frame-ancestors" in observed_meta_csp:
            errors.append(
                f"{relative_path}: frame-ancestors must be enforced by headers, "
                "not a meta CSP"
            )
        style_sources = observed_meta_csp.get(
            "style-src", observed_meta_csp.get("default-src", set())
        )
        has_inline_styles = bool(
            surface.inline_style_blocks or surface.inline_style_attributes
        )
        if has_inline_styles and "'unsafe-inline'" not in style_sources:
            errors.append(
                f"{relative_path}: inline styles are present but its exact meta "
                "CSP does not admit them"
            )
        if not has_inline_styles and "'unsafe-inline'" in style_sources:
            errors.append(
                f"{relative_path}: meta CSP admits inline styles but the page has none"
            )
        if surface.stylesheet_links and "'self'" not in style_sources:
            errors.append(
                f"{relative_path}: local stylesheet is blocked by its exact meta CSP"
            )
        script_sources = observed_meta_csp.get(
            "script-src", observed_meta_csp.get("default-src", set())
        )
        if surface.external_scripts and "'self'" not in script_sources:
            errors.append(
                f"{relative_path}: local script is blocked by its exact meta CSP"
            )
        page_inline_hashes = inline_script_hashes(page_html)
        if not page_inline_hashes.issubset(script_sources):
            errors.append(
                f"{relative_path}: inline script hashes do not match its exact meta CSP"
            )
    for key, expected_value in EXPECTED_HEADER_VALUES.items():
        if normalize(headers.get(key, "")) != normalize(expected_value):
            errors.append(f"{key} does not match the fail-closed contract")
    return headers, errors


def normalize(value: str) -> str:
    return " ".join(value.split())


def validate_live(url: str, expected: dict[str, str]) -> list[str]:
    errors: list[str] = []
    try:
        requested_url = canonical_readback_url(url)
    except ValueError as exc:
        return [f"{url}: {exc}"]
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
    try:
        final_canonical_url = canonical_readback_url(final_url)
    except ValueError as exc:
        errors.append(f"{url}: invalid final URL {final_url!r}: {exc}")
    else:
        if final_canonical_url != requested_url:
            errors.append(
                f"{url}: unexpected redirect/final target {final_canonical_url}; "
                f"expected {requested_url}"
            )
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
