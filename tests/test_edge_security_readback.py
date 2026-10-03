"""Offline contracts for exact-source and edge-security readback."""

from __future__ import annotations

import copy
import http.server
import importlib.util
import json
import pathlib
import sys
import tempfile
import threading
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load_module(name: str):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


edge = load_module("edge_security_readback")
source_witness = load_module("stamp_source_witness")


class SourceWitnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.revision = "a" * 40
        self.template = ROOT / ".well-known" / "szl-source.json"

    def test_stamp_binds_exact_source_without_runtime_claims(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            candidate = pathlib.Path(temporary) / "szl-source.json"
            candidate.write_bytes(self.template.read_bytes())
            stamped = source_witness.stamp(candidate, self.revision)
        self.assertEqual(stamped["source_revision"], self.revision)
        self.assertEqual(stamped["artifact_binding"], "EXACT_SOURCE_REVISION")
        self.assertEqual(stamped["product_runtime_readiness"], "UNAVAILABLE")
        self.assertEqual(stamped["uptime"], "UNAVAILABLE")
        self.assertEqual(stamped["dsse_live"], "UNAVAILABLE")
        self.assertIsNone(stamped["generated_at_utc"])

    def test_stamp_rejects_already_stamped_or_extended_template(self) -> None:
        template = json.loads(self.template.read_text(encoding="utf-8"))
        for mutation, expected in (
            (("source_revision", self.revision), "expected 'UNSTAMPED"),
            (("unexpected", True), "unexpected=unexpected"),
        ):
            with self.subTest(mutation=mutation[0]), tempfile.TemporaryDirectory() as temporary:
                candidate = pathlib.Path(temporary) / "szl-source.json"
                changed = copy.deepcopy(template)
                changed[mutation[0]] = mutation[1]
                candidate.write_text(json.dumps(changed), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, expected):
                    source_witness.stamp(candidate, self.revision)

    def test_duplicate_keys_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            candidate = pathlib.Path(temporary) / "szl-source.json"
            candidate.write_text('{"surface":"one","surface":"two"}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                source_witness.load_witness(candidate)


class EdgeReadbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.revision = "b" * 40

    def test_source_control_requires_exact_protected_verified_main(self) -> None:
        branch = {"protected": True, "commit": {"sha": self.revision}}
        commit = {
            "sha": self.revision,
            "verification": {"verified": True, "reason": "valid"},
        }
        result = edge.validate_source_control(branch, commit, self.revision)
        self.assertEqual(result["status"], "PASS")

        branch["protected"] = False
        result = edge.validate_source_control(branch, commit, self.revision)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("does not report main as protected", " ".join(result["errors"]))

    def test_github_probe_uses_compact_git_commit_endpoint(self) -> None:
        observed_urls: list[str] = []

        def fetcher(url: str, *, token: str | None = None):
            observed_urls.append(url)
            self.assertEqual(token, "fixture-token")
            if url.endswith("/branches/main"):
                return (
                    {"protected": True, "commit": {"sha": self.revision}},
                    {},
                )
            if url.endswith(f"/git/commits/{self.revision}"):
                return (
                    {
                        "sha": self.revision,
                        "verification": {"verified": True, "reason": "valid"},
                    },
                    {},
                )
            if url.endswith("/pages"):
                return (
                    {
                        "build_type": "workflow",
                        "status": "built",
                        "cname": "a11oy.net",
                        "https_enforced": True,
                        "html_url": "https://a11oy.net/",
                        "protected_domain_state": "verified",
                        "https_certificate": {
                            "state": "approved",
                            "domains": ["a11oy.net", "www.a11oy.net"],
                            "expires_at": "2099-01-01",
                        },
                    },
                    {},
                )
            self.fail(f"unexpected GitHub readback URL: {url}")

        source, pages = edge.probe_github(
            edge.SOURCE_REPOSITORY,
            self.revision,
            "fixture-token",
            fetcher=fetcher,
        )
        self.assertEqual(source["status"], "PASS")
        self.assertEqual(pages["status"], "PASS")
        self.assertTrue(
            any(f"/git/commits/{self.revision}" in url for url in observed_urls)
        )
        self.assertFalse(
            any(
                f"/commits/{self.revision}" in url
                and f"/git/commits/{self.revision}" not in url
                for url in observed_urls
            )
        )

    def test_pages_settings_keep_tls_enforcement_separate(self) -> None:
        pages = {
            "build_type": "workflow",
            "status": "built",
            "cname": "a11oy.net",
            "https_enforced": True,
            "html_url": "https://a11oy.net/",
            "protected_domain_state": "verified",
            "https_certificate": {
                "state": "approved",
                "domains": ["a11oy.net", "www.a11oy.net"],
                "expires_at": "2099-01-01",
            },
        }
        self.assertEqual(edge.validate_pages_settings(pages)["status"], "PASS")
        pages["https_enforced"] = False
        pages["html_url"] = "http://a11oy.net/"
        failed = edge.validate_pages_settings(pages)
        self.assertEqual(failed["status"], "FAIL")
        self.assertGreaterEqual(len(failed["errors"]), 2)

    def test_pages_settings_reject_unsafe_origin_certificate_states(self) -> None:
        valid = {
            "build_type": "workflow",
            "status": "built",
            "cname": "a11oy.net",
            "https_enforced": True,
            "html_url": "https://a11oy.net/",
            "protected_domain_state": "verified",
            "https_certificate": {
                "state": "approved",
                "domains": ["a11oy.net", "www.a11oy.net"],
                "expires_at": "2099-01-01",
            },
        }
        mutations = (
            (
                "bad authorization",
                lambda pages: pages["https_certificate"].update(state="bad_authz"),
            ),
            (
                "missing expiry",
                lambda pages: pages["https_certificate"].pop("expires_at"),
            ),
            (
                "malformed expiry",
                lambda pages: pages["https_certificate"].update(expires_at="never"),
            ),
            (
                "wrong domain",
                lambda pages: pages["https_certificate"].update(
                    domains=["example.com"]
                ),
            ),
            (
                "near expiry",
                lambda pages: pages["https_certificate"].update(
                    expires_at="2026-10-04"
                ),
            ),
            (
                "unverified domain",
                lambda pages: pages.update(protected_domain_state="pending"),
            ),
        )
        now = edge.dt.datetime(2026, 10, 3, tzinfo=edge.dt.timezone.utc)
        for label, mutate in mutations:
            with self.subTest(label=label):
                pages = copy.deepcopy(valid)
                mutate(pages)
                self.assertEqual(
                    edge.validate_pages_settings(pages, now=now)["status"],
                    "FAIL",
                )

    def test_final_main_reauthorization_rejects_mid_probe_source_move(self) -> None:
        newer = "c" * 40
        passing = {"status": "PASS", "errors": []}
        with (
            mock.patch.object(
                edge,
                "probe_github",
                return_value=(copy.deepcopy(passing), copy.deepcopy(passing)),
            ),
            mock.patch.object(
                edge, "probe_source_witness", return_value=copy.deepcopy(passing)
            ),
            mock.patch.object(
                edge, "probe_tls", return_value=copy.deepcopy(passing)
            ) as tls_probe,
            mock.patch.object(
                edge, "probe_dnssec", return_value=copy.deepcopy(passing)
            ),
            mock.patch.object(
                edge, "probe_headers", return_value=copy.deepcopy(passing)
            ),
            mock.patch.object(
                edge,
                "probe_current_main",
                return_value={
                    "status": "FAIL",
                    "expected_revision": self.revision,
                    "observed_main_revision": newer,
                    "branch_protected": True,
                    "errors": ["protected main moved during edge readback"],
                },
            ) as reauthorize,
        ):
            receipt = edge.build_receipt(
                self.revision,
                edge.SOURCE_REPOSITORY,
                "fixture-token",
            )

        self.assertEqual(receipt["result"], "FAIL")
        self.assertIn("source_control_reauthorization", receipt["failed_controls"])
        self.assertIn("tls_edge", receipt["probes"])
        self.assertIn("tls_pages_origin", receipt["probes"])
        self.assertEqual(
            tls_probe.call_args_list,
            [
                mock.call(
                    connect_hostname=edge.HOSTNAME,
                    verification_hostname=edge.HOSTNAME,
                ),
                mock.call(
                    connect_hostname=edge.PAGES_ORIGIN_HOSTNAME,
                    verification_hostname=edge.HOSTNAME,
                ),
            ],
        )
        self.assertEqual(
            receipt["probes"]["source_control_reauthorization"][
                "observed_main_revision"
            ],
            newer,
        )
        reauthorize.assert_called_once_with(
            edge.SOURCE_REPOSITORY,
            self.revision,
            "fixture-token",
        )

    def test_dnssec_requires_authenticated_ds_and_dnskey(self) -> None:
        authenticated = {
            "Status": 0,
            "AD": True,
            "Answer": [
                {"name": "a11oy.net.", "type": 43, "data": "12345 13 2 digest"}
            ],
        }
        self.assertEqual(
            edge.validate_dnssec_response(
                authenticated, resolver="fixture", record_type=43
            )["status"],
            "PASS",
        )
        unsigned = {"Status": 0, "AD": False, "Authority": []}
        failed = edge.validate_dnssec_response(
            unsigned, resolver="fixture", record_type=43
        )
        self.assertEqual(failed["status"], "FAIL")
        self.assertFalse(failed["record_present"])

    def test_source_witness_rejects_stale_revision_and_redirect(self) -> None:
        payload = json.loads(
            (ROOT / ".well-known" / "szl-source.json").read_text(encoding="utf-8")
        )
        payload["source_revision"] = self.revision

        def good_fetcher(url: str):
            return payload, {
                "final_url": edge.SOURCE_WITNESS_URL,
                "content_type": "application/json; charset=utf-8",
            }

        self.assertEqual(
            edge.probe_source_witness(self.revision, fetcher=good_fetcher)["status"],
            "PASS",
        )

        def redirected_fetcher(url: str):
            stale = copy.deepcopy(payload)
            stale["source_revision"] = "c" * 40
            return stale, {
                "final_url": "https://example.invalid/szl-source.json",
                "content_type": "application/json",
            }

        failed = edge.probe_source_witness(
            self.revision, fetcher=redirected_fetcher
        )
        self.assertEqual(failed["status"], "FAIL")
        self.assertGreaterEqual(len(failed["errors"]), 2)

    def test_header_contract_does_not_promote_committed_headers_to_live(self) -> None:
        def static_validator():
            return {"x-content-type-options": "nosniff"}, []

        def live_validator(url: str, expected: dict[str, str]):
            return [f"{url}: missing live content-security-policy"]

        result = edge.probe_headers(
            static_validator=static_validator,
            live_validator=live_validator,
        )
        self.assertEqual(result["committed_contract"], "PASS")
        self.assertEqual(result["status"], "FAIL")

    def test_duplicate_readback_json_fails_closed(self) -> None:
        with self.assertRaisesRegex(edge.ProbeError, "duplicate JSON key"):
            edge.decode_json(b'{"AD":true,"AD":false}', source="fixture")

    def test_credentialed_json_redirect_is_not_followed(self) -> None:
        target_requests: list[dict[str, str]] = []

        class TargetHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                target_requests.append(dict(self.headers.items()))
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b"{}")

            def log_message(self, format: str, *args: object) -> None:
                return

        target = http.server.ThreadingHTTPServer(("127.0.0.1", 0), TargetHandler)
        target_thread = threading.Thread(target=target.serve_forever, daemon=True)
        target_thread.start()
        target_url = f"http://127.0.0.1:{target.server_port}/private-target"

        class RedirectHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                self.send_response(302)
                self.send_header("Location", target_url)
                self.end_headers()

            def log_message(self, format: str, *args: object) -> None:
                return

        source = http.server.ThreadingHTTPServer(("127.0.0.1", 0), RedirectHandler)
        source_thread = threading.Thread(target=source.serve_forever, daemon=True)
        source_thread.start()
        source_url = f"http://127.0.0.1:{source.server_port}/source"
        try:
            with self.assertRaisesRegex(edge.ProbeError, "HTTP Error 302"):
                edge.fetch_json(source_url, token="fixture-bearer-secret")
        finally:
            source.shutdown()
            target.shutdown()
            source.server_close()
            target.server_close()
            source_thread.join(timeout=2)
            target_thread.join(timeout=2)

        self.assertEqual(target_requests, [])

    def test_live_header_probe_uses_no_redirect_opener(self) -> None:
        with mock.patch.object(
            edge.check_security_headers,
            "open_no_redirect",
            side_effect=RuntimeError("no-redirect sentinel"),
        ) as opener:
            errors = edge.check_security_headers.validate_live(
                "https://a11oy.net/",
                {},
            )
        opener.assert_called_once()
        self.assertEqual(
            errors,
            ["https://a11oy.net/: live readback failed: no-redirect sentinel"],
        )


class WorkflowContractTests(unittest.TestCase):
    def test_readback_is_automated_bounded_and_read_only(self) -> None:
        workflow = (
            ROOT / ".github" / "workflows" / "edge-security-readback.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("workflow_run:", workflow)
        self.assertIn("schedule:", workflow)
        self.assertIn("github.event.workflow_run.event == 'push'", workflow)
        self.assertIn("github.event.workflow_run.head_branch == 'main'", workflow)
        self.assertIn(
            "github.event.workflow_run.head_repository.full_name == github.repository",
            workflow,
        )
        self.assertIn("pages: read", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("pages: write", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn("scripts/edge_security_readback.py", workflow)
        self.assertIn("if: always()", workflow)
        self.assertRegex(
            workflow,
            r"actions/upload-artifact@[0-9a-f]{40} # v7\.0\.1",
        )


if __name__ == "__main__":
    unittest.main()
