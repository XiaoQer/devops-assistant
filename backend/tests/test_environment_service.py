import unittest

from app import create_app
from app.extensions import db
from app.models import Application, ApplicationEnvironment, KubernetesCluster, Project
from app.services.environment_service import EnvironmentService
from app.utils.errors import ApiError


class TestConfig:
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
    TEKTON_NAMESPACE = "tekton"
    DEFAULT_IMAGE_REGISTRY = "registry.local"
    AUTO_CREATE_SCHEMA = True
    SECRET_KEY = "environment-service-test-secret"
    TESTING = True


class EnvironmentServiceTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.context = self.app.app_context()
        self.context.push()
        project = Project(key="gateway", name="Gateway Project")
        db.session.add(project)
        db.session.flush()
        self.cluster = KubernetesCluster(
            project_id=project.id,
            name="LOCAL-TEST",
            kube_context="local-test",
            is_default=True,
            is_active=True,
        )
        db.session.add(self.cluster)
        db.session.flush()
        self.application = Application(
            project_id=project.id,
            name="gateway",
            repo_url="https://github.com/example/gateway.git",
            branch="main",
            language="java",
            framework="spring-boot",
            build_type="maven",
            namespace="gateway-dev",
            image_name="registry.local/gateway",
            image_tag="latest",
            port=8080,
            status="Running",
        )
        db.session.add(self.application)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    def test_list_keeps_empty_environment_collection(self):
        items = EnvironmentService().list(self.application)

        self.assertEqual(items, [])

    def test_delete_rejects_production_environment(self):
        prod = EnvironmentService().create(self.application, {
            "environment_name": "prod",
            "namespace": "gateway-prod",
            "kubernetes_cluster_id": self.cluster.id,
        })

        with self.assertRaises(ApiError) as context:
            EnvironmentService().delete(prod)

        self.assertEqual(context.exception.code, "PROTECTED_ENVIRONMENT")

    def test_delete_removes_non_production_environment(self):
        dev = EnvironmentService().create(self.application, {
            "environment_name": "dev",
            "namespace": "gateway-dev",
            "kubernetes_cluster_id": self.cluster.id,
        })

        EnvironmentService().delete(dev)

        self.assertIsNone(ApplicationEnvironment.query.get(dev.id))

    def test_create_requires_a_kubernetes_cluster(self):
        with self.assertRaises(ApiError) as context:
            EnvironmentService().create(self.application, {
                "environment_name": "qa",
                "namespace": "gateway-qa",
            })

        self.assertEqual(context.exception.code, "KUBERNETES_CLUSTER_REQUIRED")

    def test_clone_copies_source_environment_configuration(self):
        source = EnvironmentService().create(self.application, {
            "environment_name": "test",
            "namespace": "gateway-test",
            "kubernetes_cluster_id": self.cluster.id,
            "replicas": 2,
            "cpu_limit": "800m",
            "approval_required": False,
        })

        cloned = EnvironmentService().clone(source, "perf")

        self.assertEqual(cloned.environment_name, "perf")
        self.assertEqual(cloned.namespace, "gateway-perf")
        self.assertEqual(cloned.replicas, 2)
        self.assertEqual(cloned.cpu_limit, "800m")


if __name__ == "__main__":
    unittest.main()
