import unittest
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models import (
    Application,
    ApplicationConfig,
    ApplicationEnvironment,
    ContainerRegistry,
    Project,
    ReleaseRecord,
    User,
)
from app.services.deployment_plan_service import DeploymentPlanService

from auth_helpers import create_user, csrf_post, login


class TestConfig:
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
    TEKTON_NAMESPACE = "tekton"
    DEFAULT_IMAGE_REGISTRY = "registry.local"
    AUTO_CREATE_SCHEMA = True
    SECRET_KEY = "deployment-plan-test-secret"
    TESTING = True
    AUTH_SESSION_HOURS = 8
    AUTH_COOKIE_NAME = "test_session"
    AUTH_CSRF_COOKIE_NAME = "test_csrf"
    AUTH_COOKIE_SECURE = False


class DeploymentPlanServiceTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.context = self.app.app_context()
        self.context.push()
        self.client = self.app.test_client()
        create_user(db, User)
        _response, auth = login(self.client)
        self.csrf_token = auth["csrf_token"]
        self.project = Project(key="default", name="Default Project")
        db.session.add(self.project)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    def _create_application(self, *, build_type="maven"):
        app = Application(
            project_id=self.project.id,
            name=f"payment-service-{Application.query.count() + 1}",
            repo_url="https://github.com/example/payment-service.git",
            branch="main",
            language="java",
            framework="spring-boot",
            build_type=build_type,
            namespace="default",
            image_name="registry.local/payment-service",
            image_tag="latest",
            port=8080,
            status="Running",
        )
        db.session.add(app)
        db.session.flush()
        return app

    def test_build_plan_flags_prod_risks_and_approval(self):
        app = self._create_application()
        staging = ApplicationEnvironment(
            application_id=app.id,
            environment_name="staging",
            namespace="payment-service-staging",
            status="Healthy",
            approval_required=False,
        )
        prod = ApplicationEnvironment(
            application_id=app.id,
            environment_name="prod",
            namespace="payment-service-prod",
            status="Healthy",
            approval_required=True,
        )
        db.session.add_all([staging, prod])
        db.session.flush()
        db.session.add(ApplicationConfig(
            application_id=app.id,
            environment_id=staging.id,
            config_type="env",
            config_key="SPRING_PROFILES_ACTIVE",
            encrypted_value="token",
        ))
        db.session.add(ReleaseRecord(
            application_id=app.id,
            project_id=app.project_id,
            release_type="deploy",
            environment="prod",
            git_repo=app.repo_url,
            git_branch=app.branch,
            image_name=app.image_name,
            image_tag="v1",
            deploy_namespace="payment-service-prod",
            deploy_status="Failed",
            deploy_user="alice",
            error_message="build failed",
        ))
        db.session.commit()

        plan = DeploymentPlanService().build_plan(app, {"environment": "prod", "image_tag": "v2"})

        self.assertTrue(plan["can_deploy"])
        self.assertEqual(plan["risk_level"], "high")
        self.assertTrue(plan["target"]["approval_required"])
        self.assertIn("approval", plan["warning_checks"])
        self.assertIn("recent_release", plan["warning_checks"])
        self.assertIn("config_drift", plan["warning_checks"])

    def test_build_plan_blocks_unsupported_build_type(self):
        app = self._create_application(build_type="gradle")
        db.session.add(ApplicationEnvironment(
            application_id=app.id,
            environment_name="dev",
            namespace="payment-service-dev",
            status="Healthy",
        ))
        db.session.commit()

        plan = DeploymentPlanService().build_plan(app, {"environment": "dev"})

        self.assertFalse(plan["can_deploy"])
        self.assertIn("build_type", plan["blocked_checks"])

    def test_build_plan_blocks_unknown_environment(self):
        app = self._create_application()
        db.session.commit()

        plan = DeploymentPlanService().build_plan(app, {"environment": "qa"})

        self.assertFalse(plan["can_deploy"])
        self.assertIn("environment", plan["blocked_checks"])

    def test_build_plan_uses_application_project_default_registry(self):
        project = Project(key="payments", name="Payments")
        other_project = Project(key="platform", name="Platform")
        db.session.add_all([project, other_project])
        db.session.flush()
        app = self._create_application()
        app.project_id = project.id
        db.session.add(ApplicationEnvironment(
            application_id=app.id,
            environment_name="dev",
            namespace="payment-service-dev",
            status="Healthy",
        ))
        db.session.add_all([
            ContainerRegistry(
                project_id=project.id,
                name="Payments GHCR",
                provider="ghcr",
                server="ghcr.io",
                namespace="acme-payments",
                username="robot",
                encrypted_password="ciphertext",
                is_default=True,
            ),
            ContainerRegistry(
                project_id=other_project.id,
                name="Platform Harbor",
                provider="harbor",
                server="harbor.platform.example",
                namespace="platform",
                username="robot",
                encrypted_password="ciphertext",
                is_default=True,
            ),
        ])
        db.session.commit()

        plan = DeploymentPlanService().build_plan(app, {"environment": "dev"})

        self.assertEqual(
            plan["target"]["image_name"],
            "ghcr.io/acme-payments/payment-service-1",
        )
        registry_check = next(
            check for check in plan["checks"] if check["name"] == "registry"
        )
        self.assertEqual(registry_check["status"], "pass")

    @patch("app.services.application_service.TektonService.create_pipeline_run")
    @patch("app.services.application_service.ConfigurationService.materialize")
    @patch("app.services.application_service.KubernetesService")
    def test_deploy_route_rejects_when_precheck_fails(self, _kubernetes, materialize, create_pipeline_run):
        materialize.return_value = {
            "config_map_name": "payment-service-config",
            "secret_name": "payment-service-secret",
            "registry_secret_name": None,
        }
        create_pipeline_run.return_value = "ignored"
        app = self._create_application(build_type="gradle")
        db.session.add(ApplicationEnvironment(
            application_id=app.id,
            environment_name="dev",
            namespace="payment-service-dev",
            status="Healthy",
        ))
        db.session.commit()

        response = csrf_post(
            self.client,
            f"/api/applications/{app.id}/deploy",
            self.csrf_token,
            json={"environment": "dev"},
        )

        self.assertEqual(response.status_code, 409)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "DEPLOYMENT_PRECHECK_FAILED")
        self.assertFalse(body["error"]["details"]["can_deploy"])
        self.assertIn("build_type", body["error"]["details"]["blocked_checks"])

    def test_deploy_plan_route_returns_structured_plan(self):
        app = self._create_application()
        db.session.add(ApplicationEnvironment(
            application_id=app.id,
            environment_name="dev",
            namespace="payment-service-dev",
            status="Healthy",
        ))
        db.session.commit()

        response = csrf_post(
            self.client,
            f"/api/applications/{app.id}/deploy/plan",
            self.csrf_token,
            json={"environment": "dev"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()["data"]
        self.assertTrue(body["can_deploy"])
        self.assertEqual(body["target"]["environment"], "dev")
        self.assertIn("checks", body)


if __name__ == "__main__":
    unittest.main()
