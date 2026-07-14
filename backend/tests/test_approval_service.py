import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models import (
    Application,
    ApplicationEnvironment,
    ApplicationReleaseBatch,
    ApplicationReleaseTarget,
    ApprovalRecord,
    Project,
)
from app.services.approval_service import ApprovalService
from app.utils.errors import ApiError


class TestConfig:
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
    TEKTON_NAMESPACE = "tekton"
    DEFAULT_IMAGE_REGISTRY = "registry.local"
    AUTO_CREATE_SCHEMA = True
    SECRET_KEY = "approval-service-test-secret"
    TESTING = True


class ApprovalServiceTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.context = self.app.app_context()
        self.context.push()
        self.project = Project(key="delivery", name="Delivery Project")
        db.session.add(self.project)
        db.session.flush()
        self.application = Application(
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
        )
        db.session.add(self.application)
        db.session.flush()
        db.session.add(ApplicationEnvironment(
            application_id=self.application.id,
            environment_name="prod",
            namespace="payment-service-prod",
            replicas=3,
            approval_required=True,
        ))
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    def test_submit_returns_existing_pending_approval_for_same_image(self):
        service = ApprovalService()
        first = service.submit(self.application, {"environment": "prod", "image_tag": "v1"}, "alice")
        second = service.submit(self.application, {"environment": "prod", "image_tag": "v1"}, "alice")

        self.assertEqual(first.id, second.id)
        self.assertEqual(ApprovalRecord.query.count(), 1)
        serialized = first.to_dict()
        self.assertEqual(serialized["project_id"], self.project.id)
        self.assertIn("kubernetes_cluster_id", serialized)
        self.assertFalse(
            {"kubeconfig", "credentials", "password", "secret", "token"}
            & serialized.keys()
        )

    def test_submit_links_release_target_in_same_transaction(self):
        environment = ApplicationEnvironment.query.filter_by(
            application_id=self.application.id,
            environment_name="prod",
        ).one()
        batch = ApplicationReleaseBatch(
            application_id=self.application.id,
            project_id=self.project.id,
            branch="main",
            git_commit="abc123",
            status="Deploying",
            created_by="alice",
        )
        db.session.add(batch)
        db.session.flush()
        target = ApplicationReleaseTarget(
            batch=batch,
            environment_id=environment.id,
            status="Starting",
        )
        db.session.add(target)
        db.session.commit()

        approval = ApprovalService().submit(
            self.application,
            {
                "environment": "prod",
                "image_tag": "v-target",
            },
            "alice",
            release_target_id=target.id,
        )

        self.assertEqual(target.approval_id, approval.id)
        self.assertEqual(target.status, "WaitingApproval")

    @patch("app.services.approval_service.ApplicationService.deploy")
    def test_approve_marks_record_and_links_pipeline_run(self, deploy):
        deploy.return_value = (
            SimpleNamespace(pipeline_run_name="payment-service-run-approve"),
            SimpleNamespace(),
        )
        approval = ApprovalService().submit(
            self.application,
            {"environment": "prod", "image_tag": "v2", "git_commit": "abc123"},
            "alice",
        )

        item = ApprovalService().approve(approval, "project-owner", "Looks good")

        self.assertEqual(item.status, "Approved")
        self.assertEqual(item.approver, "project-owner")
        self.assertEqual(item.comment, "Looks good")
        self.assertEqual(item.pipeline_run_name, "payment-service-run-approve")
        self.assertIsNotNone(item.approved_at)

    def test_reject_then_reject_again_raises_processed_error(self):
        service = ApprovalService()
        approval = service.submit(
            self.application,
            {"environment": "prod", "image_tag": "v3"},
            "alice",
        )

        rejected = service.reject(approval, "project-owner", "Risk too high")

        self.assertEqual(rejected.status, "Rejected")
        self.assertEqual(rejected.comment, "Risk too high")
        self.assertIsNotNone(rejected.rejected_at)

        with self.assertRaises(ApiError) as context:
            service.reject(approval, "project-owner", "Try again")

        self.assertEqual(context.exception.code, "APPROVAL_ALREADY_PROCESSED")


if __name__ == "__main__":
    unittest.main()
