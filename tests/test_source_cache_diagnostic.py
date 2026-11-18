# SPDX-License-Identifier: Apache-2.0
"""Offline cache-diagnostic regression controls; absolutely no provider calls."""
from __future__ import annotations

import copy
import datetime as dt
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest
import unittest.mock as mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

spec = importlib.util.spec_from_file_location(
    "probe_source_cache_boundary", SCRIPTS / "probe_source_cache_boundary.py")
assert spec and spec.loader
diagnostic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostic)


class CacheBoundaryTests(unittest.TestCase):
    EXPECTED = "a" * 40
    STALE = "b" * 40

    @classmethod
    def setUpClass(cls):
        cls.template = json.loads(
            (ROOT / ".well-known" / "szl-source.json").read_text(encoding="utf-8")
        )
        assert cls.template["source_revision"].startswith("UNSTAMPED")

    @classmethod
    def witness(cls, revision):
        value = copy.deepcopy(cls.template)
        value["source_revision"] = revision
        return json.dumps(value).encode("utf-8")

    def result(self, revision):
        return {"state": "VALID", "source_revision": revision, "sha256": "0" * 64}

    def time(self):
        return dt.datetime(2026, 11, 18, 0, 10, 0, tzinfo=dt.timezone.utc)

    def test_full_witness_contract_round_trip(self):
        self.assertEqual(
            diagnostic.decode_witness(self.witness(self.EXPECTED)), self.EXPECTED
        )

    def test_reject_duplicate_keys(self):
        raw = self.witness(self.EXPECTED).decode("utf-8")
        raw = raw.replace('"surface":', '"surface": "incorrect", "surface":', 1)
        with self.assertRaisesRegex(diagnostic.ProbeFailure, "DUPLICATE"):
            diagnostic.decode_witness(raw.encode())

    def test_reject_unknown_or_incomplete_contract(self):
        bad = copy.deepcopy(self.template)
        bad["source_revision"] = self.EXPECTED
        bad["product_runtime_readiness"] = "READY"
        with self.assertRaisesRegex(diagnostic.ProbeFailure, "CONTRACT"):
            diagnostic.decode_witness(json.dumps(bad).encode())

    def test_reject_oversize_and_invalid_utf8(self):
        with self.assertRaisesRegex(diagnostic.ProbeFailure, "SIZE_CAP"):
            diagnostic.decode_witness(b"x" * (diagnostic.MAX_JSON + 1))
        with self.assertRaisesRegex(diagnostic.ProbeFailure, "INVALID_SOURCE_JSON"):
            diagnostic.decode_witness(b"\xff")

    def test_reject_dynamic_hosts_or_local_network(self):
        with self.assertRaisesRegex(diagnostic.ProbeFailure, "UNAPPROVED_PUBLIC_URL"):
            diagnostic.fetch_public("https://127.0.0.1/.well-known/szl-source.json")
        with self.assertRaisesRegex(diagnostic.ProbeFailure, "UNAPPROVED_ORIGIN_IP"):
            diagnostic.fetch_origin("127.0.0.1")
        with self.assertRaisesRegex(diagnostic.ProbeFailure, "UNAPPROVED_ORIGIN_IP"):
            diagnostic.fetch_origin("::1")

    def test_expected_revision_must_be_exact_lowercase_sha(self):
        for value in ("main", "ABC" * 13 + "A", "0" * 41, "", "0" * 39, "../"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                diagnostic.observe(value, now=self.time)

    def test_canonical_matching_not_runtime_authority(self):
        record = diagnostic.observe(
            self.EXPECTED,
            public=lambda url: self.result(self.EXPECTED),
            origin=lambda ip: self.result(self.EXPECTED),
            now=self.time,
        )
        self.assertEqual(
            record["diagnosis"], "CANONICAL_AND_ORIGIN_MATCH_NOT_PRODUCTION_QUALIFICATION"
        )
        self.assertIs(record["production_authorized"], False)
        self.assertEqual(record["canonical_release_gate"], "NOT_ASSESSED_BY_THIS_DIAGNOSTIC")
        self.assertEqual(len(record["direct_pages_origins"]), 4)

    def test_canonical_good_origin_unobserved_is_not_qualified(self):
        record = diagnostic.observe(
            self.EXPECTED,
            public=lambda url: self.result(self.EXPECTED),
            origin=lambda ip: {"state": "UNOBSERVED", "reason": "TRANSPORT"},
            now=self.time,
        )
        self.assertEqual(record["diagnosis"],
                         "CANONICAL_MATCH_ORIGIN_UNVERIFIED_NOT_RELEASE_QUALIFIED")
        self.assertFalse(record["current_protected_main_independently_verified"])

    def test_canonical_good_but_origin_drift_is_blocked(self):
        record = diagnostic.observe(
            self.EXPECTED,
            public=lambda url: self.result(self.EXPECTED),
            origin=lambda ip: self.result(self.STALE),
            now=self.time,
        )
        self.assertEqual(record["diagnosis"], "ORIGIN_SOURCE_MISMATCH_RELEASE_BLOCKED")

    def test_stale_cdn_with_all_exact_origins(self):
        calls = []
        def public(url):
            calls.append(("public", url))
            return self.result(self.STALE if url == diagnostic.CANONICAL_URL
                               else self.EXPECTED)
        def origin(ip):
            calls.append(("origin", ip))
            return self.result(self.EXPECTED)
        r = diagnostic.observe(self.EXPECTED, public=public, origin=origin, now=self.time)
        self.assertEqual(r["diagnosis"], "CDN_STALE_SOURCE_CONFIRMED_RELEASE_BLOCKED")
        self.assertEqual(len(calls), 6)
        self.assertEqual(calls[0][1], diagnostic.CANONICAL_URL)
        self.assertTrue(calls[1][1].startswith(diagnostic.CANONICAL_URL + "?szl_probe="))
        self.assertEqual([x[1] for x in calls[2:]], list(diagnostic.PAGES_IPV4))
        self.assertFalse(r["provider_mutations"])

    def test_older_origin_never_gets_cache_clearance(self):
        record = diagnostic.observe(
            self.EXPECTED,
            public=lambda url: self.result(self.STALE if url == diagnostic.CANONICAL_URL
                                           else self.EXPECTED),
            origin=lambda ip: self.result(self.STALE if ip == diagnostic.PAGES_IPV4[-1]
                                          else self.EXPECTED),
            now=self.time,
        )
        self.assertEqual(record["diagnosis"], "ORIGIN_SOURCE_MISMATCH_RELEASE_BLOCKED")

    def test_unavailable_origin_is_not_proven_stale_cache(self):
        record = diagnostic.observe(
            self.EXPECTED,
            public=lambda url: self.result(self.STALE if url == diagnostic.CANONICAL_URL
                                           else self.EXPECTED),
            origin=lambda ip: {"state": "UNOBSERVED", "reason": "TRANSPORT"},
            now=self.time,
        )
        self.assertEqual(record["diagnosis"],
                         "CACHE_VARIANT_DISAGREEMENT_ORIGIN_UNVERIFIED_RELEASE_BLOCKED")

    def test_403_on_canonical_stops_without_alternate_route(self):
        attempts = []
        def denied(url):
            attempts.append(url)
            raise diagnostic.AuthorizationStop("AUTH_OR_RATE_DENIED_403")
        record = diagnostic.observe(
            self.EXPECTED, public=denied,
            origin=lambda ip: self.fail("Origin must not be attempted after 403"),
            now=self.time,
        )
        self.assertEqual(record["diagnosis"], "AUTH_OR_RATE_DENIED_STOP")
        self.assertEqual(attempts, [diagnostic.CANONICAL_URL])
        self.assertNotIn("direct_pages_origins", record)

    def test_429_on_variant_stops_before_origin(self):
        attempts = []
        def fetch(url):
            attempts.append(url)
            if "?" in url:
                raise diagnostic.AuthorizationStop("AUTH_OR_RATE_DENIED_429")
            return self.result(self.EXPECTED)
        record = diagnostic.observe(
            self.EXPECTED, public=fetch,
            origin=lambda ip: self.fail("Origin after rate limit"),
            now=self.time,
        )
        self.assertEqual(record["diagnosis"], "AUTH_OR_RATE_DENIED_STOP")
        self.assertEqual(len(attempts), 2)

    def test_direct_origin_uses_exact_tls_sni_and_allowlisted_host(self):
        connection = mock.MagicMock()
        connection.__enter__.return_value = connection
        wrapped = mock.MagicMock()
        wrapped.__enter__.return_value = wrapped
        context = mock.MagicMock()
        context.wrap_socket.return_value = wrapped
        response = mock.MagicMock()
        response.status = 200
        response.headers = {"Content-Type": "application/json"}
        response.read.return_value = self.witness(self.EXPECTED)
        with mock.patch.object(diagnostic.socket, "create_connection",
                               return_value=connection) as connect, \
                mock.patch.object(diagnostic.ssl, "create_default_context",
                                  return_value=context), \
                mock.patch.object(diagnostic.http.client, "HTTPResponse",
                                  return_value=response):
            result = diagnostic.fetch_origin(diagnostic.PAGES_IPV4[0])
        self.assertEqual(result["source_revision"], self.EXPECTED)
        connect.assert_called_once_with((diagnostic.PAGES_IPV4[0], 443),
                                        timeout=diagnostic.TIMEOUT)
        self.assertEqual(context.minimum_version,
                         diagnostic.ssl.TLSVersion.TLSv1_2)
        context.wrap_socket.assert_called_once_with(
            connection, server_hostname=diagnostic.HOST)
        request = wrapped.sendall.call_args.args[0]
        self.assertIn(b"GET /.well-known/szl-source.json HTTP/1.1", request)
        self.assertIn(b"Host: a11oy.net\r\n", request)
        self.assertNotIn(b"Authorization", request)

    def test_401_on_origin_stops_remaining_origin_attempts(self):
        attempts = []
        def origin(ip):
            attempts.append(ip)
            raise diagnostic.AuthorizationStop("AUTH_OR_RATE_DENIED_401")
        record = diagnostic.observe(
            self.EXPECTED, public=lambda url: self.result(self.STALE),
            origin=origin, now=self.time,
        )
        self.assertEqual(record["diagnosis"], "AUTH_OR_RATE_DENIED_STOP")
        self.assertEqual(attempts, [diagnostic.PAGES_IPV4[0]])

    def test_http_error_and_wrong_type_are_unobserved(self):
        with self.assertRaisesRegex(diagnostic.ProbeFailure, "HTTP_404"):
            diagnostic._received(404, {}, b"")
        with self.assertRaisesRegex(diagnostic.ProbeFailure, "CONTENT_TYPE"):
            diagnostic._received(200, {"Content-Type": "text/html"}, b"{}")

    def test_headers_are_allowlisted_no_bearer_echo(self):
        row = diagnostic._received(
            200, {"Content-Type": "application/json",
                  "CF-Cache-Status": "HIT", "Authorization": "Bearer do-not-echo"},
            self.witness(self.EXPECTED),
        )
        self.assertNotIn("authorization", row["headers"])
        self.assertNotIn("do-not-echo", json.dumps(row))
        self.assertEqual(row["headers"]["cf_cache_status"], "HIT")

    def test_cli_writes_new_private_diagnostic_without_promoting_releases(self):
        for diagnosis, expected_exit in (
            ("CDN_STALE_SOURCE_CONFIRMED_RELEASE_BLOCKED", 1),
            ("CANONICAL_AND_ORIGIN_MATCH_NOT_PRODUCTION_QUALIFICATION", 0),
        ):
            with self.subTest(diagnosis=diagnosis), tempfile.TemporaryDirectory() as temp:
                path = pathlib.Path(temp) / "receipt.json"
                payload = {"schema": diagnostic.SCHEMA,
                           "diagnosis": diagnosis,
                           "provider_mutations": False,
                           "production_authorized": False}
                with mock.patch.object(diagnostic, "observe", return_value=payload), \
                        mock.patch.object(sys, "argv", [
                            "probe_source_cache_boundary.py", "--expected-revision",
                            self.EXPECTED, "--output", str(path),
                        ]):
                    self.assertEqual(diagnostic.main(), expected_exit)
                observed = json.loads(path.read_text(encoding="utf-8"))
                self.assertFalse(observed["production_authorized"])
                self.assertEqual(observed["diagnosis"], diagnosis)

    def test_no_overwrite_existing_append_only_output(self):
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / "receipt.json"
            path.write_text("prior", encoding="utf-8")
            with mock.patch.object(diagnostic, "observe", return_value={
                "diagnosis": "CDN_STALE_SOURCE_CONFIRMED_RELEASE_BLOCKED",
            }), mock.patch.object(sys, "argv", [
                "probe_source_cache_boundary.py", "--expected-revision",
                self.EXPECTED, "--output", str(path),
            ]):
                self.assertEqual(diagnostic.main(), 2)
            self.assertEqual(path.read_text(encoding="utf-8"), "prior")


if __name__ == "__main__":
    unittest.main()
