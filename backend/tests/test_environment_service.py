import unittest

from app import create_app
from app.extensions import db
from app.models import Application, ApplicationEnvironment
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
        self.application = Application(
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

    def test_list_creates_default_environments(self):
        items = EnvironmentService().list(self.application)

        self.assertEqual([item.environment_name for item in items], ["dev"])
        self.assertFalse(items[0].approval_required)

    def test_delete_rejects_production_environment(self):
        prod = EnvironmentService().create(self.application, {
            "environment_name": "prod",
            "namespace": "gateway-prod",
        })

        with self.assertRaises(ApiError) as context:
            EnvironmentService().delete(prod)

        self.assertEqual(context.exception.code, "PROTECTED_ENVIRONMENT")

    def test_clone_copies_source_environment_configuration(self):
        source = EnvironmentService().create(self.application, {
            "environment_name": "test",
            "namespace": "gateway-test",
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
