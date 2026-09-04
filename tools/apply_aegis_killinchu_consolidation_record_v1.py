#!/usr/bin/env python3
"""Preserve Aegis evidence while converging current product authority on Killinchu."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AEGIS_PAGE = ROOT / "aegis" / "index.html"
DECISION = ROOT / "decision.json"
SPACES = ROOT / "spaces.json"
RECORD = ROOT / "consolidation" / "aegis-killinchu-20260903.json"
TEST = ROOT / "tests" / "test_aegis_killinchu_consolidation.py"

KILLINCHU_HUB = "https://huggingface.co/spaces/SZLHOLDINGS/killinchu"
KILLINCHU_SOURCE = "https://github.com/szl-holdings/killinchu"
KILLINCHU_REVISION = "928a6dace657f8f9e067773d23d5686fe3dcc716"
A11OY_REVISION = "775acaa54724ab206b0c5477d754fbd6ed36e5f7"
VERTICAL_SERVICES_REVISION = "e08231a110fd80f85a61fba82d72ab7f1fe23836"
OLD_PRODUCT_URL = "https://a-11-oy.com/aegis"

INDEX_FILES = (
    ROOT / "README.md",
    ROOT / "FRONT_DOOR.md",
    ROOT / "llms.txt",
    ROOT / "index.html",
    ROOT / "decision" / "index.html",
    ROOT / "vessels" / "index.html",
    ROOT / "scripts" / "szl-holo-proof-v2.js",
)


def replace_once(text: str, old: str, new: str, *, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def regex_once(text: str, pattern: str, replacement: str, *, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.DOTALL)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return updated


def patch_aegis_page() -> None:
    text = AEGIS_PAGE.read_text(encoding="utf-8")
    replacements = (
        (
            "<title>Aegis Assurance — RECORD on a11oy.net</title>",
            "<title>Aegis → Killinchu — Consolidation RECORD on a11oy.net</title>",
            "title",
        ),
        (
            '<meta name="description" content="Aegis Assurance Decision Assurance RECORD. Frozen cases. Formula authority NONE. Kernel is not run here. Evaluate on a-11-oy.com/aegis."/>',
            '<meta name="description" content="Historical Aegis assurance evidence preserved after consolidation into Killinchu. Formula authority NONE. This proof origin does not run the kernel or establish runtime readiness."/>',
            "meta description",
        ),
        (
            '<meta property="og:title" content="Aegis Assurance — RECORD on a11oy.net"/>',
            '<meta property="og:title" content="Aegis → Killinchu — Consolidation RECORD"/>',
            "Open Graph title",
        ),
        (
            '<meta property="og:description" content="Proof-origin stub of Packet 8 Aegis Assurance. Evaluate on a-11-oy.com/aegis. Hub Spaces are not required."/>',
            '<meta property="og:description" content="Frozen Aegis assurance cases remain inspectable; current public cyber-physical resilience authority is Killinchu."/>',
            "Open Graph description",
        ),
        ("  <h1>Aegis Assurance</h1>", "  <h1>Aegis → Killinchu</h1>", "heading"),
        (
            '  <p class="lede">Exposure-to-Remediation Decision Assurance. Parallel enterprise proof. Frozen demonstration cases. Fail-closed. Formulas do not grant authority. This origin indexes the cases. It does not run the kernel.</p>',
            '  <p class="lede">Aegis is preserved here as an assurance and portfolio lens, not a separate product. Current public cyber-physical resilience authority is Killinchu; Sentra / Defend, IMMUNE, Vessels / Maritime, and Counter-UAS / Airspace remain capability planes inside that governed product boundary. Frozen Aegis cases remain inspectable. This origin does not run the kernel.</p>',
            "lede",
        ),
        ('    <span class="chip mute">ROADMAP</span>', '    <span class="chip">CONSOLIDATED</span>', "status chip"),
        (
            '    <span class="chip mute">Hub Spaces not required</span>',
            '    <span class="chip mute">runtime readback required</span>',
            "runtime chip",
        ),
        (
            f'    <a href="{OLD_PRODUCT_URL}">Evaluate on product · a-11-oy.com/aegis</a>',
            f'    <a href="{KILLINCHU_HUB}">Open current product authority · Killinchu</a>',
            "primary product link",
        ),
        (
            '  <p class="foot">Canonical source: github.com/szl-holdings/a11oy/verticals/aegis · Product origin a-11-oy.com · Proof origin a11oy.net · Apache-2.0 · Doctrine v11</p>',
            '  <p class="foot">Historical Aegis proof: a11oy.net/aegis/ · Current product source: github.com/szl-holdings/killinchu · Current public product authority: SZLHOLDINGS/killinchu · Proof origin a11oy.net · Apache-2.0 · Doctrine v11</p>',
            "footer authority",
        ),
    )
    for old, new, label in replacements:
        text = replace_once(text, old, new, label=label)

    current_authority = f'''  <section class="card">
    <h2>One current product authority. Preserved historical proof.</h2>
    <p><b>Aegis</b> is now an internal assurance and portfolio capability plane inside <a href="{KILLINCHU_HUB}">Killinchu</a>. It does not retain an independent product, runtime, model, or action authority.</p>
    <p><b>Killinchu</b> is the current public cyber-physical resilience boundary. Its capability planes are Aegis; Sentra / Defend; IMMUNE; Vessels / Maritime; and Counter-UAS / Airspace. Consequential execution remains policy-gated, human-authorized, independently verified, and receipted.</p>
    <p><b>This page</b> is a static RECORD. It preserves frozen Aegis cases and their expected decisions. A source merge, public repository, or reachable URL does not by itself prove deployed source parity or runtime readiness.</p>
  </section>
'''
    text = regex_once(
        text,
        r'  <section class="card">\n    <h2>Two origins\. Two jobs\.</h2>.*?  </section>\n',
        current_authority,
        label="authority section",
    )

    insertion = f'''  <section class="card">
    <h2>Consolidation evidence</h2>
    <table>
      <tbody>
        <tr><th>Killinchu source</th><td><a href="{KILLINCHU_SOURCE}">szl-holdings/killinchu</a></td></tr>
        <tr><th>Killinchu merge</th><td><code>{KILLINCHU_REVISION}</code></td></tr>
        <tr><th>A11oy publisher merge</th><td><code>{A11OY_REVISION}</code></td></tr>
        <tr><th>Vertical-services source</th><td><code>{VERTICAL_SERVICES_REVISION}</code></td></tr>
        <tr><th>Proof posture</th><td>STATIC RECORD · formula authority NONE · runtime not claimed</td></tr>
      </tbody>
    </table>
  </section>

'''
    marker = '  <section class="card">\n    <h2>Frozen cases</h2>'
    text = replace_once(text, marker, insertion + marker, label="consolidation evidence insertion")

    text = text.replace(
        'That stays on a-11-oy.com/aegis.',
        'Current evaluation belongs to the source-bound Killinchu product boundary.',
    )
    if OLD_PRODUCT_URL in text:
        raise RuntimeError("obsolete standalone Aegis product URL survived on proof page")
    AEGIS_PAGE.write_text(text, encoding="utf-8")


def patch_decision_contract() -> None:
    data = json.loads(DECISION.read_text(encoding="utf-8"))
    if data.get("formula_authority") != "NONE" or data.get("runtime_claimed") is not False:
        raise RuntimeError("decision proof boundary changed unexpectedly")
    data["contract_version"] = "1.1.0"
    permalinks = data["permalinks"]
    if permalinks.get("product_aegis") != OLD_PRODUCT_URL:
        raise RuntimeError("unexpected product_aegis pre-convergence value")
    permalinks["product_aegis"] = KILLINCHU_HUB
    permalinks["source_killinchu"] = KILLINCHU_SOURCE

    for row in data["verticals"]:
        if row.get("id") == "aegis":
            row.update(
                {
                    "display_name": "Aegis → Killinchu Capability RECORD",
                    "wedge": "Exposure-to-Remediation assurance preserved inside Killinchu",
                    "public_authority": "killinchu",
                    "runtime_claimed": False,
                }
            )
            break
    else:
        raise RuntimeError("decision contract has no Aegis vertical")

    for row in data["adapters"]:
        if row.get("id") == "aegis-assurance":
            row.update(
                {
                    "state": "legacy-space-retirement-authorized",
                    "sink": KILLINCHU_HUB,
                    "consolidated_into": "SZLHOLDINGS/killinchu",
                }
            )
            break
    else:
        raise RuntimeError("decision contract has no Aegis adapter")

    data["consolidations"] = {
        "aegis": {
            "proof_route": "https://a11oy.net/aegis/",
            "current_public_authority": "SZLHOLDINGS/killinchu",
            "current_product": KILLINCHU_HUB,
            "current_source": KILLINCHU_SOURCE,
            "capability_planes": [
                "aegis",
                "sentra_defend",
                "immune",
                "vessels_maritime",
                "counter_uas_airspace",
            ],
            "killinchu_revision": KILLINCHU_REVISION,
            "a11oy_publisher_revision": A11OY_REVISION,
            "vertical_services_revision": VERTICAL_SERVICES_REVISION,
            "runtime_readiness_claimed": False,
            "historical_cases_preserved": True,
        }
    }
    DECISION.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def walk(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def patch_space_contract() -> None:
    data = json.loads(SPACES.read_text(encoding="utf-8"))
    data["contract_version"] = "1.2.0"
    changed = 0
    for row in walk(data):
        if row.get("id") == "aegis-assurance":
            row["dest"] = KILLINCHU_HUB
            row["sink"] = "product"
            row["hub"] = "legacy-space-retirement-authorized"
            row["consolidated_into"] = "SZLHOLDINGS/killinchu"
            row["why"] = (
                "Aegis is an internal assurance capability plane inside Killinchu, not a sibling public product. "
                "Preserve the proof route; retire the duplicate Space only after exact-source and terminal-absence checks."
            )
            changed += 1
    if changed < 1:
        raise RuntimeError("spaces contract has no Aegis adapter")
    packet8 = data.get("packet8", {})
    if isinstance(packet8, dict):
        packet8["hub_create_note"] = (
            "Aegis no longer requires a sibling Space: preserve /aegis/ as proof and use Killinchu as current product authority. "
            "Other Packet 8 adapters remain governed by their own source and runtime evidence."
        )
    data["aegis_killinchu_consolidation"] = {
        "status": "SOURCE_MERGED_PROVIDER_RETIREMENT_GATED",
        "proof_route_preserved": "https://a11oy.net/aegis/",
        "current_public_authority": "SZLHOLDINGS/killinchu",
        "killinchu_revision": KILLINCHU_REVISION,
        "runtime_readiness_claimed": False,
    }
    SPACES.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def patch_indexes() -> None:
    for path in INDEX_FILES:
        text = path.read_text(encoding="utf-8")
        original = text
        text = text.replace(
            '<a href="https://a-11-oy.com/aegis">/aegis</a>',
            f'<a href="{KILLINCHU_HUB}">Aegis→Killinchu</a>',
        )
        text = text.replace(
            "- Aegis RECORD stub (evaluate at a-11-oy.com/aegis): https://a11oy.net/aegis/",
            "- Aegis → Killinchu consolidation RECORD (historical cases preserved; current authority SZLHOLDINGS/killinchu): https://a11oy.net/aegis/",
        )
        text = text.replace(
            '<li><a href="/aegis/">Aegis</a> — Exposure-to-Remediation RECORD stub. Evaluate on a-11-oy.com/aegis. Kernel is not run here.</li>',
            '<li><a href="/aegis/">Aegis → Killinchu</a> — historical Exposure-to-Remediation cases preserved as a consolidation RECORD. Current product authority is SZLHOLDINGS/killinchu. Kernel is not run here.</li>',
        )
        text = text.replace(OLD_PRODUCT_URL, KILLINCHU_HUB)
        text = text.replace(
            "Aegis RECORD stub",
            "Aegis → Killinchu consolidation RECORD",
        )
        text = text.replace("Aegis RECORD", "Aegis → Killinchu RECORD")
        text = text.replace("Aegis Record", "Aegis → Killinchu Record")
        if path.name == "index.html" and path.parent.name == "vessels":
            text = text.replace(
                'https://a-11-oy.com/vessels',
                KILLINCHU_HUB,
            ).replace(
                "Evaluate on product · a-11-oy.com/vessels",
                "Open current product authority · Killinchu",
            )
        if path.name == "README.md" and "<!-- AEGIS-KILLINCHU-CONSOLIDATION:v1 -->" not in text:
            text += f'''\n\n<!-- AEGIS-KILLINCHU-CONSOLIDATION:v1 -->
## Aegis → Killinchu consolidation

`/aegis/` remains a static historical proof route. Aegis is not a separate current product authority: it is an assurance and portfolio capability plane inside [Killinchu]({KILLINCHU_HUB}). Sentra / Defend, IMMUNE, Vessels / Maritime, and Counter-UAS / Airspace are internal capability planes. Runtime readiness is never inferred from this repository or from URL reachability.
'''
        if path.name == "FRONT_DOOR.md" and "<!-- AEGIS-KILLINCHU-CONSOLIDATION:v1 -->" not in text:
            text += f'''\n\n<!-- AEGIS-KILLINCHU-CONSOLIDATION:v1 -->
## Current resilience authority

- Preserve `/aegis/` as a consolidation RECORD with frozen historical cases.
- Route current product authority to [SZLHOLDINGS/killinchu]({KILLINCHU_HUB}).
- Do not present Aegis, Sentra, IMMUNE, or Vessels as sibling public products.
- Do not claim runtime readiness without exact source-revision and health-contract evidence.
'''
        if text != original:
            path.write_text(text, encoding="utf-8")

    for path in INDEX_FILES:
        if OLD_PRODUCT_URL in path.read_text(encoding="utf-8"):
            raise RuntimeError(f"obsolete standalone Aegis product URL remains in {path.relative_to(ROOT)}")


def write_record_and_test() -> None:
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "schema": "szl.aegis-killinchu-consolidation/v1",
        "effective_date": "2026-09-03",
        "proof_route": "https://a11oy.net/aegis/",
        "proof_route_status": "PRESERVED_HISTORICAL_RECORD",
        "current_public_authority": "SZLHOLDINGS/killinchu",
        "current_product": KILLINCHU_HUB,
        "current_source": KILLINCHU_SOURCE,
        "capability_planes": [
            "aegis",
            "sentra_defend",
            "immune",
            "vessels_maritime",
            "counter_uas_airspace",
        ],
        "evidence": {
            "killinchu_merge": KILLINCHU_REVISION,
            "a11oy_frontier_publisher_merge": A11OY_REVISION,
            "vertical_services_source": VERTICAL_SERVICES_REVISION,
        },
        "formula_authority_on_proof_origin": "NONE",
        "runtime_readiness_claimed": False,
        "historical_cases_preserved": True,
        "legacy_space_retirement": "GATED_BY_EXACT_SOURCE_AND_TERMINAL_ABSENCE",
    }
    RECORD.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    TEST.parent.mkdir(parents=True, exist_ok=True)
    TEST.write_text(
        f'''#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HUB = "{KILLINCHU_HUB}"
OLD = "{OLD_PRODUCT_URL}"


class AegisKillinchuConsolidation(unittest.TestCase):
    def test_aegis_route_is_preserved_as_proof_not_product(self) -> None:
        page = (ROOT / "aegis" / "index.html").read_text(encoding="utf-8")
        self.assertIn("Aegis → Killinchu", page)
        self.assertIn("One current product authority. Preserved historical proof.", page)
        self.assertIn(HUB, page)
        self.assertIn("formula authority NONE", page)
        self.assertIn("runtime not claimed", page)
        self.assertNotIn(OLD, page)

    def test_decision_contract_points_current_authority_to_killinchu(self) -> None:
        data = json.loads((ROOT / "decision.json").read_text(encoding="utf-8"))
        self.assertEqual(data["permalinks"]["product_aegis"], HUB)
        self.assertEqual(data["formula_authority"], "NONE")
        self.assertFalse(data["runtime_claimed"])
        row = next(item for item in data["verticals"] if item["id"] == "aegis")
        self.assertEqual(row["public_authority"], "killinchu")
        adapter = next(item for item in data["adapters"] if item["id"] == "aegis-assurance")
        self.assertEqual(adapter["consolidated_into"], "SZLHOLDINGS/killinchu")
        self.assertFalse(data["consolidations"]["aegis"]["runtime_readiness_claimed"])

    def test_space_contract_preserves_retirement_gate(self) -> None:
        data = json.loads((ROOT / "spaces.json").read_text(encoding="utf-8"))
        state = data["aegis_killinchu_consolidation"]
        self.assertEqual(state["current_public_authority"], "SZLHOLDINGS/killinchu")
        self.assertEqual(state["status"], "SOURCE_MERGED_PROVIDER_RETIREMENT_GATED")
        self.assertFalse(state["runtime_readiness_claimed"])

    def test_machine_record_is_exact_and_non_promotional(self) -> None:
        record = json.loads((ROOT / "consolidation" / "aegis-killinchu-20260903.json").read_text(encoding="utf-8"))
        self.assertEqual(record["current_public_authority"], "SZLHOLDINGS/killinchu")
        self.assertEqual(record["formula_authority_on_proof_origin"], "NONE")
        self.assertFalse(record["runtime_readiness_claimed"])
        self.assertEqual(len(record["capability_planes"]), 5)

    def test_current_facing_indexes_have_no_obsolete_product_url(self) -> None:
        paths = [
            "README.md", "FRONT_DOOR.md", "llms.txt", "index.html",
            "decision/index.html", "vessels/index.html", "scripts/szl-holo-proof-v2.js",
        ]
        for relative in paths:
            with self.subTest(path=relative):
                self.assertNotIn(OLD, (ROOT / relative).read_text(encoding="utf-8"))
        self.assertIn("https://a11oy.net/aegis/", (ROOT / "sitemap.xml").read_text(encoding="utf-8"))
        checker = (ROOT / "scripts" / "check_proof_surface.py").read_text(encoding="utf-8")
        self.assertIn('(\"terra\", \"aegis\",', checker)


if __name__ == "__main__":
    unittest.main()
''',
        encoding="utf-8",
    )


def main() -> int:
    patch_aegis_page()
    patch_decision_contract()
    patch_space_contract()
    patch_indexes()
    write_record_and_test()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
