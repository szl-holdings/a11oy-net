# SPDX-License-Identifier: Apache-2.0
"""Fixture tests for scripts/generate_hf_inventory.py (stdlib only, no network)."""

from __future__ import annotations

import importlib.util
import hashlib
import copy
import json
import shutil
import tempfile
from pathlib import Path
from unittest import TestCase, main, mock

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
        for relative in (
            "spaces.json",
            "models.json",
            "estate.json",
            "public-inventory-2026-08-31.json",
        ):
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


class GeneratorTest(TestCase):
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

    def test_primary_listing_rejects_malformed_repository_identities(self) -> None:
        for name in ("", ".", "..", "a/b", "../outside", "a?query", "a#fragment",
                     "bad name", "bad\tname", "bad\x00name"):
            with self.subTest(name=name), self.assertRaises(gen.GenerationError):
                gen.by_id([{"id": gen.ORG + "/" + name, "private": False}])

    def test_primary_listing_shape_fails_with_a_generation_error(self) -> None:
        for rows in (None, {}, "listing", [None], ["row"], [1], [False],
                     [{"id": None, "private": False}],
                     [{"id": 1, "private": False}]):
            with self.subTest(rows=rows), self.assertRaises(gen.GenerationError):
                gen.by_id(rows)

    def test_canonical_primary_membership_rejects_malformed_names(self) -> None:
        for kind in ("models", "datasets", "spaces"):
            for name in ("", "../outside", "a?query", "bad\x00name"):
                manifest = fixture("canonical_manifest.json")
                manifest["inventory"][kind][0]["id"] = gen.ORG + "/" + name
                content = (json.dumps(manifest, indent=2) + "\n").encode()
                blob = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
                with self.subTest(kind=kind, name=name), self.assertRaises(gen.GenerationError):
                    gen.canonical_source(content, "a" * 40, blob)

    def test_matching_malformed_source_and_observation_cannot_publish(self) -> None:
        raw = gen.collect(gen.FixtureSource(FIXTURE))
        raw["datasets"][0]["id"] = gen.ORG + "/a/../outside"
        with self.assertRaises(gen.GenerationError):
            self.site.run(T1, rebind(raw))
        self.assertFalse((self.site.root / gen.INVENTORY_PATH).exists())

    def test_primary_identity_validation_preserves_valid_names_and_sorting(self) -> None:
        rows = [{"id": gen.ORG + "/" + name, "private": False}
                for name in ("z-model", "README", "model_v1", "model.v2")]
        self.assertEqual(gen.by_id(rows), sorted(rows, key=lambda row: row["id"]))
        self.assertEqual(gen.by_id([]), [])

    def test_primary_and_auxiliary_names_reject_del_and_c1_controls(self) -> None:
        for control in ("\x7f", "\x80", "\x9f"):
            ident = gen.ORG + "/bad" + control + "name"
            with self.subTest(kind="primary", control=control), self.assertRaises(gen.GenerationError):
                gen.by_id([{"id": ident, "private": False}])
            for kind, key in (("collections", "slug"), ("buckets", "id")):
                with self.subTest(kind=kind, control=control), self.assertRaises(gen.GenerationError):
                    gen.public_auxiliary_rows([{key: ident, "private": False}], kind)

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
        self.assertEqual(rows["SZLHOLDINGS/chaski"]["bench"]["evidence_class"], "REPORTED")
        # Class changed since the curated record (weights now present): not carried.
        self.assertIsNone(rows["SZLHOLDINGS/SZL-Khipu-1.5B-abstain"]["bench"])
        self.assertIs(contract["trained_all"], False)
        self.assertFalse(any(row["operational"] for row in rows.values()))

    def test_unwitnessed_generated_contracts_remain_snapshots(self) -> None:
        self.site.run(T1)
        self.assertEqual(self.site.read(gen.CURRENT_PATH)["evidence_class"], "SNAPSHOT")
        models = self.site.read(gen.MODELS_PATH)
        self.assertEqual(models["evidence_class"], "SNAPSHOT")
        self.assertTrue(all(row["bench"]["evidence_class"] == "REPORTED" for row in models["models"] if row["bench"]))
        self.assertEqual(self.site.read("spaces.json")["hub_presence"]["evidence_class"], "SNAPSHOT")

    def test_live_space_cards_follow_keep_policy_and_withhold_killinchu(self) -> None:
        self.site.run(T1)
        cards = self.site.read(gen.CURRENT_PATH)["live_space_cards"]
        keep = [f"SZLHOLDINGS/{row['id']}" for row in self.site.read("spaces.json")["keep"]]
        ids = [card["id"] for card in cards]
        self.assertEqual(
            ids,
            [i for i in keep if i in ("SZLHOLDINGS/a11oy", "SZLHOLDINGS/szl-atelier")],
        )
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
        for forbidden in (
            "HF_TOKEN",
            "Authorization",
            "os.environ",
            "upload_",
            "create_commit",
            'method="POST"',
        ):
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

    @staticmethod
    def _with_native_kernels(manifest: dict, count: int = 2) -> dict:
        kernels = [{**row, "repoType": "kernel"} for row in manifest["inventory"]["models"][:count]]
        return {**manifest, "counts": {**manifest["counts"], "kernels": len(kernels)},
                "inventory": {**manifest["inventory"], "kernels": kernels}}

    @staticmethod
    def _bind(value: dict) -> tuple[bytes, str]:
        raw = json.dumps(value).encode()
        return raw, hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

    def test_canonical_native_kernels_keep_a_separate_typed_namespace(self) -> None:
        manifest = json.loads((FIXTURE / "canonical_manifest.json").read_bytes())
        native = self._with_native_kernels(manifest)
        native["inventory"]["kernels"][0]["id"] = "SZLHOLDINGS/kernel-with-no-model-mirror"
        raw, blob = self._bind(native)
        result = gen.canonical_source(raw, "a" * 40, blob)
        self.assertEqual(result["record"]["schema"], "szl.public-profile-inventory/v2")
        self.assertEqual(result["record"]["scope"], gen.NATIVE_KERNEL_SCOPE)
        self.assertEqual(result["record"]["counts"], native["counts"])
        self.assertEqual(set(result["ids"]), set(gen.NATIVE_KERNEL_SCOPE["kinds"]))
        self.assertEqual(result["ids"]["kernels"], sorted(row["id"] for row in native["inventory"]["kernels"]))

    def test_canonical_native_kernel_ambiguity_and_privacy_are_blocking(self) -> None:
        manifest = json.loads((FIXTURE / "canonical_manifest.json").read_bytes())
        good = self._with_native_kernels(manifest)
        wrong_type = copy.deepcopy(good)
        wrong_type["inventory"]["kernels"][0]["repoType"] = "model"
        private = copy.deepcopy(good)
        private["inventory"]["kernels"][0]["private"] = True
        duplicate = copy.deepcopy(good)
        duplicate["inventory"]["kernels"][1] = duplicate["inventory"]["kernels"][0]
        variants = {
            "count_mismatch": {**good, "counts": {**good["counts"], "kernels": 3}},
            "count_not_int": {**good, "counts": {**good["counts"], "kernels": True}},
            "count_without_rows": {**good, "inventory": manifest["inventory"]},
            "rows_without_count": {**good, "counts": manifest["counts"]},
            "wrong_repository_type": wrong_type,
            "private_kernel": private,
            "duplicate_kernel": duplicate,
            "unknown_kind": {**good, "counts": {**good["counts"], "collections": 0}},
        }
        for name, value in variants.items():
            raw, blob = self._bind(value)
            with self.subTest(name), self.assertRaises(gen.GenerationError):
                gen.canonical_source(raw, "a" * 40, blob)

    def native_observation(self):
        raw = gen.collect(gen.FixtureSource(FIXTURE))
        manifest = json.loads(raw["canonical_source"]["manifest_text"])
        manifest["inventory"]["kernels"] = [dict(row, repoType="kernel") for row in raw["kernels"]]
        manifest["counts"]["kernels"] = len(raw["kernels"])
        content, blob = self._bind(manifest)
        raw["canonical_source"] = gen.canonical_source(content, "a" * 40, blob)
        return raw

    def test_native_kernel_same_id_as_model_counts_both_typed_repositories(self) -> None:
        raw = self.native_observation()
        inventory = gen.build_inventory(raw, T1)
        self.assertEqual(inventory["schema"], "szl.public-hf-inventory/v5")
        expected = sum(inventory["counts"][kind] for kind in ("models", "datasets", "spaces", "kernels"))
        self.assertEqual(inventory["counts"]["repository_membership_total"], expected)
        self.assertEqual(inventory["claim_boundaries"]["kernel_membership"],
                         "SEPARATE_NATIVE_NAMESPACE_COUNTED_ONCE_PER_KIND_AND_ID")
        self.assertEqual(inventory["counts"]["public_resources_total"],
                         expected + inventory["counts"]["collections"] + inventory["counts"]["buckets"])
        self.site.run(T1, raw)
        self.assertEqual(self.site.read(gen.CURRENT_PATH)["schema"], "szl.hf-current/v2")
        native_page = gen.render_page("kernels (included in models)", self.site.read(gen.CURRENT_PATH))
        self.assertEqual(native_page, "kernels (separate native repositories)")
        _, changed = self.site.run(T2, raw)
        self.assertEqual(changed, [])

    def test_native_kernel_membership_drift_is_rejected_even_for_a_model_id(self) -> None:
        original = self.native_observation()
        for change in ("swap", "missing", "empty"):
            raw = copy.deepcopy(original)
            if change == "swap":
                raw["kernels"][0]["id"] = "SZLHOLDINGS/chaski"
            elif change == "missing":
                raw["kernels"] = raw["kernels"][1:]
            else:
                raw["kernels"] = []
            with self.subTest(change=change), self.assertRaisesRegex(gen.GenerationError, "observed kernels membership differs"):
                gen.build_inventory(raw, T1)

    def test_unavailable_kernel_listing_is_not_an_empty_observation(self) -> None:
        class MissingKernels(gen.FixtureSource):
            def listing(self, kind):
                return None if kind == "kernels" else super().listing(kind)

        with self.assertRaisesRegex(gen.GenerationError, "kernels listing is unavailable"):
            gen.collect(MissingKernels(FIXTURE))

    def test_native_kernel_without_model_mirror_is_inventoried(self) -> None:
        raw = self.native_observation()
        raw["kernels"][0]["id"] = "SZLHOLDINGS/native-only"
        manifest = json.loads(raw["canonical_source"]["manifest_text"])
        manifest["inventory"]["kernels"][0]["id"] = "SZLHOLDINGS/native-only"
        content, blob = self._bind(manifest)
        raw["canonical_source"] = gen.canonical_source(content, "a" * 40, blob)
        inventory = gen.build_inventory(raw, T1)
        self.assertIn("SZLHOLDINGS/native-only", [row["id"] for row in inventory["resources"]["kernels"]])
        self.assertNotIn("SZLHOLDINGS/native-only", [row["id"] for row in inventory["resources"]["models"]])

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
        for malformed in (None, [], {"sha": "a" * 40, "commit": []},
                          {"sha": "a" * 40, "commit": {"verification": "valid"}}):
            with self.subTest(metadata=malformed), mock.patch.object(source, "_get", return_value=malformed):
                with self.assertRaises(gen.GenerationError):
                    source.canonical_source()

    def test_retained_canonical_manifest_preserves_exact_newline_bytes(self) -> None:
        raw = gen.collect(gen.FixtureSource(FIXTURE))
        content = raw["canonical_source"]["manifest_text"].replace("\n", "\r\n").encode("utf-8")
        blob = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
        raw["canonical_source"] = gen.canonical_source(content, "a" * 40, blob)
        self.site.run(T1, raw)
        self.assertEqual((self.site.root / gen.CANONICAL_COPY_PATH).read_bytes(), content)
        _, changed = self.site.run(T2, raw)
        self.assertEqual(changed, [])

    def test_primary_record_and_public_metadata_ambiguity_are_blocking(self) -> None:
        for raw in (b'{"counts":{},"counts":{}}', b'{"private":true,"private":false}',
                    b'{"value":NaN}', b'{"value":1e999}', b'[]junk', b'\xff'):
            with self.subTest(raw=raw), self.assertRaises(gen.GenerationError):
                gen.strict_json(raw)
            source = gen.LiveSource(attempts=1)
            with mock.patch.object(source, "_bytes", return_value=raw):
                with self.assertRaises(gen.GenerationError):
                    source._get("https://huggingface.co/api/spaces/SZLHOLDINGS/README")

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
        self.assertRegex(
            text,
            r"(?m)^concurrency:\n  group: hf-inventory-refresh\n  cancel-in-progress: false$",
        )
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


