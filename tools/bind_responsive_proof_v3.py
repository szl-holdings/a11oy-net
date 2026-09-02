#!/usr/bin/env python3
"""Bind the responsive proof layer to interactive and CSS-only proof surfaces."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "assets" / "szl-responsive-proof-v3.css"
STATE = ROOT / "responsive-experience-v3.json"
HOSTS = (
    ROOT / "assets" / "szl-holo-proof-v2.css",
    ROOT / "assets" / "szl-flow-proof-static.css",
)
MARKER = "szl-responsive-proof-v3"
IMPORT = '@import url("./szl-responsive-proof-v3.css"); /* szl-responsive-proof-v3 */'


def check() -> None:
    if not ASSET.is_file():
        raise RuntimeError("responsive proof asset is missing")
    for host in HOSTS:
        if not host.is_file():
            raise RuntimeError(f"proof host stylesheet is missing: {host.relative_to(ROOT)}")
        text = host.read_text(encoding="utf-8")
        if text.count(MARKER) != 1:
            raise RuntimeError(f"{host.relative_to(ROOT)} must contain one responsive marker")
        first = next((line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("/*") and not line.lstrip().startswith("*")), "")
        if first != IMPORT:
            raise RuntimeError(f"responsive import is not the first CSS rule in {host.relative_to(ROOT)}")
    state = json.loads(STATE.read_text(encoding="utf-8"))
    if state.get("state") != "BOUND":
        raise RuntimeError("responsive proof state is not BOUND")


def bind_host(host: Path) -> bool:
    text = host.read_text(encoding="utf-8")
    body = "\n".join(line for line in text.splitlines() if MARKER not in line).lstrip("\n")
    updated = IMPORT + "\n" + body
    if not updated.endswith("\n"):
        updated += "\n"
    if updated == text:
        return False
    host.write_text(updated, encoding="utf-8", newline="\n")
    return True


def apply() -> bool:
    changed = any(bind_host(host) for host in HOSTS)
    state = json.loads(STATE.read_text(encoding="utf-8"))
    state["state"] = "BOUND"
    state["verified_bindings"] = [host.relative_to(ROOT).as_posix() for host in HOSTS]
    STATE.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    check()
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        check()
        print("responsive-proof-v3: BOUND")
    else:
        print(f"responsive-proof-v3: {'UPDATED' if apply() else 'ALREADY_BOUND'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
