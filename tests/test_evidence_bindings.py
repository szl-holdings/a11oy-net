#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Regression vectors for historical labels and future content-bound probes."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.check_evidence_bindings import (
    DOCUMENTS,
    ROOT,
    validate_binding,
    validate_documents,
)


PROBE_DIGEST = "sha256:fffe2ea97f6dbbea14bfeefa99302f17a00a99efea132a1a05d2bb511f1e712a"


class EvidenceBindingsTest(unittest.TestCase):
    def test_published_historical_contracts(self) -> None:
        self.assertEqual(validate_documents(ROOT), [])

    def test_exact_bytes_and_atomic_pair(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / "evidence"
            evidence.mkdir()
            witness = evidence / "probe.txt"
            witness.write_bytes(b"probe-v1\n")
            node = {
                "evidence_class": "MEASURED",
                "evidence_uri": "/evidence/probe.txt",
                "evidence_digest": PROBE_DIGEST,
            }
            self.assertEqual(validate_binding(root, node, "fixture"), [])
            self.assertEqual(
                validate_binding(
                    root,
                    {**node, "evidence_uri": "https://a11oy.net/evidence/probe.txt"},
                    "fixture",
                ),
                [],
            )
            witness.write_bytes(b"probe-v1!\n")
            self.assertIn("does not match", " ".join(validate_binding(root, node, "fixture")))
            for omitted in ("evidence_uri", "evidence_digest"):
                missing = {key: value for key, value in node.items() if key != omitted}
                self.assertTrue(validate_binding(root, missing, "fixture"), omitted)
            for invalid in (
                "https://huggingface.co/evidence/probe.txt",
                "//a11oy.net/evidence/probe.txt",
                "/evidence/../probe.txt",
                "/evidence/%2e%2e/probe.txt",
                "/evidence/probe.txt?version=latest",
            ):
                self.assertTrue(
                    validate_binding(root, {**node, "evidence_uri": invalid}, "fixture"),
                    invalid,
                )
            self.assertTrue(
                validate_binding(root, {**node, "evidence_digest": "sha256:bad"}, "fixture")
            )

    def test_nested_labels_and_fail_closed_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in DOCUMENTS:
                shutil.copyfile(ROOT / name, root / name)
            origin_path = root / "origin.json"
            origin = json.loads(origin_path.read_text(encoding="utf-8"))
            origin["hosts"][0]["honesty"] = "MEASURED"
            origin_path.write_text(json.dumps(origin), encoding="utf-8")
            self.assertIn("origin.json.hosts[0]", " ".join(validate_documents(root)))
            origin["hosts"][0]["honesty"] = "SNAPSHOT"
            origin_path.write_text(json.dumps(origin), encoding="utf-8")

            estate_path = root / "estate.json"
            estate = json.loads(estate_path.read_text(encoding="utf-8"))
            estate["findings"][1]["evidence"] = "MEASURED"
            estate_path.write_text(json.dumps(estate), encoding="utf-8")
            self.assertIn("estate.json.findings[1]", " ".join(validate_documents(root)))
            estate["findings"][1]["evidence"] = "SNAPSHOT"
            estate["boundaries"]["spaces_deleted"] = False
            estate["keys"]["private_keys_in_public_git"] = 0
            estate_path.write_text(json.dumps(estate), encoding="utf-8")
            failures = " ".join(validate_documents(root))
            self.assertIn("cannot establish deletion", failures)
            self.assertIn("cannot claim an estate-wide zero", failures)

    def test_human_pages_must_match_machine_snapshot_dates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in DOCUMENTS:
                shutil.copyfile(ROOT / name, root / name)
            (root / "origin").mkdir()
            (root / "estate").mkdir()
            (root / "origin" / "index.html").write_text(
                "Historical probe 2026-09-26T01:10:00Z CLOSED-as-MEASURED",
                encoding="utf-8",
            )
            (root / "estate" / "index.html").write_text(
                "Read machine snapshot", encoding="utf-8"
            )
            failures = " ".join(validate_documents(root))
            self.assertIn("latest machine-record timestamp", failures)
            self.assertIn("unbound closure", failures)
            self.assertIn("machine-link date", failures)


if __name__ == "__main__":
    unittest.main()
