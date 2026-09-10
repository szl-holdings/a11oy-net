#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CURRENT = ROOT / "public-inventory-current.json"
PAGE = ROOT / "inventory-current" / "index.html"

record = json.loads(CURRENT.read_text(encoding="utf-8"))
assert record["schema"] == "szl.proof.public-hf-inventory-current/v1"
assert record["evidence_class"] == "MEASURED"
assert record["observation"]["predicate"] == "hf-public-author-membership/v1"
assert record["observation"]["authentication"] == "none"
assert record["observation"]["counts"] == {"models": 46, "datasets": 35, "spaces": 21}
assert record["observation"]["source_revision"] == "4c6621b17ba452d5af7aa2460462fdfbe513509f"
assert record["github_profile_projection"]["merge_revision"] == "a61cb238b71d1852d84ce6394a208d0ab0110796"
projection = record["hugging_face_org_card_projection"]
assert projection["source_revision"] == "cc8c6d894e686ac4fcc788cd366140fb39e40b6c"
assert projection["hub_commit"] == "b244997b36b8a05223102d85e69d5a916a8e335f"
assert projection["publisher_workflow_run"] == 34456315383
assert projection["immutable_files_match"] is True
assert projection["runtime_files_match"] is True
assert projection["state"] == "VERIFIED"
assert record["historical_detailed_inventory"]["preserved"] is True
bounds = record["claim_boundaries"]
assert bounds["authenticated_whole_organization_total"] == "NOT_CLAIMED"
assert bounds["model_quality"] == "NOT_INFERRED"
assert bounds["runtime_readiness"] == "NOT_INFERRED_FROM_COUNTS"
assert bounds["production_authorization"] is False
assert bounds["product_route_or_default_change"] is False

html = PAGE.read_text(encoding="utf-8")
for required in (
    "MEASURED",
    "46",
    "35",
    "21",
    "hf-public-author-membership/v1",
    "Registry counts are not model quality, runtime readiness, or production authorization.",
    "2026-08-31 inventory",
    "public-inventory-current.json",
):
    assert required in html

print("current public inventory proof contract: PASS")
