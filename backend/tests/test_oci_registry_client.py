import ssl
import unittest

from urllib3.exceptions import ConnectTimeoutError, NewConnectionError

from app.services.oci_registry_client import OCIRegistryClient


class FakeResponse:
    def __init__(self, status, headers=None, data=b""):
        self.status = status
        self.headers = headers or {}
        self.data = data


class RecordingRequester:
    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def __call__(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def public_resolver(hostname, _port, **_kwargs):
    return [(2, 1, 6, "", ("93.184.216.34", 0))]


class OCIRegistryClientTest(unittest.TestCase):
    def client(self, *outcomes, resolver=public_resolver):
        requester = RecordingRequester(*outcomes)
        return OCIRegistryClient(requester=requester, resolver=resolver), requester

    def test_basic_success(self):
        client, requester = self.client(FakeResponse(200))

        result = client.test("ghcr.io", "octocat", "fake-test-token")

        self.assertTrue(result["connected"])
        self.assertEqual(result["auth_method"], "basic")
        self.assertTrue(result["tls_verified"])
        self.assertEqual(requester.calls[0][1], "https://ghcr.io/v2/")
        self.assertTrue(
            requester.calls[0][2]["headers"]["Authorization"].startswith("Basic ")
        )

    def test_bearer_challenge_exchanges_token_and_retries_v2(self):
        challenge = (
            'Bearer realm="https://auth.example.test/token",'
            'service="registry.example.test",scope="registry:catalog:*"'
        )
        client, requester = self.client(
            FakeResponse(401, {"WWW-Authenticate": challenge}),
            FakeResponse(200, data=b'{"token":"fake-bearer-token"}'),
            FakeResponse(200),
        )

        result = client.test(
            "registry.example.test", "robot", "fake-test-token"
        )

        self.assertTrue(result["connected"])
        self.assertEqual(result["auth_method"], "bearer")
        self.assertEqual(requester.calls[1][1], "https://auth.example.test/token")
        self.assertEqual(
            requester.calls[1][2]["fields"],
            {"service": "registry.example.test", "scope": "registry:catalog:*"},
        )
        self.assertEqual(
            requester.calls[2][2]["headers"]["Authorization"],
            "Bearer fake-bearer-token",
        )

    def test_access_token_is_accepted(self):
        challenge = 'Bearer realm="https://auth.example.test/token"'
        client, _requester = self.client(
            FakeResponse(401, {"www-authenticate": challenge}),
            FakeResponse(200, data=b'{"access_token":"fake-bearer-token"}'),
            FakeResponse(204),
        )

        result = client.test(
            "registry.example.test", "robot", "fake-test-token"
        )

        self.assertTrue(result["connected"])
        self.assertEqual(result["auth_method"], "bearer")

    def test_authentication_failures_are_safe(self):
        cases = [
            FakeResponse(401, {"WWW-Authenticate": 'Basic realm="Registry"'}),
            FakeResponse(401, {"WWW-Authenticate": 'Bearer realm="https://auth.example.test/token"'}),
        ]
        for challenge_response in cases:
            with self.subTest(challenge=challenge_response.headers):
                outcomes = [challenge_response]
                if str(challenge_response.headers).find("Bearer") >= 0:
                    outcomes.append(FakeResponse(401, data=b"denied"))
                client, _requester = self.client(*outcomes)

                result = client.test(
                    "registry.example.test", "robot", "fake-test-token"
                )

                self.assertFalse(result["connected"])
                self.assertEqual(result["failure_reason"], "authentication_failed")
                self.assertNotIn("fake-test-token", result["message"])
                self.assertNotIn("denied", result["message"])

    def test_invalid_challenge_and_token_payload_are_protocol_errors(self):
        cases = [
            [FakeResponse(401)],
            [FakeResponse(401, {"WWW-Authenticate": "Digest value"})],
            [
                FakeResponse(401, {"WWW-Authenticate": 'Bearer realm="https://auth.example.test/token"'}),
                FakeResponse(200, data=b"not-json"),
            ],
            [
                FakeResponse(401, {"WWW-Authenticate": 'Bearer realm="https://auth.example.test/token"'}),
                FakeResponse(200, data=b"{}"),
            ],
        ]
        for outcomes in cases:
            with self.subTest(outcomes=len(outcomes)):
                client, _requester = self.client(*outcomes)

                result = client.test(
                    "registry.example.test", "robot", "fake-test-token"
                )

                self.assertFalse(result["connected"])
                self.assertEqual(result["failure_reason"], "protocol_error")

    def test_tls_timeout_and_network_errors_are_classified(self):
        cases = [
            (ssl.SSLError("certificate failed"), "tls_failed"),
            (ConnectTimeoutError(None, "registry.example.test", "slow"), "timeout"),
            (NewConnectionError(None, "offline"), "unreachable"),
        ]
        for error, reason in cases:
            with self.subTest(reason=reason):
                client, _requester = self.client(error)

                result = client.test(
                    "registry.example.test", "robot", "fake-test-token"
                )

                self.assertFalse(result["connected"])
                self.assertEqual(result["failure_reason"], reason)
                self.assertNotIn(str(error), result["message"])

    def test_skip_tls_verify_is_visible_in_success_result_and_request(self):
        client, requester = self.client(FakeResponse(200))

        result = client.test(
            "harbor.internal.example", "robot", "fake-test-token", True
        )

        self.assertTrue(result["connected"])
        self.assertFalse(result["tls_verified"])
        self.assertTrue(requester.calls[0][2]["skip_tls_verify"])

    def test_unsafe_registry_targets_are_rejected_before_request(self):
        targets = [
            "http://registry.example.test",
            "localhost:5000",
            "127.0.0.1:5000",
            "[::1]:5000",
            "169.254.169.254",
            "0.0.0.0",
            "224.0.0.1",
        ]
        for target in targets:
            with self.subTest(target=target):
                client, requester = self.client(FakeResponse(200))

                result = client.test(target, "robot", "fake-test-token")

                self.assertFalse(result["connected"])
                self.assertEqual(result["failure_reason"], "protocol_error")
                self.assertEqual(requester.calls, [])

    def test_private_registry_target_is_allowed(self):
        client, requester = self.client(FakeResponse(200))

        result = client.test("10.0.0.20:5000", "robot", "fake-test-token")

        self.assertTrue(result["connected"])
        self.assertEqual(requester.calls[0][1], "https://10.0.0.20:5000/v2/")

    def test_unsafe_bearer_realm_does_not_receive_credentials(self):
        challenges = [
            'Bearer realm="http://auth.example.test/token"',
            'Bearer realm="https://127.0.0.1/token"',
        ]
        for challenge in challenges:
            with self.subTest(challenge=challenge):
                client, requester = self.client(
                    FakeResponse(401, {"WWW-Authenticate": challenge})
                )

                result = client.test(
                    "registry.example.test", "robot", "fake-test-token"
                )

                self.assertFalse(result["connected"])
                self.assertEqual(result["failure_reason"], "protocol_error")
                self.assertEqual(len(requester.calls), 1)


if __name__ == "__main__":
    unittest.main()
