import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models import (
    Application,
    ApplicationBuildVersion,
    ApplicationEnvironment,
    ApplicationReleaseBatch,
    ApplicationReleaseTarget,
    PipelineExecution,
    Project,
)
from app.services.cicd_workbench_service import CicdWorkbenchService
from app.services.delivery_reconciler import DeliveryReconciler


class TestConfig:
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    AUTO_CREATE_SCHEMA = True
    SECRET_KEY = "cicd-workbench-service-test-secret"
    TESTING = True


class CicdWorkbenchServiceTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.context = self.app.app_context()
        self.context.push()
        self.now = datetime.now(timezone.utc)
        self.project = Project(key="delivery", name="Delivery")
        self.other_project = Project(key="other", name="Other")
        db.session.add_all([self.project, self.other_project])
        db.session.flush()
        self.recent = self.make_application(
            self.project, "payments", "https://github.com/acme/payments.git"
        )
        self.older = self.make_application(
            self.project, "orders", "https://github.com/acme/orders.git"
        )
        self.foreign = self.make_application(
            self.other_project, "foreign", "https://github.com/acme/foreign.git"
        )
        self.dev = ApplicationEnvironment(
            application_id=self.recent.id,
            environment_name="dev",
            namespace="payments-dev",
        )
        self.prod = ApplicationEnvironment(
            application_id=self.recent.id,
            environment_name="prod",
            namespace="payments-prod",
            approval_required=True,
        )
        db.session.add_all([self.dev, self.prod])
        db.session.flush()
        self.recent_build = self.make_build(
            self.recent, "abc123", "Succeeded", self.now
        )
        self.older_build = self.make_build(
            self.older, "old123", "Failed", self.now - timedelta(days=1)
        )
        batch = ApplicationReleaseBatch(
            application_id=self.recent.id,
            project_id=self.project.id,
            build_version=self.recent_build,
            branch="main",
            git_commit="abc123",
            commit_message="ship payments",
            status="Deploying",
            created_by="admin",
            created_at=self.now,
        )
        db.session.add(batch)
        db.session.flush()
        db.session.add(ApplicationReleaseTarget(
            batch=batch,
            environment_id=self.dev.id,
            build_version_id=self.recent_build.id,
            status="Running",
        ))
        db.session.add(PipelineExecution(
            application_id=self.recent.id,
            project_id=self.project.id,
            environment="dev",
            deploy_namespace="payments-dev",
            pipeline_run_name="payments-deploy-1",
            status="Running",
            created_at=self.now,
        ))
        self.make_build(self.foreign, "foreign1", "Running", self.now + timedelta(minutes=1))
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    def make_application(self, project, name, repo_url):
        application = Application(
            project_id=project.id,
            name=name,
            repo_url=repo_url,
            branch="main",
            language="java",
            framework="spring-boot",
            build_type="maven",
            namespace=f"{name}-dev",
            image_name=f"registry.local/{name}",
            image_tag="latest",
            port=8080,
        )
        db.session.add(application)
        db.session.flush()
        return application

    def make_build(self, application, commit, status, created_at):
        build = ApplicationBuildVersion(
            application_id=application.id,
            project_id=application.project_id,
            version=commit,
            git_repo=application.repo_url,
            git_branch="main",
            git_commit=commit,
            image_name=application.image_name,
            image_tag=commit,
            status=status,
            created_by="admin",
            created_at=created_at,
        )
        db.session.add(build)
        db.session.flush()
        return build

    def test_lists_project_applications_by_recent_activity(self):
        items = CicdWorkbenchService().list_applications(self.project.id)

        self.assertEqual(
            [item["application"]["name"] for item in items],
            ["payments", "orders"],
        )
        self.assertEqual(items[0]["latest_build"]["git_commit"], "abc123")
        self.assertEqual(
            items[0]["latest_batch"]["targets"][0]["environment"], "dev"
        )
        self.assertEqual(
            {item["environment_name"] for item in items[0]["available_environments"]},
            {"dev", "prod"},
        )
        self.assertEqual(items[0]["activity_status"], "Running")

    def test_search_matches_application_name_or_repository(self):
        by_name = CicdWorkbenchService().list_applications(
            self.project.id, query="PAY"
        )
        by_repo = CicdWorkbenchService().list_applications(
            self.project.id, query="orders.git"
        )

        self.assertEqual([item["application"]["name"] for item in by_name], ["payments"])
        self.assertEqual([item["application"]["name"] for item in by_repo], ["orders"])

    def test_filters_by_derived_activity_status(self):
        failed = CicdWorkbenchService().list_applications(
            self.project.id, status="Failed"
        )

        self.assertEqual([item["application"]["name"] for item in failed], ["orders"])

    def test_never_returns_applications_from_another_project(self):
        items = CicdWorkbenchService().list_applications(self.project.id)

        self.assertNotIn("foreign", [item["application"]["name"] for item in items])

    def test_reconcile_project_only_advances_active_batches_in_project(self):
        foreign_id = self.foreign.id
        older_id = self.older.id
        foreign_build_id = self.foreign.build_versions[0].id
        older_build_id = self.older_build.id
        active_batch_id = self.recent.release_batches[0].id
        foreign_batch = ApplicationReleaseBatch(
            application_id=foreign_id,
            project_id=self.other_project.id,
            build_version_id=foreign_build_id,
            branch="main",
            git_commit="foreign1",
            status="Building",
            created_by="admin",
        )
        completed = ApplicationReleaseBatch(
            application_id=older_id,
            project_id=self.project.id,
            build_version_id=older_build_id,
            branch="main",
            git_commit="old123",
            status="Succeeded",
            created_by="admin",
        )
        db.session.add_all([foreign_batch, completed])
        db.session.commit()
        reconciler = DeliveryReconciler()

        with patch.object(reconciler, "reconcile_batch") as reconcile_batch:
            count = reconciler.reconcile_project(self.project.id)

        self.assertEqual(count, 1)
        reconcile_batch.assert_called_once_with(active_batch_id)


if __name__ == "__main__":
    unittest.main()
