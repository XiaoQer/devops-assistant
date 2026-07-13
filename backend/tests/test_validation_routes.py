import unittest

from app import create_app
from app.extensions import db
from app.models import Application, Project, User

from auth_helpers import create_user, csrf_post, login


class TestConfig:
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
    TEKTON_NAMESPACE = "tekton"
    DEFAULT_IMAGE_REGISTRY = "registry.local"
    AUTO_CREATE_SCHEMA = True
    SECRET_KEY = "route-validation-test-secret"
    TESTING = True
    AUTH_SESSION_HOURS = 8
    AUTH_COOKIE_NAME = "test_session"
    AUTH_CSRF_COOKIE_NAME = "test_csrf"
    AUTH_COOKIE_SECURE = False


class RouteValidationTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.context = self.app.app_context()
        self.context.push()
        self.client = self.app.test_client()
        create_user(db, User)
        _response, auth = login(self.client)
        self.csrf_token = auth["csrf_token"]
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
        project = Project(key="payments", name="Payments")
        db.session.add(project)
        db.session.commit()
        self.project_id = project.id

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    def test_ai_intent_route_requires_non_empty_text(self):
        response = csrf_post(
            self.client, "/api/ai/intent/resolve", self.csrf_token, json={"text": "   "}
        )

        self.assertEqual(response.status_code, 400)
        body = response.get_json()
        self.assertFalse(body["success"])
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(body["error"]["details"]["field"], "text")

    def test_ai_intent_route_rejects_non_object_payload(self):
        response = csrf_post(
            self.client,
            "/api/ai/intent/resolve",
            self.csrf_token,
            json=["open payment-service"],
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "INVALID_REQUEST_BODY")

    def test_ai_intent_route_still_resolves_known_application(self):
        response = csrf_post(
            self.client,
            "/api/ai/intent/resolve",
            self.csrf_token,
            json={"text": "打开 payment-service"},
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()["data"]
        self.assertEqual(data["intent"], "open_application")
        self.assertEqual(data["target"]["application_name"], "payment-service")

    def test_create_application_requires_name_and_repo_url(self):
        response = csrf_post(
            self.client, "/api/applications", self.csrf_token, json={}
        )

        self.assertEqual(response.status_code, 400)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(body["error"]["details"]["fields"], ["name", "repo_url"])

    def test_submit_approval_requires_application_id(self):
        response = csrf_post(self.client, "/api/approvals", self.csrf_token, json={})

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

    def test_create_registry_requires_configuration_and_credentials(self):
        response = csrf_post(
            self.client,
            f"/api/projects/{self.project_id}/registries",
            self.csrf_token,
            json={},
        )

        self.assertEqual(response.status_code, 400)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(
            body["error"]["details"]["fields"],
            ["name", "server", "username", "password"],
        )

    def test_registry_connection_requires_object_and_write_only_fields(self):
        path = f"/api/projects/{self.project_id}/registries/test-connection"
        non_object = csrf_post(
            self.client,
            path,
            self.csrf_token,
            json=["not-an-object"],
        )
        self.assertEqual(non_object.status_code, 400)
        self.assertEqual(
            non_object.get_json()["error"]["code"],
            "INVALID_REQUEST_BODY",
        )

        missing = csrf_post(
            self.client,
            path,
            self.csrf_token,
            json={},
        )
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(missing.get_json()["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(
            missing.get_json()["error"]["details"]["fields"],
            ["server", "username", "password"],
        )

        http_server = csrf_post(
            self.client,
            path,
            self.csrf_token,
            json={
                "server": "http://harbor.example.test",
                "username": "robot",
                "password": "safe-test-value",
            },
        )
        self.assertEqual(http_server.status_code, 400)
        self.assertEqual(
            http_server.get_json()["error"]["code"],
            "REGISTRY_SERVER_INVALID",
        )

        non_boolean_tls = csrf_post(
            self.client,
            path,
            self.csrf_token,
            json={
                "server": "harbor.example.test",
                "username": "robot",
                "password": "safe-test-value",
                "skip_tls_verify": "false",
            },
        )
        self.assertEqual(non_boolean_tls.status_code, 400)
        self.assertEqual(
            non_boolean_tls.get_json()["error"]["code"],
            "REGISTRY_TLS_VERIFY_INVALID",
        )

    def test_cluster_connection_requires_object_and_write_only_fields(self):
        non_object = csrf_post(
            self.client,
            f"/api/projects/{self.project_id}/clusters/test-connection",
            self.csrf_token,
            json=["not-an-object"],
        )
        self.assertEqual(non_object.status_code, 400)
        self.assertEqual(non_object.get_json()["error"]["code"], "INVALID_REQUEST_BODY")

        missing = csrf_post(
            self.client,
            f"/api/projects/{self.project_id}/clusters/test-connection",
            self.csrf_token,
            json={},
        )
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(missing.get_json()["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(
            missing.get_json()["error"]["details"]["fields"],
            ["kubeconfig", "kube_context"],
        )

    def test_deploy_plan_requires_explicit_environment(self):
        response = csrf_post(
            self.client, "/api/applications/1/deploy/plan", self.csrf_token, json={}
        )

        self.assertEqual(response.status_code, 400)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(body["error"]["details"]["field"], "environment")

    def test_deploy_requires_explicit_environment(self):
        response = csrf_post(
            self.client, "/api/applications/1/deploy", self.csrf_token, json={}
        )

        self.assertEqual(response.status_code, 400)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(body["error"]["details"]["field"], "environment")


if __name__ == "__main__":
    unittest.main()
