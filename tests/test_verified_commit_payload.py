# SPDX-License-Identifier: Apache-2.0
"""Tests for scripts/verified_commit_payload.py (stdlib only, no network)."""

from __future__ import annotations

import base64
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("verified_commit_payload", ROOT / "scripts" / "verified_commit_payload.py")
assert SPEC is not None and SPEC.loader is not None
vcp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(vcp)

BASE = "b" * 40


class VerifiedCommitPayloadTest(unittest.TestCase):
    def test_request_carries_exact_bytes_and_expected_head(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "estate").mkdir()
            (root / "estate" / "hf-current.json").write_bytes(b'{"a": 1}\n')
            (root / "public-inventory.json").write_bytes("{\"t\": \"—\"}\n".encode("utf-8"))
            porcelain = b" M public-inventory.json\0 M estate/hf-current.json\0"
            request = vcp.build_request(root, "szl-holdings/a11oy-net", "bot/x", BASE, "head", "body", porcelain)
        self.assertIn("createCommitOnBranch", request["query"])
        payload = request["variables"]["input"]
        self.assertEqual(payload["expectedHeadOid"], BASE)
        self.assertEqual(payload["branch"], {"repositoryNameWithOwner": "szl-holdings/a11oy-net", "branchName": "bot/x"})
        self.assertEqual(payload["message"], {"headline": "head", "body": "body"})
        additions = payload["fileChanges"]["additions"]
        self.assertEqual([row["path"] for row in additions], ["estate/hf-current.json", "public-inventory.json"])
        self.assertEqual(base64.b64decode(additions[0]["contents"]), b'{"a": 1}\n')
        self.assertEqual(base64.b64decode(additions[1]["contents"]).decode("utf-8"), "{\"t\": \"—\"}\n")
        self.assertEqual(payload["fileChanges"]["deletions"], [])

    def test_untracked_new_file_and_deletion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "new.json").write_bytes(b"{}\n")
            request = vcp.build_request(root, "o/r", "b", BASE, "h", "b", b"?? new.json\0 D gone.json\0")
        changes = request["variables"]["input"]["fileChanges"]
        self.assertEqual([row["path"] for row in changes["additions"]], ["new.json"])
        self.assertEqual(changes["deletions"], [{"path": "gone.json"}])

    def test_refuses_empty_and_rename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                vcp.build_request(Path(tmp), "o/r", "b", BASE, "h", "b", b"")
            with self.assertRaises(ValueError):
                vcp.build_request(Path(tmp), "o/r", "b", BASE, "h", "b", b"R  new.json\0old.json\0")


if __name__ == "__main__":
    unittest.main()
