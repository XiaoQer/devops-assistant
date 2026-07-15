import unittest
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models import Application, Project, User
from auth_helpers import create_user, csrf_post, login


class TestConfig:
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    AUTO_CREATE_SCHEMA = True
    SECRET_KEY = "runtime-routes-test-secret"
    TEKTON_NAMESPACE = "tekton"
    DEFAULT_IMAGE_REGISTRY = "registry.local"
    TESTING = True
    AUTH_SESSION_HOURS = 8
    AUTH_COOKIE_NAME = "test_session"
    AUTH_CSRF_COOKIE_NAME = "test_csrf"
    AUTH_COOKIE_SECURE = False


class RuntimeRoutesTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.context = self.app.app_context()
        self.context.push()
        self.client = self.app.test_client()
        create_user(db, User)
        _response, auth = login(self.client)
        self.csrf_token = auth["csrf_token"]
        project = Project(key="payments", name="Payments")
        db.session.add(project)
        db.session.flush()
        application = Application(
            project_id=project.id,
            name="payments-api",
            repo_url="https://example.test/payments.git",
            branch="main",
        )
        db.session.add(application)
        db.session.commit()
        self.project_id = project.id
        self.application_id = application.id

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    @patch("app.routes.runtime.ProjectRuntimeService.inventory")
    def test_project_runtime_returns_unified_response(self, inventory):
        inventory.return_value = {
            "summary": {"deployments": 0},
            "items": [],
            "pagination": {"page": 1, "page_size": 20, "total": 0, "pages": 0},
            "refreshed_at": "2026-07-15T00:00:00+00:00",
        }

        response = self.client.get(
            f"/api/projects/{self.project_id}/runtime?environment=prod&resource=pods&page=2&page_size=50"
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["items"], [])
        self.assertIn("timestamp", body)
        self.assertIn("trace_id", body)
        inventory.assert_called_once()
        self.assertEqual(inventory.call_args.args[1:5], ("prod", "pods", 2, 50))

    def test_project_runtime_requires_environment_and_bounds_page_size(self):
        missing = self.client.get(f"/api/projects/{self.project_id}/runtime")
        oversized = self.client.get(
            f"/api/projects/{self.project_id}/runtime?environment=prod&page_size=101"
        )

        self.assertEqual(missing.status_code, 400)
        self.assertEqual(oversized.status_code, 400)

    @patch("app.routes.runtime.ProjectRuntimeService.environments")
    def test_runtime_environment_directory(self, environments):
        environments.return_value = [{"name": "prod", "display_name": "Production"}]
        response = self.client.get(f"/api/projects/{self.project_id}/runtime/environments")
        self.assertEqual(response.get_json()["data"][0]["name"], "prod")

    def test_missing_project_is_not_found(self):
        response = self.client.get("/api/projects/999/runtime")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["error"]["code"], "PROJECT_NOT_FOUND")

    @patch("app.routes.runtime.DeliveryContextService.resolve")
    def test_restart_requires_confirmation(self, resolve):
        resolve.return_value = object()
        path = (
            f"/api/projects/{self.project_id}/applications/{self.application_id}"
            "/environments/prod/runtime/deployments/payments-api/restart"
        )

        response = csrf_post(
            self.client, path, self.csrf_token, json={"confirmed": False}
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.get_json()["error"]["code"], "CONFIRMATION_REQUIRED"
        )

    @patch("app.routes.runtime.RuntimeOperationService.deployment_manifest")
    @patch("app.routes.runtime.DeliveryContextService.resolve")
    def test_deployment_yaml_uses_application_environment_context(
        self, resolve, manifest
    ):
        context = object()
        resolve.return_value = context
        manifest.return_value = {"kind": "Deployment"}

        response = self.client.get(
            f"/api/projects/{self.project_id}/applications/{self.application_id}"
            "/environments/prod/runtime/deployments/payments-api/yaml"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"]["kind"], "Deployment")
        manifest.assert_called_once_with(context, "payments-api")

    @patch("app.routes.runtime.RuntimeExecService.create")
    @patch("app.routes.runtime.DeliveryContextService.resolve")
    def test_exec_session_requires_reason_and_returns_ticket(self, resolve, create):
        context = object()
        resolve.return_value = context
        create.return_value = {
            "ticket": "short-lived",
            "expires_at": "2026-07-15T00:01:00+00:00",
            "websocket_url": "/api/runtime/exec/short-lived",
        }
        path = (
            f"/api/projects/{self.project_id}/applications/{self.application_id}"
            "/environments/prod/runtime/pods/payments-api-a/exec-sessions"
        )

        response = csrf_post(
            self.client,
            path,
            self.csrf_token,
            json={
                "confirmed": True,
                "container": "api",
                "reason": "investigate incident",
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["data"]["ticket"], "short-lived")
        self.assertEqual(create.call_args.args[0], context)
        self.assertEqual(create.call_args.args[1:3], ("payments-api-a", "api"))
        self.assertEqual(create.call_args.args[4], "investigate incident")


if __name__ == "__main__":
    unittest.main()
