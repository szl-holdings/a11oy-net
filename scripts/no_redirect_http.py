#!/usr/bin/env python3
"""Bounded HTTP opener that never follows redirects.

Callers validate one exact public or provider URL at a time. A redirect is a
failed readback, not authority to contact another endpoint or forward headers.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from typing import Any


PAYMENT_REQUIRED_HEADER = "PAYMENT-REQUIRED"


def describe_http_error(exc: urllib.error.HTTPError) -> str:
    """Name an edge refusal instead of reporting only a bare status line.

    Cloudflare crawler protection answers automated clients with HTTP 402 and an
    x402 ``PAYMENT-REQUIRED`` header; a managed challenge answers 403 with
    ``cf-mitigated: challenge``. Both refuse the probe at the edge and observe
    nothing about the origin's content, so the message says which one occurred.
    A 402 without that header is not labelled x402. Every other status keeps
    urllib's own wording, for example ``HTTP Error 302: Found``.
    """

    headers = exc.headers

    def header(name: str) -> str:
        value = headers.get(name) if headers is not None else None
        return value.strip() if isinstance(value, str) else ""

    if exc.code == 402:
        if header(PAYMENT_REQUIRED_HEADER):
            return (
                "edge returned 402 (x402 paywall); "
                f"{PAYMENT_REQUIRED_HEADER} header present"
            )
        return (
            "edge returned 402 Payment Required without a "
            f"{PAYMENT_REQUIRED_HEADER} header; not identified as x402"
        )
    if exc.code == 403 and header("cf-mitigated").lower() == "challenge":
        return "edge returned 403 managed challenge (cf-mitigated: challenge)"
    return str(exc)


class RejectRedirects(urllib.request.HTTPRedirectHandler):
    """Return the original 3xx response as an HTTPError without a second request."""

    def redirect_request(
        self,
        request: urllib.request.Request,
        file_pointer: Any,
        code: int,
        message: str,
        headers: Any,
        new_url: str,
    ) -> None:
        return None


def open_no_redirect(
    request: urllib.request.Request,
    *,
    timeout: float,
):
    opener = urllib.request.build_opener(RejectRedirects())
    return opener.open(request, timeout=timeout)
