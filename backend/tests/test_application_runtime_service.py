import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app import create_app
from app.extensions import db
from app.models import Application, Project, ReleaseRecord
from app.services.application_runtime_service import ApplicationRuntimeService
from app.services.release_service import ReleaseService


class ApplicationRuntimeServiceTest(unittest.TestCase):
    def setUp(self):
        self.context = SimpleNamespace(
            application=SimpleNamespace(name="payments-api"),
            environment=SimpleNamespace(namespace="payments-prod"),
            cluster=SimpleNamespace(id=7),
        )
        self.target = Mock()

    @patch("app.services.application_runtime_service.KubernetesClusterService.client")
    def test_status_uses_environment_target_client(self, client):
        client.return_value = self.target
        self.target.get_application_status.return_value = {"status": "Healthy"}

        result = ApplicationRuntimeService().status(self.context)

        self.assertEqual(result["status"], "Healthy")
        client.assert_called_once_with(self.context.cluster)
        self.target.get_application_status.assert_called_once_with(
            "payments-api", "payments-prod"
        )

    @patch("app.services.application_runtime_service.KubernetesClusterService.client")
    def test_logs_manifest_and_rollback_use_same_target(self, client):
        client.return_value = self.target
        self.target.get_application_pod_logs.return_value = "pod logs"
        self.target.get_application_pod_manifest.return_value = {"kind": "Pod"}
        self.target.rollback_deployment.return_value = {"image": "ghcr.io/acme/api:v1"}
        service = ApplicationRuntimeService()

        logs = service.pod_logs(self.context, "pod-1", "api", 100)
        manifest = service.pod_manifest(self.context, "pod-1")
        rollback = service.rollback(self.context, "ghcr.io/acme/api:v1")

        self.assertEqual(logs, "pod logs")
        self.assertEqual(manifest, {"kind": "Pod"})
        self.assertEqual(rollback["image"], "ghcr.io/acme/api:v1")
        self.target.get_application_pod_logs.assert_called_once_with(
            "pod-1", "payments-prod", "payments-api", "api", 100
        )
        self.target.get_application_pod_manifest.assert_called_once_with(
            "pod-1", "payments-prod", "payments-api"
        )
        self.target.rollback_deployment.assert_called_once_with(
            "payments-api", "payments-prod", "ghcr.io/acme/api:v1"
        )

    @patch("app.services.application_runtime_service.KubernetesClusterService.client")
    def test_pod_detail_uses_environment_target_and_application_ownership(self, client):
        client.return_value = self.target
        self.target.get_application_pod_detail.return_value = {"name": "pod-1"}

        result = ApplicationRuntimeService().pod_detail(self.context, "pod-1")

        self.assertEqual(result["name"], "pod-1")
        self.target.get_application_pod_detail.assert_called_once_with(
            "pod-1", "payments-prod", "payments-api"
        )

class ReleaseRuntimeIntegrationTest(unittest.TestCase):
    class TestConfig:
        SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        AUTO_CREATE_SCHEMA = True
        SECRET_KEY = "release-runtime-test-secret"
        TEKTON_NAMESPACE = "tekton"
        DEFAULT_IMAGE_REGISTRY = "registry.local"
        TESTING = True

    def setUp(self):
        self.context = create_app(self.TestConfig).app_context()
        self.context.push()
        self.project = Project(key="payments", name="Payments")
        db.session.add(self.project)
        db.session.flush()
        self.application = Application(
            project_id=self.project.id,
            name="payments-api",
            repo_url="https://github.com/acme/payments-api.git",
            branch="main",
            language="java",
            framework="spring-boot",
            build_type="maven",
            namespace="payments-dev",
            image_name="ghcr.io/acme/payments-api",
            image_tag="v2",
            port=8080,
        )
        db.session.add(self.application)
        db.session.flush()
        self.source = ReleaseRecord(
            application_id=self.application.id,
            project_id=self.project.id,
            kubernetes_cluster_id=7,
            release_type="deploy",
            environment="dev",
            git_repo=self.application.repo_url,
            git_branch="main",
            image_name=self.application.image_name,
            image_tag="v1",
            deploy_namespace="payments-dev",
            deploy_status="Succeeded",
            deploy_user="alice",
        )
        db.session.add(self.source)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    @patch("app.services.release_service.ApplicationRuntimeService.rollback")
    @patch("app.services.release_service.DeliveryContextService.resolve")
    def test_rollback_revalidates_context_and_uses_target_runtime(
        self, resolve, runtime_rollback
    ):
        delivery_context = SimpleNamespace(
            cluster=SimpleNamespace(id=9),
            namespace="payments-new-dev",
        )
        resolve.return_value = delivery_context
        runtime_rollback.return_value = {"image": self.source.image}

        result, record = ReleaseService().rollback(
            self.application,
            self.source.id,
            "dev",
            "bob",
        )

        resolve.assert_called_once_with(
            self.project,
            self.application,
            "dev",
        )
        runtime_rollback.assert_called_once_with(
            delivery_context,
            self.source.image,
        )
        self.assertEqual(result["image"], self.source.image)
        self.assertEqual(record.kubernetes_cluster_id, 9)
        self.assertEqual(record.deploy_namespace, "payments-new-dev")


if __name__ == "__main__":
    unittest.main()
