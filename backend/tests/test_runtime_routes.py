import unittest
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models import Project, User
from auth_helpers import create_user, login


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
        login(self.client)
        project = Project(key="payments", name="Payments")
        db.session.add(project)
        db.session.commit()
        self.project_id = project.id

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    @patch("app.routes.runtime.ProjectRuntimeService.overview")
    def test_project_runtime_returns_unified_response(self, overview):
        overview.return_value = {
            "summary": {"environments": 0, "deployments": 0},
            "environments": [],
            "refreshed_at": "2026-07-15T00:00:00+00:00",
        }

        response = self.client.get(f"/api/projects/{self.project_id}/runtime")

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["environments"], [])
        self.assertIn("timestamp", body)
        self.assertIn("trace_id", body)
        overview.assert_called_once()
        self.assertEqual(overview.call_args.args[0].id, self.project_id)

    def test_missing_project_is_not_found(self):
        response = self.client.get("/api/projects/999/runtime")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["error"]["code"], "PROJECT_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
