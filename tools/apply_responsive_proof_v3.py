#!/usr/bin/env python3
"""Apply both responsive proof bindings without generator short-circuiting."""
from __future__ import annotations

import json

import bind_responsive_proof_v3 as base


def main() -> int:
    changed = False
    for host in base.HOSTS:
        changed = base.bind_host(host) or changed
    state = json.loads(base.STATE.read_text(encoding="utf-8"))
    state["state"] = "BOUND"
    state["verified_bindings"] = [host.relative_to(base.ROOT).as_posix() for host in base.HOSTS]
    base.STATE.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    base.check()
    print(f"responsive-proof-v3: {'UPDATED' if changed else 'ALREADY_BOUND'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
