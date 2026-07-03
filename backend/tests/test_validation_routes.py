import unittest

from app import create_app
from app.extensions import db
from app.models import Application


class TestConfig:
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
    TEKTON_NAMESPACE = "tekton"
    DEFAULT_IMAGE_REGISTRY = "registry.local"
    AUTO_CREATE_SCHEMA = True
    SECRET_KEY = "route-validation-test-secret"
    TESTING = True


class RouteValidationTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.context = self.app.app_context()
        self.context.push()
        self.client = self.app.test_client()
        db.session.add(Application(
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
        ))
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    def test_ai_intent_route_requires_non_empty_text(self):
        response = self.client.post("/api/ai/intent/resolve", json={"text": "   "})

        self.assertEqual(response.status_code, 400)
        body = response.get_json()
        self.assertFalse(body["success"])
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(body["error"]["details"]["field"], "text")

    def test_ai_intent_route_rejects_non_object_payload(self):
        response = self.client.post("/api/ai/intent/resolve", json=["open payment-service"])

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "INVALID_REQUEST_BODY")

    def test_ai_intent_route_still_resolves_known_application(self):
        response = self.client.post("/api/ai/intent/resolve", json={"text": "打开 payment-service"})

        self.assertEqual(response.status_code, 200)
        data = response.get_json()["data"]
        self.assertEqual(data["intent"], "open_application")
        self.assertEqual(data["target"]["application_name"], "payment-service")

    def test_create_application_requires_name_and_repo_url(self):
        response = self.client.post("/api/applications", json={})

        self.assertEqual(response.status_code, 400)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(body["error"]["details"]["fields"], ["name", "repo_url"])

    def test_submit_approval_requires_application_id(self):
        response = self.client.post("/api/approvals", json={})

        self.assertEqual(response.status_code, 400)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(body["error"]["details"]["field"], "application_id")

    def test_compare_environments_requires_query_params(self):
        response = self.client.get("/api/applications/1/environments/compare")

        self.assertEqual(response.status_code, 400)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(body["error"]["details"]["field"], "left")

    def test_create_registry_requires_name_and_server(self):
        response = self.client.post("/api/registries", json={})

        self.assertEqual(response.status_code, 400)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(body["error"]["details"]["fields"], ["name", "server"])

    def test_deploy_plan_requires_explicit_environment(self):
        response = self.client.post("/api/applications/1/deploy/plan", json={})

        self.assertEqual(response.status_code, 400)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(body["error"]["details"]["field"], "environment")

    def test_deploy_requires_explicit_environment(self):
        response = self.client.post("/api/applications/1/deploy", json={})

        self.assertEqual(response.status_code, 400)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(body["error"]["details"]["field"], "environment")


if __name__ == "__main__":
    unittest.main()
