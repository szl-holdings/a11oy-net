#!/usr/bin/env python3
"""Repin the Aegis→Killinchu proof record to the intelligence-v4 source set."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "aegis" / "index.html"
DECISION = ROOT / "decision.json"
RECORD = ROOT / "consolidation" / "aegis-killinchu-20260903.json"
TEST = ROOT / "tests" / "test_aegis_killinchu_consolidation.py"

OLD_A11OY = "775acaa54724ab206b0c5477d754fbd6ed36e5f7"
OLD_VERTICAL = "e08231a110fd80f85a61fba82d72ab7f1fe23836"
PUBLIC_TAXONOMY = "a50b1970bae4383f9760f7146436d424d5101fd3"
INTELLIGENCE_PUBLISHER = "55d9336fed3a23da5b1abfed4f7f38dcc5121a06"
VERTICAL_SOURCE = "83edba5c5e730c91d8f5f0a6531213fb860677af"
RUNTIME_VERSION = "2.2.0"
KILLINCHU = "928a6dace657f8f9e067773d23d5686fe3dcc716"


def replace_once(text: str, old: str, new: str, *, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def patch_page() -> None:
    text = PAGE.read_text(encoding="utf-8")
    text = replace_once(
        text,
        f"<tr><th>A11oy publisher merge</th><td><code>{OLD_A11OY}</code></td></tr>",
        f"<tr><th>A11oy public taxonomy</th><td><code>{PUBLIC_TAXONOMY}</code></td></tr>\n"
        f"        <tr><th>Intelligence-v4 publisher</th><td><code>{INTELLIGENCE_PUBLISHER}</code></td></tr>",
        label="A11oy evidence row",
    )
    text = replace_once(
        text,
        f"<tr><th>Vertical-services source</th><td><code>{OLD_VERTICAL}</code></td></tr>",
        f"<tr><th>Vertical-services source</th><td><code>{VERTICAL_SOURCE}</code></td></tr>\n"
        f"        <tr><th>Expected runtime version</th><td><code>{RUNTIME_VERSION}</code></td></tr>",
        label="vertical-services evidence row",
    )
    text = replace_once(
        text,
        "<tr><th>Proof posture</th><td>STATIC RECORD · formula authority NONE · runtime not claimed</td></tr>",
        "<tr><th>Proof posture</th><td>STATIC RECORD · formula authority NONE · exact runtime parity not claimed by this origin</td></tr>",
        label="proof posture",
    )
    if OLD_A11OY in text or OLD_VERTICAL in text:
        raise RuntimeError("stale v3 evidence survived page repin")
    PAGE.write_text(text, encoding="utf-8")


def patch_decision() -> None:
    data = json.loads(DECISION.read_text(encoding="utf-8"))
    item = data["consolidations"]["aegis"]
    if item.get("killinchu_revision") != KILLINCHU:
        raise RuntimeError("Killinchu source authority changed unexpectedly")
    if item.get("a11oy_publisher_revision") != OLD_A11OY:
        raise RuntimeError("unexpected prior A11oy publisher revision")
    if item.get("vertical_services_revision") != OLD_VERTICAL:
        raise RuntimeError("unexpected prior vertical-services revision")
    if item.get("runtime_readiness_claimed") is not False:
        raise RuntimeError("proof origin unexpectedly claims runtime readiness")

    item.pop("a11oy_publisher_revision")
    item.update(
        {
            "a11oy_public_taxonomy_revision": PUBLIC_TAXONOMY,
            "a11oy_intelligence_publisher_revision": INTELLIGENCE_PUBLISHER,
            "vertical_services_revision": VERTICAL_SOURCE,
            "vertical_services_runtime_version": RUNTIME_VERSION,
            "runtime_readiness_claimed": False,
            "runtime_readiness_authority": "EXACT_PROVIDER_READBACK_REQUIRED",
        }
    )
    data["contract_version"] = "1.2.0"
    DECISION.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def patch_record() -> None:
    data = json.loads(RECORD.read_text(encoding="utf-8"))
    evidence = data["evidence"]
    expected = {
        "killinchu_merge": KILLINCHU,
        "a11oy_frontier_publisher_merge": OLD_A11OY,
        "vertical_services_source": OLD_VERTICAL,
    }
    if evidence != expected:
        raise RuntimeError(f"unexpected pre-repin evidence: {evidence}")
    data["schema"] = "szl.aegis-killinchu-consolidation/v2"
    data["evidence"] = {
        "killinchu_consolidation_merge": KILLINCHU,
        "a11oy_public_taxonomy_merge": PUBLIC_TAXONOMY,
        "a11oy_intelligence_v4_publisher_merge": INTELLIGENCE_PUBLISHER,
        "vertical_services_source": VERTICAL_SOURCE,
        "vertical_services_runtime_version": RUNTIME_VERSION,
    }
    data["runtime_readiness_claimed"] = False
    data["runtime_readiness_authority"] = "EXACT_PROVIDER_READBACK_REQUIRED"
    data["publication_authority"] = "SZL_HOLDINGS_A11OY_PROTECTED_MAIN_HF_SYNC"
    RECORD.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def patch_test() -> None:
    text = TEST.read_text(encoding="utf-8")
    anchor = 'OLD = "https://a-11-oy.com/aegis"\n'
    constants = (
        anchor
        + f'PUBLIC_TAXONOMY = "{PUBLIC_TAXONOMY}"\n'
        + f'INTELLIGENCE_PUBLISHER = "{INTELLIGENCE_PUBLISHER}"\n'
        + f'VERTICAL_SOURCE = "{VERTICAL_SOURCE}"\n'
        + f'RUNTIME_VERSION = "{RUNTIME_VERSION}"\n'
    )
    text = replace_once(text, anchor, constants, label="test constants")
    old_block = '''        self.assertEqual(record["current_public_authority"], "SZLHOLDINGS/killinchu")
        self.assertEqual(record["formula_authority_on_proof_origin"], "NONE")
        self.assertFalse(record["runtime_readiness_claimed"])
        self.assertEqual(len(record["capability_planes"]), 5)
'''
    new_block = '''        self.assertEqual(record["schema"], "szl.aegis-killinchu-consolidation/v2")
        self.assertEqual(record["current_public_authority"], "SZLHOLDINGS/killinchu")
        self.assertEqual(record["formula_authority_on_proof_origin"], "NONE")
        self.assertFalse(record["runtime_readiness_claimed"])
        self.assertEqual(record["runtime_readiness_authority"], "EXACT_PROVIDER_READBACK_REQUIRED")
        self.assertEqual(len(record["capability_planes"]), 5)
        evidence = record["evidence"]
        self.assertEqual(evidence["a11oy_public_taxonomy_merge"], PUBLIC_TAXONOMY)
        self.assertEqual(evidence["a11oy_intelligence_v4_publisher_merge"], INTELLIGENCE_PUBLISHER)
        self.assertEqual(evidence["vertical_services_source"], VERTICAL_SOURCE)
        self.assertEqual(evidence["vertical_services_runtime_version"], RUNTIME_VERSION)
'''
    text = replace_once(text, old_block, new_block, label="machine-record assertions")
    old_decision = '''        self.assertFalse(data["consolidations"]["aegis"]["runtime_readiness_claimed"])
'''
    new_decision = '''        consolidation = data["consolidations"]["aegis"]
        self.assertFalse(consolidation["runtime_readiness_claimed"])
        self.assertEqual(consolidation["a11oy_public_taxonomy_revision"], PUBLIC_TAXONOMY)
        self.assertEqual(consolidation["a11oy_intelligence_publisher_revision"], INTELLIGENCE_PUBLISHER)
        self.assertEqual(consolidation["vertical_services_revision"], VERTICAL_SOURCE)
        self.assertEqual(consolidation["vertical_services_runtime_version"], RUNTIME_VERSION)
'''
    text = replace_once(text, old_decision, new_decision, label="decision assertions")
    TEST.write_text(text, encoding="utf-8")


def main() -> int:
    patch_page()
    patch_decision()
    patch_record()
    patch_test()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
