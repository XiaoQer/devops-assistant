import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.runtime_exec_registry import RuntimeExecRegistry
from app.services.runtime_exec_service import RuntimeExecService
from app.utils.errors import ApiError


class FakeClock:
    def __init__(self):
        self.value = 1000.0

    def __call__(self):
        return self.value


class RuntimeExecRegistryTest(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.registry = RuntimeExecRegistry(
            ticket_ttl=60,
            max_per_user=2,
            max_per_target=1,
            clock=self.clock,
        )

    def test_ticket_is_single_use_and_bound_to_actor(self):
        ticket = self.registry.issue(7, (1, 2, "prod", "pod-a", "api"), {"pod": "pod-a"})

        with self.assertRaises(ApiError) as wrong_actor:
            self.registry.consume(ticket, 8)
        self.assertEqual(wrong_actor.exception.code, "EXEC_TICKET_INVALID")

        session = self.registry.consume(ticket, 7)
        self.assertEqual(session.payload["pod"], "pod-a")
        with self.assertRaises(ApiError) as reused:
            self.registry.consume(ticket, 7)
        self.assertEqual(reused.exception.code, "EXEC_TICKET_INVALID")

    def test_ticket_expires_after_sixty_seconds(self):
        ticket = self.registry.issue(7, (1, 2, "prod", "pod-a", "api"), {})
        self.clock.value += 61

        with self.assertRaises(ApiError) as caught:
            self.registry.consume(ticket, 7)

        self.assertEqual(caught.exception.code, "EXEC_TICKET_EXPIRED")

    def test_concurrency_limits_release_when_session_closes(self):
        first = self.registry.issue(7, (1, 2, "prod", "pod-a", "api"), {})
        with self.assertRaises(ApiError) as same_target:
            self.registry.issue(8, (1, 2, "prod", "pod-a", "api"), {})
        self.assertEqual(same_target.exception.code, "EXEC_TARGET_BUSY")

        second = self.registry.issue(7, (1, 2, "prod", "pod-b", "api"), {})
        with self.assertRaises(ApiError) as user_limit:
            self.registry.issue(7, (1, 2, "prod", "pod-c", "api"), {})
        self.assertEqual(user_limit.exception.code, "EXEC_USER_LIMIT")

        self.registry.release(first)
        replacement = self.registry.issue(7, (1, 2, "prod", "pod-c", "api"), {})
        self.assertTrue(replacement)
        self.registry.release(second)
        self.registry.release(replacement)


class RuntimeExecServiceTest(unittest.TestCase):
    def setUp(self):
        self.context = SimpleNamespace(
            project=SimpleNamespace(id=1, members=[SimpleNamespace(email="admin", role="admin", status="active")]),
            application=SimpleNamespace(id=2, name="payments"),
            environment=SimpleNamespace(environment_name="prod", approval_required=True),
            cluster=SimpleNamespace(id=3),
            namespace="payments-prod",
        )
        self.actor = SimpleNamespace(id=7)
        self.actor.username = "admin"
        self.registry = RuntimeExecRegistry()

    def test_reason_is_required(self):
        with self.assertRaises(ApiError) as caught:
            RuntimeExecService(RuntimeExecRegistry()).create(
                self.context, "payments-a", "api", self.actor, " "
            )
        self.assertEqual(caught.exception.code, "EXEC_REASON_REQUIRED")

    def test_non_approval_environment_does_not_require_reason(self):
        self.context.environment.approval_required = False
        with patch("app.services.runtime_exec_service.KubernetesClusterService.client") as client, \
                patch("app.services.runtime_exec_service.RuntimeOperationAudit.start") as start, \
                patch("app.services.runtime_exec_service.db.session.add"), \
                patch("app.services.runtime_exec_service.db.session.commit"):
            client.return_value.list_application_pod_containers.return_value = ["api"]
            result = RuntimeExecService(self.registry).create(
                self.context, "payments-a", "api", self.actor, ""
            )
        self.assertTrue(result["ticket"])
        self.assertEqual(start.call_args.kwargs["reason"], "免审批环境终端操作")

    def test_approval_environment_requires_runtime_permission(self):
        self.context.project.members = [
            SimpleNamespace(email="developer@example.com", role="developer", status="active")
        ]
        self.actor.username = "developer@example.com"
        with self.assertRaises(ApiError) as caught:
            RuntimeExecService(self.registry).create(
                self.context, "payments-a", "api", self.actor, "investigate incident"
            )
        self.assertEqual(caught.exception.code, "EXEC_PERMISSION_REQUIRED")

    @patch("app.services.runtime_exec_service.db.session.commit")
    @patch("app.services.runtime_exec_service.db.session.add")
    @patch("app.services.runtime_exec_service.RuntimeOperationAudit.start")
    @patch("app.services.runtime_exec_service.KubernetesClusterService.client")
    def test_create_validates_container_and_returns_short_lived_session(
        self, client, _start, _add, _commit
    ):
        client.return_value.list_application_pod_containers.return_value = ["api", "sidecar"]
        registry = RuntimeExecRegistry()

        result = RuntimeExecService(registry).create(
            self.context,
            "payments-a",
            "api",
            self.actor,
            "investigate production incident",
        )

        self.assertTrue(result["ticket"])
        self.assertTrue(result["websocket_url"].endswith(result["ticket"]))
        self.assertIn("expires_at", result)
        client.return_value.list_application_pod_containers.assert_called_once_with(
            "payments-a", "payments-prod", "payments"
        )


if __name__ == "__main__":
    unittest.main()
