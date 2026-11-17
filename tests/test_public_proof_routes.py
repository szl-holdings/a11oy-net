"""Offline fail-closed contracts for the public proof GET route readback."""

from __future__ import annotations

import http.client
import pathlib
import sys
import unittest
import urllib.error
from urllib.parse import urlsplit


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import edge_security_readback as edge  # noqa: E402


class Response:
    def __init__(
        self, url: str, body: bytes, *,
        status: int = 200, content_type: str = "application/json",
        mitigated: str | None = None, final_url: str | None = None,
    ) -> None:
        self.status = status
        self.url = final_url or url
        self.body = body
        self.headers = {"Content-Type": content_type}
        if mitigated is not None:
            self.headers["cf-mitigated"] = mitigated

    def geturl(self) -> str:
        return self.url

    def read(self, size: int = -1) -> bytes:
        return self.body if size < 0 else self.body[:size]

    def __enter__(self):
        return self

    def __exit__(self, *_args: object) -> bool:
        return False


class PublicProofReadbackTests(unittest.TestCase):
    @staticmethod
    def published_fixture(request, *, timeout: int):
        assert timeout == 12
        assert request.get_method() == "GET"
        assert request.full_url.startswith("https://a11oy.net/")
        assert request.get_header("Authorization") is None
        path = urlsplit(request.full_url).path
        data_path = ROOT / path.lstrip("/")
        if path.endswith("/"):
            data_path = data_path / "index.html"
        content_type = "application/json" if path.endswith(".json") else "text/html"
        return Response(request.full_url, data_path.read_bytes(), content_type=content_type)

    def test_five_exact_public_paths_pass_using_checked_in_fixtures(self) -> None:
        seen = []

        def open_fixture(request, *, timeout):
            seen.append(request.full_url)
            return self.published_fixture(request, timeout=timeout)

        result = edge.probe_public_proof_routes(opener=open_fixture)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["paths_checked"], 5)
        self.assertEqual(result["errors"], [])
        self.assertEqual(
            seen, [edge.SURFACE + path for path, _, _ in edge.PUBLIC_PROOF_ROUTES]
        )
        self.assertTrue(all(row["http_status"] == 200 for row in result["results"]))

    def test_managed_challenge_refuses_without_echoing_private_headers(self) -> None:
        secret = "fixture-secret-not-for-receipt"

        def challenge(request, *, timeout):
            headers = http.client.HTTPMessage()
            headers["cf-mitigated"] = "challenge"
            headers["Authorization"] = secret
            raise urllib.error.HTTPError(request.full_url, 403, "Forbidden", headers, None)

        result = edge.probe_public_proof_routes(opener=challenge)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(len(result["errors"]), 5)
        self.assertEqual(result["results"][0]["code"], "EDGE_MANAGED_CHALLENGE")
        self.assertNotIn(secret, str(result))

    def test_x402_paywall_is_not_a_successful_public_proof_read(self) -> None:
        def paywall(request, *, timeout):
            headers = http.client.HTTPMessage()
            headers["PAYMENT-REQUIRED"] = "fixture-private-quote"
            raise urllib.error.HTTPError(request.full_url, 402, "Payment Required", headers, None)

        result = edge.probe_public_proof_routes(opener=paywall)
        self.assertEqual(result["results"][0]["code"], "EDGE_PAYMENT_CHALLENGE")
        self.assertNotIn("fixture-private-quote", str(result))

    def test_redirect_and_other_refusals_fail_without_following(self) -> None:
        def redirect(request, *, timeout):
            raise urllib.error.HTTPError(
                request.full_url, 302, "Found", http.client.HTTPMessage(), None
            )

        self.assertEqual(
            edge.probe_public_proof_routes(opener=redirect)["results"][0]["code"],
            "HTTP_302",
        )

        def wrong_origin(request, *, timeout):
            response = self.published_fixture(request, timeout=timeout)
            response.url = "https://other.example/record.json"
            return response

        self.assertEqual(
            edge.probe_public_proof_routes(opener=wrong_origin)["results"][0]["code"],
            "REDIRECT_OR_ORIGIN_DRIFT",
        )

    def test_success_status_requires_matching_media_type_and_payload(self) -> None:
        def wrong_media(request, *, timeout):
            return Response(request.full_url, b"<html></html>", content_type="text/html")

        self.assertEqual(
            edge.probe_public_proof_routes(opener=wrong_media)["results"][0]["code"],
            "WRONG_CONTENT_TYPE",
        )

        def broken_json(request, *, timeout):
            return Response(request.full_url, b'{"contract_version":"1","contract_version":"2"}')

        self.assertEqual(
            edge.probe_public_proof_routes(opener=broken_json)["results"][0]["code"],
            "INVALID_PUBLIC_DOCUMENT",
        )

        def challenge_as_200(request, *, timeout):
            return Response(
                request.full_url, b"{}",
                mitigated="challenge",
            )

        self.assertEqual(
            edge.probe_public_proof_routes(opener=challenge_as_200)["results"][0]["code"],
            "EDGE_MANAGED_CHALLENGE",
        )

    def test_oversized_empty_and_bad_html_are_refused(self) -> None:
        def huge(request, *, timeout):
            return Response(request.full_url, b"x" * (edge.MAX_PUBLIC_PROOF_BYTES + 1))

        self.assertEqual(
            edge.probe_public_proof_routes(opener=huge)["results"][0]["code"],
            "EMPTY_OR_OVERSIZED_BODY",
        )

        def empty(request, *, timeout):
            return Response(request.full_url, b"")

        self.assertEqual(
            edge.probe_public_proof_routes(opener=empty)["results"][0]["code"],
            "EMPTY_OR_OVERSIZED_BODY",
        )

        def bad_html(request, *, timeout):
            response = self.published_fixture(request, timeout=timeout)
            if request.full_url.endswith("/record/"):
                response.body = b"<html><title>Other site</title></html>"
            return response

        self.assertEqual(
            edge.probe_public_proof_routes(opener=bad_html)["results"][3]["code"],
            "MISSING_PUBLIC_HTML_MARKER",
        )

    def test_network_unavailable_preserves_fail_closed_result(self) -> None:
        def absent(request, *, timeout):
            raise OSError("secret bearer value should not be echoed")

        result = edge.probe_public_proof_routes(opener=absent)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(all(r["code"] == "TRANSPORT_UNAVAILABLE" for r in result["results"]))
        self.assertNotIn("bearer", str(result))


if __name__ == "__main__":
    unittest.main()
