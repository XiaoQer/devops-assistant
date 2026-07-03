import unittest

from app import create_app
from app.extensions import db
from app.models import Application
from app.services.ai_assistant_service import AiAssistantService


class TestConfig:
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
    TEKTON_NAMESPACE = "tekton"
    DEFAULT_IMAGE_REGISTRY = "registry.local"
    AUTO_CREATE_SCHEMA = True
    SECRET_KEY = "ai-test-secret"
    TESTING = True


class AiAssistantServiceTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.context = self.app.app_context()
        self.context.push()
        application = Application(
            name="payment-service",
            repo_url="https://github.com/example/payment-service.git",
            branch="main",
            language="java",
            framework="spring-boot",
            build_type="maven",
            namespace="default",
            image_name="registry.local/payment-service",
            image_tag="latest",
            port=8080,
            status="Running",
        )
        db.session.add(application)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    def test_resolves_deploy_application_intent(self):
        result = AiAssistantService().analyze_user_intent("Deploy payment-service to production")

        self.assertEqual(result["intent"], "deploy_application")
        self.assertEqual(result["matched_environment"], "prod")
        self.assertEqual(result["target"]["application_name"], "payment-service")
        self.assertTrue(result["requires_confirmation"])

    def test_resolves_open_application_intent(self):
        result = AiAssistantService().analyze_user_intent("打开 payment-service")

        self.assertEqual(result["intent"], "open_application")
        self.assertEqual(result["recommended_action"]["route"], "/applications/1")


if __name__ == "__main__":
    unittest.main()

