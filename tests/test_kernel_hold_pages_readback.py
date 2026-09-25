"""Source contract for the kernel-hold public routes. Does not prove Pages publish."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def test_root_pointer_stays_hold() -> None:
    payload = json.loads((ROOT / "kernel-hold.json").read_text(encoding="utf-8"))
    assert payload["disposition"] == "HOLD"
    assert payload["production_authorization"] is False
    assert payload["path"] == "/kernel-hold-2026-09-19.json"


def test_estate_pointer_stays_hold() -> None:
    payload = json.loads((ROOT / "estate" / "kernel-hold.json").read_text(encoding="utf-8"))
    assert payload["disposition"] == "HOLD"
    assert payload["production_authorization"] is False
    assert payload["path"] == "/kernel-hold-2026-09-19.json"


def test_dated_record_stays_overdue_hold() -> None:
    payload = json.loads((ROOT / "kernel-hold-2026-09-19.json").read_text(encoding="utf-8"))
    assert payload["disposition"] == "HOLD"
    assert payload["cutoff_status"] == "OVERDUE"
    assert payload["production_authorization"] is False
    assert payload["empty_v1_branch_created"] is False


def test_html_route_exists_and_does_not_claim_live() -> None:
    html = (ROOT / "kernel-hold.html").read_text(encoding="utf-8")
    assert "HOLD" in html
    assert "does not authorize promotion" in html.lower() or "does not authorize promotion" in html
    assert "UNAVAILABLE" in html
    assert "LIVE kernels" not in html
