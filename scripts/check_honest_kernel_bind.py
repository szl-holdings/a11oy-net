#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed contract: kernel chips bind /honest locked_formula_count."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
DILIGENCE = ROOT / "diligence" / "index.html"
BIND = ROOT / "scripts" / "honest_kernel_bind.js"
HEADERS = ROOT / "_headers"
HONEST_URL = "https://a-11-oy.com/api/a11oy/v1/honest"
HONEST_FIELD = "locked_formula_count"
HTML_SURFACES = tuple(
    path
    for path in sorted(ROOT.rglob("*.html"))
    if ".git" not in path.parts
)
KERNEL_CHIP = re.compile(
    r"""id=["']cnt-locked["']"""
    r"""|id=["']pt-locked["']"""
    r"""|id=["']hs-proven["']"""
    r"""|data-kernel-chip"""
    r"""|locked-proven\s*=""",
    re.I,
)
HONEST_BIND = re.compile(
    r"""(?:/api/a11oy/v1/honest|/honest)[\s\S]{0,500}?locked_formula_count"""
    r"""|locked_formula_count[\s\S]{0,240}?(?:/api/a11oy/v1/honest|/honest)""",
    re.I,
)
HARDCODED_EIGHT = re.compile(
    r"""locked-proven\s*=\s*(?:<b>)?exactly\s*8"""
    r"""|locked-proven\s*=\s*exactly\s+eight""",
    re.I,
)
CATALOG_LABEL = re.compile(
    r"""(?:genome|catalog)\s+LOCKED-PROVEN|LOCKED-PROVEN\s+catalog""",
    re.I,
)


def check() -> None:
    bind = BIND.read_text(encoding="utf-8")
    assert BIND.is_file()
    assert HONEST_URL in bind
    assert HONEST_FIELD in bind
    assert "value === 8" in bind
    assert "N/A" in bind
    assert "UNAVAILABLE" in bind
    assert re.search(r"\?\?\s*8\b", bind) is None
    assert re.search(r"\|\|\s*8\b", bind) is None
    assert "exactly 8" not in bind.lower()
    assert "exactly eight" not in bind.lower()

    index = INDEX.read_text(encoding="utf-8")
    assert HARDCODED_EIGHT.search(index) is None, (
        "hero/footer kernel chips must not paint a hardcoded exactly 8"
    )
    assert 'data-kernel-chip="locked-proven"' in index
    assert f'data-honest-url="{HONEST_URL}"' in index
    assert f'data-honest-field="{HONEST_FIELD}"' in index
    assert 'id="cnt-locked"' in index
    assert ">N/A<" in index
    assert HONEST_BIND.search(index)
    assert 'src="scripts/honest_kernel_bind.js"' in index
    assert "https://a-11-oy.com" in index
    assert CATALOG_LABEL.search(index), "catalog LOCKED-PROVEN=25 must stay labelled"
    assert "catalog LOCKED-PROVEN" in index
    catalog = re.search(
        r'class="catalog-chip"[^>]*>(.*?)</span>',
        index,
        re.I | re.S,
    )
    assert catalog, "catalog 25 must be a catalog-chip, not the kernel"
    catalog_html = catalog.group(0)
    assert "25" in catalog_html
    assert "glass" not in catalog_html
    assert "record" not in catalog_html
    assert "live" not in catalog_html
    assert "var(--proof)" not in catalog_html
    catalog_text = catalog.group(1).lower()
    assert "genome catalog" in catalog_text or "not the kernel" in catalog_text
    assert "Lean-8 ≠ genome-144" in index or "Lean-8 != genome-144" in index
    assert 'class="frontier-kernel"' in index
    assert "not ROADMAP" in index
    assert 'class="conjecture"' in index
    assert "Conjecture 1" in index
    kanchay = (ROOT / "assets" / "kanchay.css").read_text(encoding="utf-8")
    assert ".conjecture,.conjecture b{color:var(--gray)" in kanchay
    assert ".catalog-chip,.catalog-chip b{color:var(--gray)" in kanchay

    kernel_hosts = re.findall(
        r"<span[^>]*data-kernel-chip[^>]*>.*?</span>",
        index,
        re.I | re.S,
    )
    assert kernel_hosts, "kernel chips must exist so the bind can be probed"
    for host in kernel_hosts:
        assert "LOCKED-PROVEN" not in host
        assert "exactly 8" not in host.lower()
        assert ">25<" not in host

    headers = HEADERS.read_text(encoding="utf-8")
    assert "connect-src 'self' https://huggingface.co https://a-11-oy.com" in headers
    meta = re.search(
        r'http-equiv="Content-Security-Policy" content="([^"]+)"',
        index,
    )
    assert meta, "root meta CSP required"
    assert "connect-src 'self' https://huggingface.co https://a-11-oy.com" in meta.group(1)

    saw_chip = False
    for path in HTML_SURFACES:
        text = path.read_text(encoding="utf-8")
        relative = str(path.relative_to(ROOT))
        assert HARDCODED_EIGHT.search(text) is None, f"{relative}: hardcoded kernel 8"
        has_chip = bool(KERNEL_CHIP.search(text))
        if has_chip:
            saw_chip = True
            assert HONEST_BIND.search(text), (
                f"{relative}: kernel chip must bind {HONEST_URL} {HONEST_FIELD}"
            )
            if path == DILIGENCE:
                assert "N/A" in text
                assert CATALOG_LABEL.search(text)
                assert "Lean-8 ≠ genome-144" in text or "Lean-8 != genome-144" in text
                assert "Conjecture 1" in text
    assert saw_chip, "missing kernel-chip probe is FAIL"


if __name__ == "__main__":
    check()
    print(
        "OK: kernel chips bind /honest locked_formula_count === 8 or N/A; "
        "catalog 25 stays labelled."
    )
