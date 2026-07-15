import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.services.runtime_operation_service import RuntimeOperationService
from app.utils.errors import ApiError


class RuntimeOperationServiceTest(unittest.TestCase):
    def setUp(self):
        self.context = SimpleNamespace(
            project=SimpleNamespace(id=1),
            application=SimpleNamespace(id=2, name="payments"),
            environment=SimpleNamespace(environment_name="prod"),
            cluster=SimpleNamespace(id=3),
            namespace="payments-prod",
        )
        self.actor = SimpleNamespace(id=4)

    def test_restart_requires_explicit_confirmation(self):
        with self.assertRaises(ApiError) as caught:
            RuntimeOperationService().restart_deployment(
                self.context, "payments", self.actor, False
            )

        self.assertEqual(caught.exception.code, "CONFIRMATION_REQUIRED")

    @patch("app.services.runtime_operation_service.db.session.commit")
    @patch("app.services.runtime_operation_service.db.session.add")
    @patch("app.services.runtime_operation_service.RuntimeOperationAudit.start")
    @patch("app.services.runtime_operation_service.KubernetesClusterService.client")
    def test_restart_uses_resolved_context_and_finishes_audit(
        self, client, start, _add, _commit
    ):
        target = client.return_value
        target.restart_deployment.return_value = {
            "deployment": "payments",
            "namespace": "payments-prod",
        }
        audit = start.return_value

        result = RuntimeOperationService().restart_deployment(
            self.context, "payments", self.actor, True, "recover availability"
        )

        target.restart_deployment.assert_called_once_with(
            "payments", "payments-prod", "payments"
        )
        audit.finish.assert_called_once_with("Succeeded")
        self.assertEqual(result["deployment"], "payments")

    @patch("app.services.runtime_operation_service.db.session.commit")
    @patch("app.services.runtime_operation_service.db.session.add")
    @patch("app.services.runtime_operation_service.RuntimeOperationAudit.start")
    @patch("app.services.runtime_operation_service.KubernetesClusterService.client")
    def test_delete_rejects_pod_not_owned_by_application_and_audits_failure(
        self, client, start, _add, _commit
    ):
        client.return_value.delete_application_pod.side_effect = ApiError(
            "Pod 不属于当前 Application", 404, "POD_NOT_FOUND"
        )
        audit = start.return_value

        with self.assertRaises(ApiError) as caught:
            RuntimeOperationService().delete_pod(
                self.context, "other-pod", self.actor, True, "replace failed pod"
            )

        self.assertEqual(caught.exception.code, "POD_NOT_FOUND")
        audit.finish.assert_called_once_with("Failed", "Pod 不属于当前 Application")

    @patch("app.services.runtime_operation_service.KubernetesClusterService.client")
    def test_manifests_are_read_from_resolved_namespace(self, client):
        client.return_value.get_application_deployment_manifest.return_value = {
            "kind": "Deployment"
        }

        result = RuntimeOperationService().deployment_manifest(
            self.context, "payments"
        )

        self.assertEqual(result["kind"], "Deployment")
        client.return_value.get_application_deployment_manifest.assert_called_once_with(
            "payments", "payments-prod", "payments"
        )


if __name__ == "__main__":
    unittest.main()