class AuxiliaryObservationTests(TestCase):
    def setUp(self):
        self.raw = gen.collect(gen.FixtureSource(FIXTURE))

    def build(self, raw=None):
        return gen.build_inventory(self.raw if raw is None else raw, T1)

    def test_valid_public_fixture_retains_counts_and_coverage(self):
        inventory = self.build()
        self.assertEqual(inventory["counts"]["collections"], 1)
        self.assertEqual(inventory["counts"]["buckets"], 1)
        self.assertEqual(inventory["resources"]["collections"][0]["item_count"], 3)
        self.assertEqual(inventory["resources"]["buckets"][0]["visibility"], "PUBLIC")
        self.assertEqual(inventory["resources"]["buckets"][0]["observed_object_count"], 2)
        self.assertEqual(inventory["collection_coverage"]["models"]["covered"], 1)

    def test_empty_public_observations_are_valid(self):
        for kind in ("collections", "buckets"):
            self.raw[kind] = []
        self.raw["collection_detail"] = {}
        self.raw["bucket_tree"] = {}
        inventory = self.build()
        self.assertEqual(inventory["counts"]["collections"], 0)
        self.assertEqual(inventory["counts"]["buckets"], 0)

    def test_unknown_or_private_listing_visibility_blocks_public_counts(self):
        for kind in ("collections", "buckets"):
            for value in (None, True, 0, 1, "false", "true", [], {}):
                raw = copy.deepcopy(self.raw)
                raw[kind][0]["private"] = value
                with self.subTest(kind=kind, value=value), self.assertRaises(gen.GenerationError):
                    self.build(raw)
            raw = copy.deepcopy(self.raw)
            del raw[kind][0]["private"]
            with self.subTest(kind=kind, value="missing"), self.assertRaises(gen.GenerationError):
                self.build(raw)

    def test_duplicate_auxiliary_rows_cannot_inflate_counts(self):
        for kind in ("collections", "buckets"):
            raw = copy.deepcopy(self.raw)
            raw[kind].append(copy.deepcopy(raw[kind][0]))
            with self.subTest(kind=kind), self.assertRaises(gen.GenerationError):
                self.build(raw)

    def test_foreign_missing_or_nonstring_auxiliary_identity_blocks(self):
        for kind, key in (("collections", "slug"), ("buckets", "id")):
            for value in (None, 42, "other/resource", "SZLHOLDINGS/", "SZLHOLDINGS/../other"):
                raw = copy.deepcopy(self.raw)
                raw[kind][0][key] = value
                with self.subTest(kind=kind, value=value), self.assertRaises(gen.GenerationError):
                    self.build(raw)

    def test_malformed_auxiliary_listing_blocks(self):
        for kind in ("collections", "buckets"):
            for value in (None, {}, "unavailable", [None], [[]]):
                raw = copy.deepcopy(self.raw)
                raw[kind] = value
                with self.subTest(kind=kind, value=value), self.assertRaises(gen.GenerationError):
                    self.build(raw)

    def test_collect_rejects_bad_summaries_before_fetching_detail(self):
        for kind in ("collections", "buckets"):
            source = gen.FixtureSource(FIXTURE)
            listing = source.listing

            def bad_listing(requested):
                rows = listing(requested)
                if requested == kind:
                    rows[0]["private"] = None
                return rows

            with self.subTest(kind=kind), mock.patch.object(source, "listing", bad_listing), \
                    mock.patch.object(source, "collection") as collection, \
                    mock.patch.object(source, "bucket_tree") as tree:
                with self.assertRaises(gen.GenerationError):
                    gen.collect(source)
                collection.assert_not_called()
                tree.assert_not_called()

    def test_collection_detail_binds_exact_requested_slug(self):
        slug = self.raw["collections"][0]["slug"]
        for value in (None, [], {}, {"slug": "other/resource", "items": []}):
            raw = copy.deepcopy(self.raw)
            raw["collection_detail"][slug] = value
            with self.subTest(detail=value), self.assertRaises(gen.GenerationError):
                self.build(raw)
        del self.raw["collection_detail"][slug]
        with self.assertRaises(gen.GenerationError):
            self.build()

    def test_conflicting_detail_visibility_blocks(self):
        slug = self.raw["collections"][0]["slug"]
        for value in (True, None, 0, "false"):
            raw = copy.deepcopy(self.raw)
            raw["collection_detail"][slug]["private"] = value
            with self.subTest(value=value), self.assertRaises(gen.GenerationError):
                self.build(raw)
        # The captured detail API omits this field; the public listing binds it.
        self.raw["collection_detail"][slug]["private"] = False
        self.assertEqual(self.build()["counts"]["collections"], 1)

    def test_missing_or_malformed_items_are_not_an_empty_collection(self):
        slug = self.raw["collections"][0]["slug"]
        for value in (None, {}, "unavailable", [None], [{"type": "model"}],
                      [{"id": "SZLHOLDINGS/chaski", "type": []}]):
            raw = copy.deepcopy(self.raw)
            raw["collection_detail"][slug]["items"] = value
            with self.subTest(items=value), self.assertRaises(gen.GenerationError):
                self.build(raw)
        del self.raw["collection_detail"][slug]["items"]
        with self.assertRaises(gen.GenerationError):
            self.build()

    def test_explicit_empty_items_and_nonrepository_collection_items_are_valid(self):
        detail = next(iter(self.raw["collection_detail"].values()))
        detail["items"] = []
        self.assertEqual(self.build()["resources"]["collections"][0]["item_count"], 0)
        detail["items"] = [{"id": "1234.56789", "type": "paper", "position": 0}]
        self.assertEqual(self.build()["resources"]["collections"][0]["item_count"], 1)

    def test_missing_or_malformed_detail_maps_are_blocking(self):
        for key in ("collection_detail", "bucket_tree"):
            for value in (None, [], "unavailable"):
                raw = copy.deepcopy(self.raw)
                raw[key] = value
                with self.subTest(key=key, value=value), self.assertRaises(gen.GenerationError):
                    self.build(raw)

    def test_missing_bucket_tree_is_not_an_observed_empty_bucket(self):
        ident = self.raw["buckets"][0]["id"]
        for value in (None, {}, "unavailable"):
            raw = copy.deepcopy(self.raw)
            raw["bucket_tree"][ident] = value
            with self.subTest(tree=value), self.assertRaises(gen.GenerationError):
                self.build(raw)
        del self.raw["bucket_tree"][ident]
        with self.assertRaises(gen.GenerationError):
            self.build()
        self.raw["bucket_tree"][ident] = []
        self.assertEqual(self.build()["resources"]["buckets"][0]["observed_object_count"], 0)

    def test_malformed_bucket_entries_block_instead_of_reporting_empty(self):
        ident = self.raw["buckets"][0]["id"]
        for entry in (None, [], {}, {"path": "x"}, {"type": None, "path": "x"},
                      {"type": "unknown", "path": "x"}, {"type": [], "path": "x"},
                      {"type": "file", "size": 0},
                      {"type": "directory", "path": ""}):
            raw = copy.deepcopy(self.raw)
            raw["bucket_tree"][ident] = [entry]
            with self.subTest(entry=entry), self.assertRaises(gen.GenerationError):
                self.build(raw)

    def test_bucket_file_size_requires_observed_nonnegative_integer(self):
        ident = self.raw["buckets"][0]["id"]
        for size in (None, True, False, -1, "0", "2048", 1.5, {}, []):
            raw = copy.deepcopy(self.raw)
            raw["bucket_tree"][ident] = [{"path": "file", "type": "file", "size": size}]
            with self.subTest(size=size), self.assertRaises(gen.GenerationError):
                self.build(raw)
        raw = copy.deepcopy(self.raw)
        raw["bucket_tree"][ident] = [{"path": "file", "type": "file"}]
        with self.assertRaises(gen.GenerationError):
            self.build(raw)

    def test_bucket_directories_and_observed_empty_files_remain_valid(self):
        ident = self.raw["buckets"][0]["id"]
        self.raw["bucket_tree"][ident] = [
            {"path": "empty", "type": "file", "size": 0},
            {"path": "logs", "type": "directory"},
        ]
        bucket = self.build()["resources"]["buckets"][0]
        self.assertEqual(bucket["observed_object_count"], 1)
        self.assertEqual(bucket["observed_size_bytes"], 0)

    def test_duplicate_bucket_paths_block_instead_of_inflating_counts(self):
        ident = self.raw["buckets"][0]["id"]
        first = {"path": "same", "type": "file", "size": 7}
        for second in (first, {"path": "same", "type": "directory"}):
            raw = copy.deepcopy(self.raw)
            raw["bucket_tree"][ident] = [first, second]
            with self.subTest(second=second), self.assertRaises(gen.GenerationError):
                self.build(raw)

    def test_repository_membership_drift_still_blocks(self):
        for kind in ("models", "datasets", "spaces"):
            raw = copy.deepcopy(self.raw)
            raw[kind] = raw[kind][1:]
            with self.subTest(kind=kind), self.assertRaisesRegex(gen.GenerationError, "membership differs"):
                self.build(raw)


if __name__ == "__main__":
    main()

