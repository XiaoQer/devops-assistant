import unittest

from app import create_app
from app.extensions import db
from app.models import (
    Application,
    ApplicationEnvironment,
    ContainerRegistry,
    KubernetesCluster,
    Project,
)
from app.services.delivery_context_service import DeliveryContextService
from app.utils.errors import ApiError


class TestConfig:
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    AUTO_CREATE_SCHEMA = True
    SECRET_KEY = "delivery-context-test-secret"
    TEKTON_NAMESPACE = "tekton"
    DEFAULT_IMAGE_REGISTRY = "registry.local"
    TESTING = True


class DeliveryContextServiceTest(unittest.TestCase):
    def setUp(self):
        self.app_context = create_app(TestConfig).app_context()
        self.app_context.push()
        self.project = Project(key="payments", name="Payments")
        self.other_project = Project(key="platform", name="Platform")
        db.session.add_all([self.project, self.other_project])
        db.session.flush()
        self.application = Application(
            project_id=self.project.id,
            name="payments-api",
            repo_url="https://github.com/acme/payments-api.git",
            branch="main",
            language="java",
            framework="spring-boot",
            build_type="maven",
            namespace="payments",
            image_name="legacy.local/payments-api",
            image_tag="latest",
            port=8080,
        )
        db.session.add(self.application)
        db.session.flush()
        self.cluster = KubernetesCluster(
            project_id=self.project.id,
            name="payments-prod",
            kube_context="prod-context",
            environment_label="production",
            encrypted_kubeconfig="ciphertext",
            connection_status="connected",
            is_active=True,
            is_default=True,
        )
        db.session.add(self.cluster)
        db.session.flush()
        self.environment = ApplicationEnvironment(
            application_id=self.application.id,
            kubernetes_cluster_id=self.cluster.id,
            environment_name="prod",
            namespace="payments-prod",
        )
        self.registry = ContainerRegistry(
            project_id=self.project.id,
            name="Payments GHCR",
            provider="ghcr",
            server="ghcr.io",
            namespace="acme",
            username="robot",
            encrypted_password="ciphertext",
            connection_status="connected",
            is_default=True,
            is_active=True,
        )
        db.session.add_all([self.environment, self.registry])
        db.session.commit()
        self.service = DeliveryContextService()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.app_context.pop()

    def assert_error(self, code):
        with self.assertRaises(ApiError) as raised:
            self.service.resolve(self.project, self.application, "prod")
        self.assertEqual(raised.exception.code, code)

    def test_resolves_connected_project_delivery_context(self):
        context = self.service.resolve(self.project, self.application, "prod")

        self.assertEqual(context.project.id, self.project.id)
        self.assertEqual(context.application.id, self.application.id)
        self.assertEqual(context.environment.id, self.environment.id)
        self.assertEqual(context.cluster.id, self.cluster.id)
        self.assertEqual(context.registry.id, self.registry.id)
        self.assertEqual(context.namespace, "payments-prod")
        self.assertEqual(context.kube_context, "prod-context")
        self.assertEqual(context.image_name, "ghcr.io/acme/payments-api")

    def test_rejects_missing_environment(self):
        self.environment.environment_name = "dev"
        db.session.commit()

        self.assert_error("ENVIRONMENT_NOT_FOUND")

    def test_rejects_unbound_environment_cluster(self):
        self.environment.kubernetes_cluster_id = None
        db.session.commit()

        self.assert_error("CLUSTER_REQUIRED")

    def test_rejects_cluster_outside_project(self):
        other_cluster = KubernetesCluster(
            project_id=self.other_project.id,
            name="platform-prod",
            kube_context="platform",
            environment_label="production",
            encrypted_kubeconfig="ciphertext",
            connection_status="connected",
        )
        db.session.add(other_cluster)
        db.session.flush()
        self.environment.kubernetes_cluster_id = other_cluster.id
        db.session.commit()

        self.assert_error("CLUSTER_NOT_READY")

    def test_rejects_inactive_or_unconnected_cluster(self):
        for active, status in ((False, "connected"), (True, "untested"), (True, "failed")):
            with self.subTest(active=active, status=status):
                self.cluster.is_active = active
                self.cluster.connection_status = status
                db.session.commit()
                self.assert_error("CLUSTER_NOT_READY")

    def test_rejects_missing_default_registry(self):
        db.session.delete(self.registry)
        db.session.commit()

        self.assert_error("REGISTRY_REQUIRED")

    def test_rejects_inactive_or_unconnected_registry(self):
        for active, status in ((False, "connected"), (True, "untested"), (True, "failed")):
            with self.subTest(active=active, status=status):
                self.registry.is_active = active
                self.registry.connection_status = status
                db.session.commit()
                self.assert_error("REGISTRY_NOT_READY")


if __name__ == "__main__":
    unittest.main()
