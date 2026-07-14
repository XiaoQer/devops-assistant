import unittest
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models import (
    ApprovalRecord,
    Application,
    ApplicationConfig,
    ApplicationEnvironment,
    Project,
    ReleaseRecord,
    User,
    UserSession,
)

from auth_helpers import FAKE_PASSWORD, create_user, csrf_post, login


class TestConfig:
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
    TEKTON_NAMESPACE = "tekton"
    DEFAULT_IMAGE_REGISTRY = "registry.local"
    AUTO_CREATE_SCHEMA = True
    SECRET_KEY = "auth-routes-test-secret"
    TESTING = True
    AUTH_SESSION_HOURS = 3
    AUTH_COOKIE_NAME = "test_session"
    AUTH_CSRF_COOKIE_NAME = "test_csrf"
    AUTH_COOKIE_SECURE = False
    CORS_ORIGINS = ["https://console.example"]
    MAX_CONTENT_LENGTH = 16384


class AuthRoutesTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.context = self.app.app_context()
        self.context.push()
        self.client = self.app.test_client()
        self.user = create_user(db, User)

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    def assert_error(self, response, status, code):
        self.assertEqual(response.status_code, status)
        body = response.get_json()
        self.assertFalse(body["success"])
        self.assertEqual(body["error"]["code"], code)
        self.assertTrue(body["trace_id"])
        return body

    def test_health_blueprint_is_public(self):
        health = self.client.get("/api/health")
        kubernetes = self.client.get("/api/health/kubernetes")

        self.assertEqual(health.status_code, 200)
        self.assertIn(kubernetes.status_code, (200, 503))
        self.assertNotEqual(kubernetes.status_code, 401)

    def test_login_is_public_and_rejects_invalid_json_fields_as_bad_request(self):
        cases = [
            {},
            {"username": "", "password": FAKE_PASSWORD},
            {"username": "admin", "password": ""},
            {"username": 123, "password": FAKE_PASSWORD},
            {"username": "admin", "password": []},
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                response = self.client.post("/api/auth/login", json=payload)
                self.assertEqual(response.status_code, 400)
                self.assertNotEqual(response.get_json()["error"]["code"], "AUTHENTICATION_REQUIRED")

    def test_login_rejects_oversized_fields_and_request_bodies(self):
        for payload in (
            {"username": "a" * 121, "password": FAKE_PASSWORD},
            {"username": "admin", "password": "a" * 4097},
        ):
            with self.subTest(field=next(key for key, value in payload.items() if len(value) > 120)):
                self.assert_error(
                    self.client.post("/api/auth/login", json=payload),
                    400,
                    "VALIDATION_ERROR",
                )

        response = self.client.post(
            "/api/auth/login",
            data=b" " * 16385,
            content_type="application/json",
        )
        self.assert_error(response, 413, "REQUEST_TOO_LARGE")

    def test_business_get_requires_authentication_with_uniform_envelope(self):
        response = self.client.get("/api/projects")

        body = self.assert_error(response, 401, "AUTHENTICATION_REQUIRED")
        self.assertIn("message", body)
        self.assertIn("timestamp", body)

    def test_login_returns_safe_user_and_csrf_and_sets_secure_cookie_shapes(self):
        response, data = login(self.client)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["user"], self.user.to_dict())
        self.assertTrue(data["csrf_token"])
        serialized = str(data).lower()
        self.assertNotIn("password_hash", serialized)
        self.assertNotIn("token_digest", serialized)
        cookies = response.headers.getlist("Set-Cookie")
        session_cookie = next(item for item in cookies if item.startswith("test_session="))
        csrf_cookie = next(item for item in cookies if item.startswith("test_csrf="))
        self.assertIn("HttpOnly", session_cookie)
        self.assertIn("SameSite=Lax", session_cookie)
        self.assertIn("Max-Age=10800", session_cookie)
        self.assertIn("Path=/", session_cookie)
        self.assertNotIn("HttpOnly", csrf_cookie)
        self.assertIn("SameSite=Lax", csrf_cookie)
        self.assertIn("Max-Age=10800", csrf_cookie)
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_wrong_credentials_have_identical_response(self):
        missing = self.client.post(
            "/api/auth/login",
            json={"username": "missing", "password": FAKE_PASSWORD},
        )
        wrong = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "wrong"},
        )

        self.assertEqual(missing.status_code, 401)
        self.assertEqual(wrong.status_code, 401)
        self.assertEqual(missing.get_json()["message"], wrong.get_json()["message"])
        self.assertEqual(
            missing.get_json()["error"]["code"],
            wrong.get_json()["error"]["code"],
        )

    def test_me_returns_same_safe_user_and_csrf(self):
        _response, login_data = login(self.client)

        response = self.client.get("/api/auth/me")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"], login_data)
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_me_rotates_missing_or_invalid_csrf_cookie_but_not_valid_cookie(self):
        login(self.client)
        session = UserSession.query.one()

        with patch(
            "app.services.auth_service.secrets.token_urlsafe",
            side_effect=["rotated-missing", "rotated-invalid"],
        ) as generate:
            self.client.delete_cookie("test_csrf")
            missing = self.client.get("/api/auth/me")
            self.assertEqual(
                missing.get_json()["data"]["csrf_token"],
                "rotated-missing",
            )
            self.assertTrue(
                any(
                    item.startswith("test_csrf=rotated-missing")
                    for item in missing.headers.getlist("Set-Cookie")
                )
            )

            self.client.set_cookie("test_csrf", "invalid")
            invalid = self.client.get("/api/auth/me")
            self.assertEqual(
                invalid.get_json()["data"]["csrf_token"],
                "rotated-invalid",
            )

            valid = self.client.get("/api/auth/me")
            self.assertEqual(
                valid.get_json()["data"]["csrf_token"],
                "rotated-invalid",
            )

        self.assertEqual(generate.call_count, 2)
        db.session.refresh(session)
        self.assertNotEqual(session.csrf_digest, "rotated-invalid")

    def test_logout_requires_csrf_then_revokes_session_and_clears_cookies(self):
        _response, data = login(self.client)
        session_id = UserSession.query.one().id

        self.assert_error(
            self.client.post("/api/auth/logout"),
            403,
            "CSRF_VALIDATION_FAILED",
        )
        response = csrf_post(self.client, "/api/auth/logout", data["csrf_token"])

        self.assertEqual(response.status_code, 200)
        db.session.expire_all()
        self.assertIsNotNone(db.session.get(UserSession, session_id).revoked_at)
        cookies = response.headers.getlist("Set-Cookie")
        self.assertTrue(any(item.startswith("test_session=;") for item in cookies))
        self.assertTrue(any(item.startswith("test_csrf=;") for item in cookies))
        self.assertIn("no-store", response.headers["Cache-Control"])
        self.assert_error(
            self.client.get("/api/auth/me"),
            401,
            "AUTHENTICATION_REQUIRED",
        )

    def test_business_write_requires_matching_csrf(self):
        _response, data = login(self.client)
        payload = {"key": "", "name": ""}

        for token in (None, "wrong"):
            headers = {} if token is None else {"X-CSRF-Token": token}
            with self.subTest(token_present=token is not None):
                self.assert_error(
                    self.client.post("/api/projects", json=payload, headers=headers),
                    403,
                    "CSRF_VALIDATION_FAILED",
                )

        response = csrf_post(
            self.client,
            "/api/projects",
            data["csrf_token"],
            json=payload,
        )
        self.assertNotEqual(response.status_code, 403)

    def test_business_write_requires_header_cookie_and_database_digest_to_match(self):
        _response, data = login(self.client)

        self.client.delete_cookie("test_csrf")
        self.assert_error(
            csrf_post(self.client, "/api/projects", data["csrf_token"], json={}),
            403,
            "CSRF_VALIDATION_FAILED",
        )
        self.client.set_cookie("test_csrf", "wrong-cookie")
        self.assert_error(
            csrf_post(self.client, "/api/projects", data["csrf_token"], json={}),
            403,
            "CSRF_VALIDATION_FAILED",
        )
        self.client.set_cookie("test_csrf", data["csrf_token"])
        self.assert_error(
            csrf_post(self.client, "/api/projects", "wrong-header", json={}),
            403,
            "CSRF_VALIDATION_FAILED",
        )

    def _create_application_delivery_records(self):
        project = Project(key="trusted-actor", name="Trusted Actor Project")
        db.session.add(project)
        db.session.flush()
        app = Application(
            project_id=project.id,
            name="trusted-actor-app",
            repo_url="https://github.com/example/trusted-actor-app.git",
            branch="main",
            language="python",
            framework="flask",
            build_type="dockerfile",
            namespace="trusted-actor-dev",
            image_name="registry.local/trusted-actor-app",
            image_tag="v2",
            port=8080,
            status="Running",
        )
        db.session.add(app)
        db.session.flush()
        environment = ApplicationEnvironment(
            application_id=app.id,
            environment_name="dev",
            namespace="trusted-actor-dev",
            approval_required=False,
        )
        source_release = ReleaseRecord(
            application_id=app.id,
            project_id=project.id,
            release_type="deploy",
            environment="dev",
            git_repo=app.repo_url,
            git_branch=app.branch,
            image_name=app.image_name,
            image_tag="v1",
            deploy_namespace=environment.namespace,
            deploy_status="Succeeded",
            deploy_user="previous-user",
        )
        approval = ApprovalRecord(
            application_id=app.id,
            project_id=project.id,
            environment="dev",
            namespace=environment.namespace,
            image_name=app.image_name,
            image_tag=app.image_tag,
            applicant="requester",
            status="Pending",
        )
        db.session.add_all([environment, source_release, approval])
        db.session.commit()
        return app, environment, source_release, approval

    def test_config_writes_use_authenticated_user_instead_of_x_user(self):
        _response, auth = login(self.client)
        app, environment, _release, _approval = (
            self._create_application_delivery_records()
        )

        response = csrf_post(
            self.client,
            f"/api/projects/{app.project_id}/applications/{app.id}/configs",
            auth["csrf_token"],
            json={
                "environment_id": environment.id,
                "config_key": "LOG_LEVEL",
                "value": "info",
            },
            headers={"X-User": "attacker"},
        )

        self.assertEqual(response.status_code, 201)
        created = ApplicationConfig.query.one()
        self.assertEqual(created.changed_by, "admin")

        update_response = self.client.patch(
            f"/api/projects/{app.project_id}/applications/{app.id}/configs/{created.id}",
            json={"value": "debug"},
            headers={
                "X-CSRF-Token": auth["csrf_token"],
                "X-User": "attacker",
            },
        )

        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(
            ApplicationConfig.query.filter_by(is_active=True).one().changed_by,
            "admin",
        )

    @patch("app.routes.applications.ApprovalService.submit")
    @patch("app.routes.applications.DeploymentPlanService.build_plan")
    def test_deploy_approval_uses_authenticated_user(self, build_plan, submit):
        _response, auth = login(self.client)
        app, environment, _release, approval = (
            self._create_application_delivery_records()
        )
        environment.approval_required = True
        db.session.commit()
        build_plan.return_value = {"can_deploy": True}
        submit.return_value = approval

        response = csrf_post(
            self.client,
            f"/api/projects/{app.project_id}/applications/{app.id}/deploy",
            auth["csrf_token"],
            json={"environment": "dev"},
            headers={"X-User": "attacker"},
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(submit.call_args.args[2], "admin")

    @patch("app.routes.applications.ReleaseService.rollback")
    @patch("app.routes.applications.ApplicationService.deploy")
    @patch("app.routes.applications.DeploymentPlanService.build_plan")
    def test_deploy_and_rollback_use_authenticated_user(
        self, build_plan, deploy, rollback
    ):
        _response, auth = login(self.client)
        app, _environment, source_release, _approval = (
            self._create_application_delivery_records()
        )
        build_plan.return_value = {"can_deploy": True}
        execution = unittest.mock.Mock()
        execution.to_dict.return_value = {}
        deployed_release = unittest.mock.Mock()
        deployed_release.to_dict.return_value = {}
        deploy.return_value = (execution, deployed_release)
        rollback_record = unittest.mock.Mock()
        rollback_record.to_dict.return_value = {}
        rollback.return_value = ({}, rollback_record)
        headers = {"X-User": "attacker"}

        deploy_response = csrf_post(
            self.client,
            f"/api/projects/{app.project_id}/applications/{app.id}/deploy",
            auth["csrf_token"],
            json={"environment": "dev"},
            headers=headers,
        )
        rollback_response = csrf_post(
            self.client,
            f"/api/projects/{app.project_id}/applications/{app.id}/rollback",
            auth["csrf_token"],
            json={"environment": "dev", "release_id": source_release.id},
            headers=headers,
        )

        self.assertEqual(deploy_response.status_code, 201)
        self.assertEqual(rollback_response.status_code, 200)
        self.assertEqual(deploy.call_args.args[2], "admin")
        self.assertEqual(rollback.call_args.args[3], "admin")

    @patch("app.routes.approvals.ApprovalService.reject")
    @patch("app.routes.approvals.ApprovalService.approve")
    @patch("app.routes.approvals.ApprovalService.submit")
    def test_approval_actions_use_authenticated_user(
        self, submit, approve, reject
    ):
        _response, auth = login(self.client)
        app, _environment, _release, approval = (
            self._create_application_delivery_records()
        )
        submit.return_value = approval
        approve.return_value = approval
        reject.return_value = approval
        headers = {"X-User": "attacker"}

        submit_response = csrf_post(
            self.client,
            f"/api/projects/{app.project_id}/approvals",
            auth["csrf_token"],
            json={"application_id": app.id, "environment": "dev"},
            headers=headers,
        )
        approve_response = csrf_post(
            self.client,
            f"/api/projects/{app.project_id}/approvals/{approval.id}/approve",
            auth["csrf_token"],
            json={"comment": "approved"},
            headers=headers,
        )
        reject_response = csrf_post(
            self.client,
            f"/api/projects/{app.project_id}/approvals/{approval.id}/reject",
            auth["csrf_token"],
            json={"comment": "rejected"},
            headers=headers,
        )

        self.assertEqual(submit_response.status_code, 201)
        self.assertEqual(approve_response.status_code, 200)
        self.assertEqual(reject_response.status_code, 200)
        self.assertEqual(submit.call_args.args[2], "admin")
        self.assertEqual(approve.call_args.args[1], "admin")
        self.assertEqual(reject.call_args.args[1], "admin")

    def test_options_preflight_is_public_and_credentialed_for_controlled_origin(self):
        response = self.client.options(
            "/api/projects",
            headers={
                "Origin": "https://console.example",
                "Access-Control-Request-Method": "POST",
            },
        )

        self.assertNotEqual(response.status_code, 401)
        self.assertEqual(
            response.headers["Access-Control-Allow-Origin"],
            "https://console.example",
        )
        self.assertEqual(response.headers["Access-Control-Allow-Credentials"], "true")

        rejected = self.client.options(
            "/api/projects",
            headers={
                "Origin": "https://attacker.example",
                "Access-Control-Request-Method": "POST",
            },
        )
        self.assertNotIn("Access-Control-Allow-Origin", rejected.headers)


if __name__ == "__main__":
    unittest.main()
