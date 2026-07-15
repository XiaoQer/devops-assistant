import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.services.runtime_exec_socket import RuntimeExecSocketBridge
from app.utils.errors import ApiError


class FakeWebSocket:
    def __init__(self, messages):
        self.messages = list(messages)
        self.sent = []

    def receive(self, timeout=None):
        return self.messages.pop(0) if self.messages else None

    def send(self, payload):
        self.sent.append(json.loads(payload))


class TimeoutThenMessageWebSocket(FakeWebSocket):
    connected = True

    def receive(self, timeout=None):
        if self.messages and self.messages[0] is None:
            self.messages.pop(0)
            return None
        return super().receive(timeout)


class FakeStream:
    def __init__(self):
        self.stdin = []
        self.resize = []
        self.closed = False
        self.stdout = ["hello\n"]
        self.stderr = ["warning\n"]

    def is_open(self):
        return not self.closed

    def update(self, timeout=0):
        return None

    def peek_stdout(self):
        return bool(self.stdout)

    def read_stdout(self):
        return self.stdout.pop(0)

    def peek_stderr(self):
        return bool(self.stderr)

    def read_stderr(self):
        return self.stderr.pop(0)

    def write_stdin(self, value):
        self.stdin.append(value)

    def write_channel(self, channel, value):
        self.resize.append((channel, value))

    def close(self):
        self.closed = True


class RuntimeExecSocketBridgeTest(unittest.TestCase):
    def setUp(self):
        self.registry = Mock()
        self.audit = Mock()
        self.context = SimpleNamespace(
            cluster=SimpleNamespace(id=3),
            namespace="payments-prod",
            application=SimpleNamespace(name="payments"),
        )
        self.ticket = SimpleNamespace(
            payload={
                "context": self.context,
                "pod": "payments-a",
                "container": "api",
                "audit": self.audit,
            }
        )
        self.registry.consume.return_value = self.ticket

    def test_rejects_untrusted_origin_before_consuming_ticket(self):
        bridge = RuntimeExecSocketBridge(self.registry)

        with self.assertRaises(ApiError) as caught:
            bridge.run(
                FakeWebSocket([]),
                "ticket",
                SimpleNamespace(id=7),
                "https://evil.example",
                ["http://localhost:5173"],
            )

        self.assertEqual(caught.exception.code, "EXEC_ORIGIN_REJECTED")
        self.registry.consume.assert_not_called()
        self.registry.release.assert_called_once_with("ticket")

    @patch("app.services.runtime_exec_socket.db.session.commit")
    @patch("app.services.runtime_exec_socket.KubernetesClusterService.client")
    def test_forwards_terminal_frames_and_finishes_audit(self, client, _commit):
        stream = FakeStream()
        client.return_value.open_application_pod_exec.return_value = stream
        websocket = FakeWebSocket([
            json.dumps({"type": "stdin", "data": "pwd\n"}),
            json.dumps({"type": "resize", "cols": 120, "rows": 40}),
            json.dumps({"type": "close"}),
        ])

        RuntimeExecSocketBridge(self.registry).run(
            websocket,
            "ticket",
            SimpleNamespace(id=7),
            "http://localhost:5173",
            ["http://localhost:5173"],
        )

        self.assertEqual(stream.stdin, ["pwd\n"])
        self.assertEqual(stream.resize[0][0], 4)
        self.assertIn("stdout", [item["type"] for item in websocket.sent])
        self.assertIn("stderr", [item["type"] for item in websocket.sent])
        self.audit.finish.assert_called_once_with("Succeeded")
        self.registry.release.assert_called_once_with("ticket")
        stream.close()

    @patch("app.services.runtime_exec_socket.db.session.commit")
    @patch("app.services.runtime_exec_socket.KubernetesClusterService.client")
    def test_receive_timeout_does_not_close_session(self, client, _commit):
        stream = FakeStream()
        client.return_value.open_application_pod_exec.return_value = stream
        websocket = TimeoutThenMessageWebSocket([
            None,
            json.dumps({"type": "stdin", "data": "pwd\n"}),
            json.dumps({"type": "close"}),
        ])

        RuntimeExecSocketBridge(self.registry).run(
            websocket,
            "ticket",
            SimpleNamespace(id=7),
            "http://localhost:5173",
            ["http://localhost:5173"],
        )

        self.assertEqual(stream.stdin, ["pwd\n"])
        self.audit.finish.assert_called_once_with("Succeeded")


if __name__ == "__main__":
    unittest.main()
