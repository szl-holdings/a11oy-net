# SPDX-License-Identifier: Apache-2.0
"""Fixture tests for scripts/generate_hf_inventory.py (stdlib only, no network)."""

from __future__ import annotations

import importlib.util
import hashlib
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "hf_api"
SPEC = importlib.util.spec_from_file_location("generate_hf_inventory", ROOT / "scripts" / "generate_hf_inventory.py")
assert SPEC is not None and SPEC.loader is not None
gen = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gen)

T1 = "2026-09-29T06:00:00Z"
T2 = "2026-09-30T06:00:00Z"
PAGE = """<!doctype html>
<p>models <b data-hf-current="counts.models">—</b> · observed <span data-hf-current="observed_at">—</span></p>
<ul>
    <!-- hf-current:live-space-rows begin · generated -->
    <li>stale row</li>
    <!-- hf-current:live-space-rows end -->
</ul>
"""


def fixture(name: str):
    return json.loads((FIXTURE / name).read_text(encoding="utf-8"))


def rebind(raw):
    """A changed synthetic source and observation; never used for live outputs."""
    manifest = json.loads(raw["canonical_source"]["manifest_text"])
    spaces = list(raw["spaces"])
    listed = {row["id"] for row in spaces}
    spaces.extend(row for row in raw["special_spaces"].values()
                  if row.get("private") is False and row["id"] not in listed)
    rows = {"models": raw["models"], "datasets": raw["datasets"], "spaces": spaces}
    manifest["inventory"] = rows
    manifest["counts"] = {kind: len(value) for kind, value in rows.items()}
    content = (json.dumps(manifest, indent=2) + "\n").encode()
    blob = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
    raw["canonical_source"] = gen.canonical_source(content, "a" * 40, blob)
    return raw


class SiteCopy:
    """A throwaway site root holding the inputs the generator reads."""

    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        for relative in ("spaces.json", "models.json", "estate.json", "public-inventory-2026-08-31.json"):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        for page in gen.PAGES:
            target = self.root / page
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(PAGE, encoding="utf-8")

    def run(self, observed_at: str, raw=None) -> tuple[dict[str, str], list[str]]:
        raw = raw if raw is not None else gen.collect(gen.FixtureSource(FIXTURE))
        outputs = gen.generate(self.root, raw, observed_at)
        changed = gen.write(self.root, outputs, dry_run=False, log=lambda _line: None)
        return outputs, changed

    def read(self, relative: str):
        return json.loads((self.root / relative).read_text(encoding="utf-8"))

    def close(self) -> None:
        self._tmp.cleanup()


class GeneratorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.site = SiteCopy()

    def tearDown(self) -> None:
        self.site.close()

    def test_counts_equal_the_fixture_listing(self) -> None:
        self.site.run(T1)
        inventory = self.site.read(gen.INVENTORY_PATH)
        current = self.site.read(gen.CURRENT_PATH)
        listed_spaces = len(fixture("spaces.json"))
        self.assertEqual(inventory["counts"]["models"], len(fixture("models.json")))
        self.assertEqual(inventory["counts"]["datasets"], len(fixture("datasets.json")))
        self.assertEqual(inventory["counts"]["kernels"], len(fixture("kernels.json")))
        self.assertEqual(inventory["counts"]["spaces_list_api_rows"], listed_spaces)
        self.assertEqual(inventory["counts"]["special_spaces_added"], 1)
        self.assertEqual(inventory["counts"]["spaces"], listed_spaces + 1)
        repository_total = len(fixture("models.json")) + len(fixture("datasets.json")) + listed_spaces + 1
        self.assertEqual(inventory["counts"]["repository_membership_total"], repository_total)
        self.assertEqual(inventory["counts"]["public_resources_total"],
                         repository_total + len(fixture("collections.json")) + len(fixture("buckets.json")))
        self.assertEqual(inventory["claim_boundaries"]["kernel_membership"],
                         "MODEL_SUBSET_COUNTED_ONCE_IN_TOTALS")
        self.assertEqual(current["counts"]["spaces_public"], listed_spaces + 1)
        self.assertEqual(inventory["private_assets"], "NOT_OBSERVED")
        self.assertEqual(current["private_assets"], "NOT_OBSERVED")
        self.assertEqual(inventory["content_sha256"], gen.inventory_content_sha(inventory))
        for kind, rows in inventory["resources"].items():
            ids = [row.get("id") or row.get("slug") for row in rows]
            self.assertEqual(ids, sorted(ids), kind)
        bucket = inventory["resources"]["buckets"][0]
        self.assertEqual(bucket["observed_object_count"], 2)
        self.assertEqual(bucket["observed_size_bytes"], 2778)
        collection = inventory["resources"]["collections"][0]
        self.assertEqual(collection["item_count"], 3)
        self.assertEqual(inventory["collection_coverage"]["models"]["covered"], 1)
        stages = inventory["spaces_by_runtime_stage"]
        self.assertEqual(stages, {"BUILD_ERROR": 1, "RUNNING": listed_spaces})
        grid = next(row for row in inventory["resources"]["spaces"] if row["id"].endswith("/the-grid"))
        self.assertEqual(grid["runtime"]["repository_revision_state"], "DIFFERS_FROM_REPOSITORY_HEAD")
        readme = next(row for row in inventory["resources"]["spaces"] if row["id"].endswith("/README"))
        self.assertEqual(readme["listing"], "SPECIAL_SPACE_OUTSIDE_LIST_API")
        self.assertEqual(readme["canonical_live_url"], "https://szlholdings-readme.static.hf.space/")

    def test_same_observation_is_byte_identical(self) -> None:
        raw = gen.collect(gen.FixtureSource(FIXTURE))
        first = gen.generate(self.site.root, raw, T1)
        second = gen.generate(self.site.root, raw, T1)
        self.assertEqual(first, second)

    def test_unchanged_content_keeps_its_observation_time(self) -> None:
        self.site.run(T1)
        outputs, changed = self.site.run(T2)
        self.assertEqual(changed, [])
        self.assertEqual(json.loads(outputs[gen.INVENTORY_PATH])["observed_at"], T1)

    def test_changed_content_takes_the_new_observation_time(self) -> None:
        self.site.run(T1)
        raw = gen.collect(gen.FixtureSource(FIXTURE))
        raw["models"] = raw["models"][1:]
        rebind(raw)
        _outputs, changed = self.site.run(T2, raw)
        self.assertIn(gen.INVENTORY_PATH, changed)
        self.assertIn(gen.MODELS_PATH, changed)
        self.assertEqual(self.site.read(gen.INVENTORY_PATH)["observed_at"], T2)
        self.assertEqual(self.site.read(gen.MODELS_PATH)["captured_at"], T2)
        self.assertEqual(self.site.read(gen.MODELS_PATH)["hub"]["models"], len(raw["models"]))

    def test_classification_follows_the_published_class_rules(self) -> None:
        expected = {
            "SZLHOLDINGS/chaski": "TRAINED_WEIGHTS",
            "SZLHOLDINGS/Moons-Nano": "NANO_SYNTHETIC",
            "SZLHOLDINGS/szl-maskmod": "KERNEL_SOFTWARE",
            "SZLHOLDINGS/szl-block-kv": "CODE_OR_SCRIPTS",
            "SZLHOLDINGS/qantu": "ROADMAP_EMPTY",
            "SZLHOLDINGS/szl-training-scripts": "CODE_OR_SCRIPTS",
            "SZLHOLDINGS/szl-energy-attest": "ROADMAP_EMPTY",
            "SZLHOLDINGS/SZLHOLDINGS": "CODE_OR_SCRIPTS",
            "SZLHOLDINGS/SZL-Khipu-1.5B-abstain": "TRAINED_WEIGHTS",
        }
        observed = {item["id"]: gen.classify_model(item) for item in fixture("models.json")}
        self.assertEqual(observed, expected)
        chaski = next(item for item in fixture("models.json") if item["id"].endswith("/chaski"))
        self.assertNotIn("training_args.bin", gen.weight_files(gen.siblings_of(chaski)))

    def test_models_contract_counts_and_bench_carry_rule(self) -> None:
        self.site.run(T1)
        contract = self.site.read(gen.MODELS_PATH)
        rows = {row["id"]: row for row in contract["models"]}
        self.assertEqual(sum(contract["counts"].values()), len(rows))
        self.assertEqual(contract["hub"]["private"], "NOT_OBSERVED")
        # Same class and the bench source file is still listed: carried forward.
        self.assertEqual(rows["SZLHOLDINGS/chaski"]["bench"]["source"], "eval_measured.json")
        # Class changed since the curated record (weights now present): not carried.
        self.assertIsNone(rows["SZLHOLDINGS/SZL-Khipu-1.5B-abstain"]["bench"])
        self.assertIs(contract["trained_all"], False)
        self.assertFalse(any(row["operational"] for row in rows.values()))

    def test_live_space_cards_follow_keep_policy_and_withhold_killinchu(self) -> None:
        self.site.run(T1)
        cards = self.site.read(gen.CURRENT_PATH)["live_space_cards"]
        keep = [f"SZLHOLDINGS/{row['id']}" for row in self.site.read("spaces.json")["keep"]]
        ids = [card["id"] for card in cards]
        self.assertEqual(ids, [i for i in keep if i in ("SZLHOLDINGS/a11oy", "SZLHOLDINGS/szl-atelier")])
        self.assertNotIn("SZLHOLDINGS/killinchu", ids)
        presence = self.site.read("spaces.json")["hub_presence"]
        self.assertIn("killinchu", presence["keep"]["listed"])
        self.assertIn("governed-receipt-verifier", presence["keep"]["not_listed"])

    def test_pages_render_fields_and_rows_idempotently(self) -> None:
        outputs, _changed = self.site.run(T1)
        page = outputs["index.html"]
        count = len(fixture("models.json"))
        self.assertIn(f'<b data-hf-current="counts.models">{count}</b>', page)
        self.assertIn(f'<span data-hf-current="observed_at">{T1}</span>', page)
        self.assertNotIn("stale row", page)
        self.assertEqual(page.count('data-space="SZLHOLDINGS/'), 2)
        current = self.site.read(gen.CURRENT_PATH)
        self.assertEqual(gen.render_page(page, current), page)
        with self.assertRaises(gen.GenerationError):
            gen.render_page('<b data-hf-current="counts.nope">1</b>', current)

    def test_refuses_rows_it_must_not_publish(self) -> None:
        raw = gen.collect(gen.FixtureSource(FIXTURE))
        leaked = json.loads(json.dumps(raw))
        leaked["datasets"].append({"id": "SZLHOLDINGS/secret", "private": True})
        with self.assertRaises(gen.GenerationError):
            gen.build_inventory(leaked, T1)
        foreign = json.loads(json.dumps(raw))
        foreign["models"].append({"id": "someone-else/model", "private": False})
        with self.assertRaises(gen.GenerationError):
            gen.build_inventory(foreign, T1)
        storefront = json.loads(json.dumps(raw))
        storefront["spaces"][0]["cardData"]["title"] = "visit a11" + "oy.com"
        with self.assertRaises(gen.GenerationError):
            gen.build_inventory(storefront, T1)
        with self.assertRaises(gen.GenerationError):
            gen.generate(self.site.root, raw, "2026-02-30T00:00:00Z")

    def test_refuses_a_listing_that_may_be_truncated(self) -> None:
        class FullPage(gen.FixtureSource):
            def listing(self, kind: str):
                rows = super().listing(kind)
                if kind == "collections":
                    return [dict(rows[0], slug=f"{rows[0]['slug']}-{i}") for i in range(gen.LISTING_LIMIT[kind])]
                return rows

        with self.assertRaises(gen.GenerationError):
            gen.collect(FullPage(FIXTURE))
        self.assertIsInstance(gen.collect(gen.FixtureSource(FIXTURE)), dict)

    def test_generator_holds_no_token_and_no_write_path(self) -> None:
        source = (ROOT / "scripts" / "generate_hf_inventory.py").read_text(encoding="utf-8")
        for forbidden in ("HF_TOKEN", "Authorization", "os.environ", "upload_", "create_commit", "method=\"POST\""):
            self.assertNotIn(forbidden, source)

    def test_canonical_binding_retains_exact_bytes_and_all_three_memberships(self) -> None:
        outputs, _ = self.site.run(T1)
        current = self.site.read(gen.CURRENT_PATH)
        record = self.site.read(gen.MEMBERSHIP_PATH)
        source = (self.site.root / gen.CANONICAL_COPY_PATH).read_bytes()
        self.assertEqual(source, (FIXTURE / "canonical_manifest.json").read_bytes())
        self.assertEqual(record["source_sha256"], hashlib.sha256(source).hexdigest())
        self.assertEqual(record, current["canonical_membership_source"])
        self.assertEqual(record["scope_sha256"], hashlib.sha256(gen.canonical(gen.PUBLIC_SCOPE)).hexdigest())
        self.assertFalse(record["production_authorization"])
        self.assertIn(gen.MEMBERSHIP_PATH, outputs)

    def test_observed_membership_drift_missing_binding_and_kernel_only_are_blocking(self) -> None:
        original = gen.collect(gen.FixtureSource(FIXTURE))
        for kind in ("models", "datasets", "spaces"):
            raw = copy.deepcopy(original)
            raw[kind] = raw[kind][1:]
            with self.subTest(kind=kind), self.assertRaises(gen.GenerationError):
                gen.build_inventory(raw, T1)
        missing = copy.deepcopy(original)
        del missing["canonical_source"]
        with self.assertRaises(gen.GenerationError):
            gen.build_inventory(missing, T1)
        kernel_only = copy.deepcopy(original)
        kernel_only["kernels"][0]["id"] = "SZLHOLDINGS/unlisted-kernel"
        with self.assertRaises(gen.GenerationError):
            gen.build_inventory(kernel_only, T1)

    def test_canonical_scope_blob_duplicate_keys_and_private_disposition_are_blocking(self) -> None:
        original = (FIXTURE / "canonical_manifest.json").read_bytes()
        manifest = json.loads(original)
        variants = [
            {**manifest, "schemaVersion": 1},
            {**manifest, "org": "someone-else"},
            {**manifest, "inventoryScope": {**manifest["inventoryScope"], "authenticated": True}},
            {**manifest, "inventoryScope": {**manifest["inventoryScope"], "visibility": "all"}},
            {**manifest, "inventoryScope": {**manifest["inventoryScope"], "privateAssetsIncluded": True}},
            {**manifest, "counts": {**manifest["counts"], "spaces": True}},
            {**manifest, "counts": {**manifest["counts"], "models": manifest["counts"]["models"] + 1}},
            {**manifest, "inventory": {**manifest["inventory"], "spaces":
             [{**manifest["inventory"]["spaces"][0], "private": True}] + manifest["inventory"]["spaces"][1:]}},
            {**manifest, "inventory": {**manifest["inventory"], "spaces":
             [{**manifest["inventory"]["spaces"][0], "private": None}] + manifest["inventory"]["spaces"][1:]}},
            {**manifest, "inventory": {**manifest["inventory"], "models":
             [{**manifest["inventory"]["models"][0], "id": "other/model"}] + manifest["inventory"]["models"][1:]}},
            {**manifest, "observedAt": "2026-09-29"},
        ]
        raw_variants = [json.dumps(value).encode() for value in variants]
        raw_variants.extend((b"{broken", original.rstrip()[:-1] + b',"counts":{}}',
                             b'{"schemaVersion":NaN}', b'{"schemaVersion":1e999}'))
        for raw in raw_variants:
            blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            with self.subTest(raw=raw[:80]), self.assertRaises(gen.GenerationError):
                gen.canonical_source(raw, "a" * 40, blob)
        with self.assertRaises(gen.GenerationError):
            gen.canonical_source(original, "main", "b" * 40)
        with self.assertRaises(gen.GenerationError):
            gen.canonical_source(original, "a" * 40, "b" * 40)

    def test_live_source_resolves_signed_head_then_reads_immutable_manifest(self) -> None:
        raw = (FIXTURE / "canonical_manifest.json").read_bytes()
        blob = fixture("canonical_source.json")["source_git_blob"]
        source = gen.LiveSource(attempts=1)
        with mock.patch.object(source, "_get", side_effect=[
            {"sha": "a" * 40, "commit": {"verification": {"verified": True}}},
            {"type": "file", "path": gen.CANONICAL_PATH, "sha": blob},
        ]) as metadata, mock.patch.object(source, "_bytes", return_value=raw) as content:
            result = source.canonical_source()
        self.assertEqual(result["record"]["source_revision"], "a" * 40)
        self.assertIn("ref=" + "a" * 40, metadata.call_args_list[1].args[0])
        self.assertIn("/" + "a" * 40 + "/", content.call_args.args[0])
        with mock.patch.object(source, "_get", return_value={"sha": "a" * 40,
             "commit": {"verification": {"verified": False}}}):
            with self.assertRaises(gen.GenerationError):
                source.canonical_source()
        with mock.patch.object(source, "_get", return_value={"sha": "b" * 40}):
            with self.assertRaisesRegex(gen.GenerationError, "advanced"):
                source.validate_source_head("a" * 40)

    def test_unknown_public_disposition_and_reserved_identity_are_blocking(self) -> None:
        original = gen.collect(gen.FixtureSource(FIXTURE))
        for value in (None, 0, "false"):
            for kind in ("models", "datasets", "spaces"):
                raw = copy.deepcopy(original)
                raw[kind][0]["private"] = value
                with self.subTest(kind=kind, value=value), self.assertRaises(gen.GenerationError):
                    gen.build_inventory(raw, T1)
            raw = copy.deepcopy(original)
            raw["special_spaces"]["README"]["private"] = value
            with self.subTest(reserved=value), self.assertRaises(gen.GenerationError):
                gen.build_inventory(raw, T1)
        raw = copy.deepcopy(original)
        raw["special_spaces"]["README"]["id"] = "other/README"
        with self.assertRaises(gen.GenerationError):
            gen.build_inventory(raw, T1)

    def test_equal_counts_different_source_membership_and_reserved_omission_block(self) -> None:
        original = gen.collect(gen.FixtureSource(FIXTURE))
        advanced = copy.deepcopy(original)
        advanced["models"][0]["id"] = "SZLHOLDINGS/new-source-model"
        rebind(advanced)
        original["canonical_source"] = advanced["canonical_source"]
        with self.assertRaises(gen.GenerationError):
            gen.build_inventory(original, T1)
        raw = gen.collect(gen.FixtureSource(FIXTURE))
        raw["special_spaces"] = {}
        with self.assertRaises(gen.GenerationError):
            gen.build_inventory(raw, T1)

    def test_refresh_workflow_is_scheduled_locked_tokenless_and_never_merges(self) -> None:
        text = (ROOT / gen.REFRESH_WORKFLOW).read_text(encoding="utf-8")
        self.assertRegex(text, r"(?m)^  schedule:\n    - cron: \"[0-9*/ ,-]+\"$")
        self.assertRegex(text, r"(?m)^  workflow_dispatch:$")
        # One lock for every trigger: never keyed by event name.
        self.assertRegex(text, r"(?m)^concurrency:\n  group: hf-inventory-refresh\n  cancel-in-progress: false$")
        self.assertNotIn("event_name }}", text.split("jobs:", 1)[0])
        self.assertIn("python3 scripts/generate_hf_inventory.py", text)
        self.assertIn("python3 scripts/check_proof_surface.py", text)
        # No Hugging Face credential of any name, and no merge path.
        self.assertNotRegex(text, r"secrets\.(HF_|HUGGING|HUB_)")
        self.assertNotIn("gh pr merge", text)
        self.assertNotIn("--admin", text)
        # main requires verified signatures: the refresh commit is created
        # through GraphQL createCommitOnBranch (GitHub-signed), never pushed.
        self.assertNotRegex(text, r"(?m)^\s*git (commit|push)\b")
        self.assertIn("python3 scripts/verified_commit_payload.py", text)
        self.assertIn("gh api graphql --input", text)
        self.assertIn('branch="bot/hf-inventory-', text)
        for line in text.splitlines():
            if "uses:" in line and not line.lstrip().startswith("#"):
                self.assertRegex(line, r"@[0-9a-f]{40}\b", line)


if __name__ == "__main__":
    unittest.main()
