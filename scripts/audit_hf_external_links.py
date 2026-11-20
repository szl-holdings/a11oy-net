# SPDX-License-Identifier: Apache-2.0
"""Bounded public Hugging Face link readback; never a release/identity proof.

The existing check_links.py verifies local assets but deliberately ignores other
origins. This audit fills that coverage gap without credentials, and distinguishes
HTTP method limitations from access denial. Offline inventory is the CI default;
explicit --live uses only anonymous HTTPS requests to Hugging Face hosts.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request


def allowed_url(url: str) -> bool:
    try:
        parsed = urllib.parse.urlsplit(url)
        host = (parsed.hostname or "").lower()
        return (
            parsed.scheme == "https"
            and parsed.username is None
            and parsed.password is None
            and parsed.port is None
            and (host == "huggingface.co" or host.endswith(".hf.space"))
        )
    except ValueError:
        return False


def public_url(raw: str) -> tuple[str, bool] | None:
    """Never retain or print query strings: they may contain secret tokens."""
    if not allowed_url(raw):
        return None
    parsed = urllib.parse.urlsplit(raw)
    safe = urllib.parse.urlunsplit(("https", parsed.hostname.lower(), parsed.path or "/", "", ""))
    return safe, bool(parsed.query)


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        mapping = dict(attrs)
        for field in ("href", "src", "poster"):
            if mapping.get(field):
                self.urls.append(mapping[field])
        if mapping.get("srcset"):
            self.urls.extend(x.strip().split()[0] for x in mapping["srcset"].split(",") if x.strip())
        if tag == "meta" and (mapping.get("name", "") + mapping.get("property", "")).endswith("image"):
            if mapping.get("content"):
                self.urls.append(mapping["content"])

    handle_startendtag = handle_starttag


def inventory(root: Path) -> list[dict]:
    rows: dict[str, dict] = {}
    for page in sorted(root.rglob("*.html")):
        if ".git" in page.relative_to(root).parts:
            continue
        links = _Links()
        links.feed(page.read_text(encoding="utf-8"))
        for raw in links.urls:
            sanitized = public_url(raw)
            if sanitized is None:
                continue
            url, withheld = sanitized
            item = rows.setdefault(url, {"url": url, "source_files": set(), "query_withheld": False})
            item["source_files"].add(page.relative_to(root).as_posix())
            item["query_withheld"] |= withheld
    return [
        {**row, "source_files": sorted(row["source_files"])}
        for _key, row in sorted(rows.items())
    ]


class _HfOnlyRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not allowed_url(newurl):
            raise urllib.error.HTTPError(newurl, 599, "off-host redirect blocked", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _attempt(opener, url: str, method: str, timeout: float) -> tuple[int | None, str]:
    req = urllib.request.Request(url, method=method, headers={"User-Agent": "SZL-HF-Link-Audit/1.0"})
    try:
        with opener.open(req, timeout=timeout) as response:
            if method == "GET":
                response.read(64)  # bounded, no body contents logged
            return int(response.status), response.geturl()
    except urllib.error.HTTPError as exc:
        return int(exc.code), url
    except (OSError, ValueError):
        return None, url


def probe(url: str, *, timeout: float = 7, opener=None) -> dict:
    if not allowed_url(url) or urllib.parse.urlsplit(url).query:
        return {"status": "WITHHELD_UNSAFE_URL", "head_status": None, "get_status": None}
    opener = opener or urllib.request.build_opener(_HfOnlyRedirect())
    head_status, head_final = _attempt(opener, url, "HEAD", timeout)
    get_status, final = None, head_final
    # HEAD 404/405/501 can be false negatives. No blind retry on 429.
    if head_status is None or head_status in (401, 403, 404, 405, 501):
        get_status, final = _attempt(opener, url, "GET", timeout)
    actual = get_status if get_status is not None else head_status
    if isinstance(actual, int) and 200 <= actual < 400 and allowed_url(final):
        endpoint = urllib.parse.urlsplit(final).path
        status = "ACCESS_REQUIRED" if endpoint.startswith(("/login", "/join")) else "HTTP_REACHABLE_UNVERIFIED"
    elif actual in (401, 403):
        status = "ACCESS_REQUIRED"
    elif actual == 404:
        status = "RESTRICTED_OR_MISSING"
    elif actual == 429:
        status = "RATE_LIMITED"
    else:
        status = "UNKNOWN_OR_TRANSIENT"
    return {"status": status, "head_status": head_status, "get_status": get_status}


def evaluate(root: Path, *, live: bool, max_urls: int = 100, workers: int = 3, timeout: float = 7) -> dict:
    entries = inventory(root)
    selected = entries[:max_urls]
    if live:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            outcomes = list(pool.map(lambda row: (
                {"status": "WITHHELD_QUERY", "head_status": None, "get_status": None}
                if row["query_withheld"] else probe(row["url"], timeout=timeout)
            ), selected))
    else:
        outcomes = [{"status": "NOT_PROBED", "head_status": None, "get_status": None} for _ in selected]
    results = [{**row, **outcome} for row, outcome in zip(selected, outcomes)]
    return {
        "schema": "szl.hf-public-links/v1",
        "observed_utc": datetime.now(timezone.utc).isoformat(),
        "claim_boundary": "HTTP_REACHABILITY_IS_NOT_PROVENANCE_OR_RUNTIME_READINESS",
        "mode": "ANONYMOUS_LIVE" if live else "OFFLINE_INVENTORY",
        "unique_urls": len(entries),
        "observed_urls": len(results),
        "unobserved_urls": len(entries) - len(results),
        "statuses": {kind: sum(r["status"] == kind for r in results)
                     for kind in sorted({r["status"] for r in results})},
        "release_admission": "HOLD_UNVERIFIED",
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--live", action="store_true", help="Opt-in anonymous HTTPS probes")
    parser.add_argument("--max-urls", type=int, default=100)
    parser.add_argument("--timeout", type=float, default=7)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if not 1 <= args.max_urls <= 100 or not 1 <= args.workers <= 3 or not 1 <= args.timeout <= 10:
        parser.error("bounded max-urls (1..100), workers (1..3), and timeout (1..10) required")
    report = evaluate(args.root.resolve(), live=args.live, max_urls=args.max_urls,
                      workers=args.workers, timeout=args.timeout)
    serialized = json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.write_text(serialized, encoding="utf-8")
    else:
        print(serialized)
    return 0  # Audit only: never silently grant release admission.


if __name__ == "__main__":
    raise SystemExit(main())
