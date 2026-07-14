import unittest
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models import (
    ApprovalRecord,
    Application,
    ApplicationConfig,
    ApplicationEnvironment,
    PipelineExecution,
    Project,
    ReleaseRecord,
    User,
)

from auth_helpers import create_user, csrf_post, login


class TestConfig:
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
    TEKTON_NAMESPACE = "tekton"
    DEFAULT_IMAGE_REGISTRY = "registry.local"
    AUTO_CREATE_SCHEMA = True
    SECRET_KEY = "project-application-routes-test-secret"
    TESTING = True
    AUTH_SESSION_HOURS = 8
    AUTH_COOKIE_NAME = "test_session"
    AUTH_CSRF_COOKIE_NAME = "test_csrf"
    AUTH_COOKIE_SECURE = False


class ProjectApplicationRoutesTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.context = self.app.app_context()
        self.context.push()
        self.client = self.app.test_client()
        create_user(db, User)
        _response, auth = login(self.client)
        self.csrf_token = auth["csrf_token"]

        self.project_a = Project(key="project-a", name="Project A")
        self.project_b = Project(key="project-b", name="Project B")
        db.session.add_all([self.project_a, self.project_b])
        db.session.flush()
        self.application = Application(
            project_id=self.project_a.id,
            name="payments",
            repo_url="https://github.com/example/payments.git",
            branch="main",
            language="java",
            framework="spring-boot",
            build_type="maven",
            namespace="payments-dev",
            image_name="registry.local/payments",
            image_tag="latest",
            port=8080,
            status="Running",
        )
        db.session.add(self.application)
        db.session.flush()
        self.environment = ApplicationEnvironment(
            application_id=self.application.id,
            environment_name="dev",
            namespace="payments-dev",
        )
        db.session.add(self.environment)
        db.session.flush()
        self.config = ApplicationConfig(
            application_id=self.application.id,
            environment_id=self.environment.id,
            config_type="env",
            config_key="LOG_LEVEL",
            encrypted_value="info",
        )
        self.execution = PipelineExecution(
            application_id=self.application.id,
            project_id=self.project_a.id,
            environment="dev",
            deploy_namespace="payments-dev",
            pipeline_run_name="payments-run-001",
        )
        self.release = ReleaseRecord(
            application_id=self.application.id,
            project_id=self.project_a.id,
            release_type="deploy",
            environment="dev",
            git_repo=self.application.repo_url,
            git_branch="main",
            image_name=self.application.image_name,
            image_tag="v1",
            deploy_namespace="payments-dev",
        )
        self.approval = ApprovalRecord(
            application_id=self.application.id,
            project_id=self.project_a.id,
            environment="dev",
            namespace="payments-dev",
            image_name=self.application.image_name,
            image_tag="v2",
            applicant="admin",
        )
        db.session.add_all([
            self.config,
            self.execution,
            self.release,
            self.approval,
        ])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    def assert_not_found(self, response, code):
        self.assertEqual(response.status_code, 404)
        body = response.get_json()
        self.assertFalse(body["success"])
        self.assertEqual(body["error"]["code"], code)
        self.assertTrue(body["trace_id"])

    def test_application_and_nested_resources_hide_cross_project_ownership(self):
        paths = [
            f"/api/projects/{self.project_b.id}/applications/{self.application.id}",
            f"/api/projects/{self.project_b.id}/applications/{self.application.id}/environments",
            f"/api/projects/{self.project_b.id}/applications/{self.application.id}/configs",
            f"/api/projects/{self.project_b.id}/applications/{self.application.id}/executions",
            f"/api/projects/{self.project_b.id}/applications/{self.application.id}/releases",
        ]

        for path in paths:
            with self.subTest(path=path):
                self.assert_not_found(
                    self.client.get(path),
                    "APPLICATION_NOT_FOUND",
                )

    def test_delivery_centers_and_pipeline_details_hide_cross_project_records(self):
        self.assert_not_found(
            self.client.get(
                f"/api/projects/{self.project_b.id}/pipelines/"
                f"{self.execution.pipeline_run_name}/status"
            ),
            "PIPELINE_EXECUTION_NOT_FOUND",
        )
        self.assert_not_found(
            self.client.get(
                f"/api/projects/{self.project_b.id}/approvals/{self.approval.id}"
            ),
            "APPROVAL_NOT_FOUND",
        )

    def test_config_list_rejects_environment_from_another_project(self):
        other_application = Application(
            project_id=self.project_b.id,
            name="platform",
            repo_url="https://github.com/example/platform.git",
            branch="main",
            language="nodejs",
            framework="express",
            build_type="npm",
            namespace="platform-dev",
            image_name="registry.local/platform",
            image_tag="latest",
            port=3000,
        )
        db.session.add(other_application)
        db.session.flush()
        other_environment = ApplicationEnvironment(
            application_id=other_application.id,
            environment_name="dev",
            namespace="platform-dev",
        )
        db.session.add(other_environment)
        db.session.commit()

        response = self.client.get(
            f"/api/projects/{self.project_a.id}/applications/"
            f"{self.application.id}/configs",
            query_string={"environmentId": other_environment.id},
        )

        self.assert_not_found(response, "ENVIRONMENT_NOT_FOUND")

    def test_project_delivery_lists_only_return_owned_records(self):
        applications = self.client.get(
            f"/api/projects/{self.project_a.id}/applications"
        ).get_json()["data"]
        pipelines = self.client.get(
            f"/api/projects/{self.project_a.id}/pipelines"
        ).get_json()["data"]["items"]
        releases = self.client.get(
            f"/api/projects/{self.project_a.id}/releases"
        ).get_json()["data"]["items"]
        approvals = self.client.get(
            f"/api/projects/{self.project_a.id}/approvals"
        ).get_json()["data"]["items"]

        self.assertEqual([item["id"] for item in applications], [self.application.id])
        self.assertEqual([item["id"] for item in pipelines], [self.execution.id])
        self.assertEqual([item["id"] for item in releases], [self.release.id])
        self.assertEqual([item["id"] for item in approvals], [self.approval.id])

        for project_id in (self.project_b.id,):
            self.assertEqual(
                self.client.get(
                    f"/api/projects/{project_id}/applications"
                ).get_json()["data"],
                [],
            )
            for resource in ("pipelines", "releases", "approvals"):
                self.assertEqual(
                    self.client.get(
                        f"/api/projects/{project_id}/{resource}"
                    ).get_json()["data"]["items"],
                    [],
                )

    def test_global_delivery_routes_do_not_exist(self):
        for path in (
            "/api/applications",
            "/api/pipelines",
            "/api/releases",
            "/api/approvals",
        ):
            with self.subTest(path=path):
                self.assert_not_found(self.client.get(path), "NOT_FOUND")

    @patch("app.services.application_service.RepoAnalyzerService.analyze")
    def test_application_creation_requires_project_path_without_default_fallback(
        self, analyze
    ):
        analyze.return_value = {
            "language": "nodejs",
            "framework": "vite",
            "build_type": "npm",
            "port": 3000,
        }
        payload = {
            "name": "console",
            "repo_url": "https://github.com/example/console.git",
        }

        missing_project = csrf_post(
            self.client,
            "/api/applications",
            self.csrf_token,
            json=payload,
        )
        created = csrf_post(
            self.client,
            f"/api/projects/{self.project_b.id}/applications",
            self.csrf_token,
            json=payload,
        )

        self.assert_not_found(missing_project, "NOT_FOUND")
        self.assertEqual(created.status_code, 201)
        application = Application.query.filter_by(name="console").one()
        self.assertEqual(application.project_id, self.project_b.id)
        self.assertIsNone(Project.query.filter_by(key="default").first())


if __name__ == "__main__":
    unittest.main()
