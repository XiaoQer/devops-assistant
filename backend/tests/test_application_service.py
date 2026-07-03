import unittest
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models import Application, ApplicationEnvironment, Project, ReleaseRecord
from app.services.application_service import ApplicationService
from app.utils.errors import ApiError


class TestConfig:
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
    TEKTON_NAMESPACE = "tekton"
    DEFAULT_IMAGE_REGISTRY = "registry.local"
    AUTO_CREATE_SCHEMA = True
    SECRET_KEY = "application-service-test-secret"
    TESTING = True


class FakeKubernetesService:
    pass


class ApplicationServiceTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.context = self.app.app_context()
        self.context.push()
        self.project = Project(key="default", name="Default Project")
        db.session.add(self.project)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    @patch("app.services.application_service.RepoAnalyzerService.analyze")
    def test_create_generates_application_spec_and_default_environments(self, analyze):
        analyze.return_value = {
            "language": "nodejs",
            "framework": "vite",
            "build_type": "npm",
            "port": 3000,
        }

        app = ApplicationService().create({
            "name": "frontend-console",
            "repo_url": "https://github.com/example/frontend-console.git",
        })

        self.assertEqual(app.language, "nodejs")
        self.assertIsNotNone(app.project_id)
        self.assertEqual(app.application_spec["spec"]["runtime"]["framework"], "vite")
        self.assertEqual(
            app.application_spec["spec"]["build"]["image"],
            "registry.local/frontend-console:latest",
        )
        environments = ApplicationEnvironment.query.filter_by(application_id=app.id).all()
        self.assertEqual([item.environment_name for item in environments], ["dev"])

    def test_create_rejects_duplicate_application_name(self):
        db.session.add(Application(
            project_id=self.project.id,
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

        with self.assertRaises(ApiError) as context:
            ApplicationService().create({
                "name": "payment-service",
                "repo_url": "https://github.com/example/another-payment-service.git",
            })

        self.assertEqual(context.exception.code, "APPLICATION_EXISTS")

    @patch("app.services.application_service.TektonService.create_pipeline_run")
    @patch("app.services.application_service.ConfigurationService.materialize")
    @patch("app.services.application_service.KubernetesService", FakeKubernetesService)
    def test_deploy_creates_execution_and_release_for_environment(self, materialize, create_pipeline_run):
        materialize.return_value = {
            "config_map_name": "payment-service-config",
            "secret_name": "payment-service-secret",
            "registry_secret_name": None,
        }
        create_pipeline_run.return_value = "payment-service-run-001"
        app = Application(
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
        db.session.add(app)
        db.session.flush()
        db.session.add(ApplicationEnvironment(
            application_id=app.id,
            environment_name="staging",
            namespace="payment-service-staging",
            replicas=2,
        ))
        db.session.commit()

        execution, release = ApplicationService().deploy(
            app,
            {"environment": "staging", "image_tag": "2026.07.02"},
            "alice",
        )

        self.assertEqual(execution.pipeline_run_name, "payment-service-run-001")
        self.assertEqual(execution.image_url, "registry.local/payment-service:2026.07.02")
        self.assertEqual(release.environment, "staging")
        self.assertEqual(release.deploy_namespace, "payment-service-staging")
        self.assertEqual(release.deploy_user, "alice")
        self.assertEqual(app.status, "deploying")
        self.assertEqual(app.image_tag, "2026.07.02")
        self.assertEqual(ReleaseRecord.query.count(), 1)


if __name__ == "__main__":
    unittest.main()
