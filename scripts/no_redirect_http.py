#!/usr/bin/env python3
"""Bounded HTTP opener that never follows redirects.

Callers validate one exact public or provider URL at a time. A redirect is a
failed readback, not authority to contact another endpoint or forward headers.
"""

from __future__ import annotations

import urllib.request
from typing import Any


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
