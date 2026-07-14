import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models import (
    ApprovalRecord,
    Application,
    ApplicationConfig,
    ApplicationEnvironment,
    ContainerRegistry,
    KubernetesCluster,
    PipelineExecution,
    Project,
    ReleaseRecord,
    User,
)
from app.services.configuration_service import ConfigurationService

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

    @patch("app.routes.applications.ApplicationRuntimeService")
    def test_runtime_routes_delegate_to_environment_target_context(self, runtime):
        cluster = KubernetesCluster(
            project_id=self.project_a.id,
            name="payments-target",
            kube_context="target",
            environment_label="development",
            encrypted_kubeconfig="ciphertext",
            connection_status="connected",
            is_default=True,
        )
        registry = ContainerRegistry(
            project_id=self.project_a.id,
            name="payments-registry",
            provider="ghcr",
            server="ghcr.io",
            namespace="acme",
            username="robot",
            encrypted_password="ciphertext",
            connection_status="connected",
            is_default=True,
        )
        db.session.add_all([cluster, registry])
        db.session.flush()
        self.environment.kubernetes_cluster_id = cluster.id
        db.session.commit()
        service = runtime.return_value
        service.status.return_value = {"status": "Healthy"}
        service.pod_logs.return_value = "target logs"
        service.pod_manifest.return_value = {"kind": "Pod"}
        prefix = (
            f"/api/projects/{self.project_a.id}/applications/"
            f"{self.application.id}"
        )

        status = self.client.get(f"{prefix}/status?environment=dev")
        logs = self.client.get(
            f"{prefix}/runtime/pods/pod-1/logs?environment=dev"
        )
        manifest = self.client.get(
            f"{prefix}/runtime/pods/pod-1/yaml?environment=dev"
        )

        self.assertEqual(status.status_code, 200)
        self.assertEqual(logs.get_json()["data"]["logs"], "target logs")
        self.assertEqual(manifest.get_json()["data"], {"kind": "Pod"})
        for call in (
            service.status.call_args,
            service.pod_logs.call_args,
            service.pod_manifest.call_args,
        ):
            self.assertEqual(call.args[0].cluster.id, cluster.id)

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

    @patch("app.routes.pipelines.DeliveryReconciler")
    @patch("app.routes.pipelines.CicdWorkbenchService")
    def test_cicd_workbench_is_project_scoped_and_forwards_filters(
        self, workbench, reconciler
    ):
        workbench.return_value.list_applications.return_value = [{
            "application": {"id": self.application.id, "name": "payments"},
            "activity_status": "Running",
        }]

        response = self.client.get(
            f"/api/projects/{self.project_a.id}/pipelines/workbench"
            "?query=pay&status=Running"
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["success"])
        self.assertTrue(body["timestamp"])
        self.assertTrue(body["trace_id"])
        self.assertEqual(body["data"]["items"][0]["application"]["name"], "payments")
        workbench.return_value.list_applications.assert_called_once_with(
            self.project_a.id,
            query="pay",
            status="Running",
        )
        reconciler.return_value.reconcile_project.assert_called_once_with(
            self.project_a.id
        )

    @patch("app.routes.pipelines.CicdWorkbenchService")
    def test_cicd_workbench_rejects_missing_project(self, workbench):
        response = self.client.get("/api/projects/99999/pipelines/workbench")

        self.assert_not_found(response, "PROJECT_NOT_FOUND")
        workbench.assert_not_called()

    @patch("app.routes.applications.DeliveryReconciler")
    @patch("app.routes.applications.ReleaseBatchService.add_targets")
    def test_append_release_targets_delegates_and_reconciles(
        self, add_targets, reconciler
    ):
        add_targets.return_value = SimpleNamespace(id=42)
        reconciler.return_value.reconcile_batch.return_value = {
            "id": 42,
            "targets": [{"environment_id": self.environment.id}],
        }

        response = csrf_post(
            self.client,
            f"/api/projects/{self.project_a.id}/applications/"
            f"{self.application.id}/release-batches/42/targets",
            self.csrf_token,
            json={"environment_ids": [self.environment.id]},
        )

        self.assertEqual(response.status_code, 201)
        body = response.get_json()
        self.assertTrue(body["success"])
        self.assertTrue(body["timestamp"])
        self.assertTrue(body["trace_id"])
        self.assertEqual(body["data"]["id"], 42)
        add_targets.assert_called_once_with(
            self.application, 42, [self.environment.id]
        )
        reconciler.return_value.reconcile_batch.assert_called_once_with(42)

    @patch("app.routes.applications.DeliveryReconciler")
    @patch("app.routes.applications.ReleaseBatchService.add_targets")
    def test_append_release_targets_hides_cross_project_application(
        self, add_targets, reconciler
    ):
        response = csrf_post(
            self.client,
            f"/api/projects/{self.project_b.id}/applications/"
            f"{self.application.id}/release-batches/42/targets",
            self.csrf_token,
            json={"environment_ids": [self.environment.id]},
        )

        self.assert_not_found(response, "APPLICATION_NOT_FOUND")
        add_targets.assert_not_called()
        reconciler.assert_not_called()

    def test_deploy_rejects_internal_recovery_fields(self):
        response = csrf_post(
            self.client,
            f"/api/projects/{self.project_a.id}/applications/"
            f"{self.application.id}/deploy",
            self.csrf_token,
            json={
                "environment": "dev",
                "release_target_id": 999,
                "existing_pipeline_run_name": "forged-run",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json()["error"]["code"],
            "INTERNAL_DELIVERY_FIELDS_FORBIDDEN",
        )

    def test_approval_submit_rejects_internal_recovery_field(self):
        response = csrf_post(
            self.client,
            f"/api/projects/{self.project_a.id}/approvals",
            self.csrf_token,
            json={
                "application_id": self.application.id,
                "environment": "dev",
                "release_target_id": 999,
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json()["error"]["code"],
            "INTERNAL_DELIVERY_FIELDS_FORBIDDEN",
        )

    @patch("app.routes.pipelines.TektonService")
    def test_pipeline_logs_and_retry_deny_cross_project_before_tekton(self, tekton):
        logs = self.client.get(
            f"/api/projects/{self.project_b.id}/pipelines/"
            f"{self.execution.pipeline_run_name}/logs"
        )
        retry = csrf_post(
            self.client,
            f"/api/projects/{self.project_b.id}/pipelines/"
            f"{self.execution.pipeline_run_name}/retry",
            self.csrf_token,
        )

        self.assert_not_found(logs, "PIPELINE_EXECUTION_NOT_FOUND")
        self.assert_not_found(retry, "PIPELINE_EXECUTION_NOT_FOUND")
        tekton.assert_not_called()

    @patch("app.routes.pipelines.TektonService")
    def test_pipeline_operations_always_use_server_namespace(self, tekton):
        service = tekton.return_value
        service.get_pipeline_run_status.return_value = {"status": "Running"}
        service.list_task_runs.return_value = []
        service.get_pipeline_run_log_details.return_value = {"status": "Running"}
        service.get_pipeline_run_logs.return_value = "logs"
        service.retry_pipeline_run.return_value = {"pipeline_run_name": "retried"}
        prefix = (
            f"/api/projects/{self.project_a.id}/pipelines/"
            f"{self.execution.pipeline_run_name}"
        )

        self.assertEqual(
            self.client.get(f"{prefix}/status?namespace=attacker").status_code,
            200,
        )
        self.assertEqual(
            self.client.get(f"{prefix}/logs?namespace=attacker").status_code,
            200,
        )
        self.assertEqual(
            csrf_post(
                self.client,
                f"{prefix}/retry?namespace=attacker",
                self.csrf_token,
            ).status_code,
            201,
        )

        service.get_pipeline_run_status.assert_called_once_with(
            self.execution.pipeline_run_name, TestConfig.TEKTON_NAMESPACE
        )
        service.list_task_runs.assert_called_once_with(
            self.execution.pipeline_run_name, TestConfig.TEKTON_NAMESPACE
        )
        service.get_pipeline_run_log_details.assert_called_once_with(
            self.execution.pipeline_run_name, TestConfig.TEKTON_NAMESPACE
        )
        service.get_pipeline_run_logs.assert_called_once_with(
            self.execution.pipeline_run_name, TestConfig.TEKTON_NAMESPACE
        )
        service.retry_pipeline_run.assert_called_once_with(
            self.execution.pipeline_run_name, TestConfig.TEKTON_NAMESPACE
        )

    @patch("app.services.release_service.ApplicationRuntimeService")
    def test_inconsistent_release_project_id_is_hidden_and_cannot_rollback(
        self, runtime
    ):
        inconsistent = ReleaseRecord(
            application_id=self.application.id,
            project_id=self.project_b.id,
            release_type="deploy",
            environment="dev",
            git_repo=self.application.repo_url,
            git_branch="main",
            image_name=self.application.image_name,
            image_tag="cross-project",
            deploy_namespace="payments-dev",
            deploy_status="Succeeded",
        )
        db.session.add(inconsistent)
        db.session.commit()

        nested = self.client.get(
            f"/api/projects/{self.project_a.id}/applications/"
            f"{self.application.id}/releases"
        ).get_json()["data"]
        project_b_center = self.client.get(
            f"/api/projects/{self.project_b.id}/releases"
        ).get_json()["data"]["items"]
        rollback = csrf_post(
            self.client,
            f"/api/projects/{self.project_a.id}/applications/"
            f"{self.application.id}/rollback",
            self.csrf_token,
            json={"release_id": inconsistent.id, "environment": "dev"},
        )

        self.assertNotIn(inconsistent.id, [item["id"] for item in nested])
        self.assertNotIn(inconsistent.id, [item["id"] for item in project_b_center])
        self.assert_not_found(rollback, "RELEASE_NOT_FOUND")
        runtime.assert_not_called()

    def test_inconsistent_execution_project_id_is_hidden_from_all_projects(self):
        inconsistent = PipelineExecution(
            application_id=self.application.id,
            project_id=self.project_b.id,
            environment="dev",
            deploy_namespace="payments-dev",
            pipeline_run_name="payments-run-inconsistent",
        )
        db.session.add(inconsistent)
        db.session.commit()

        nested = self.client.get(
            f"/api/projects/{self.project_a.id}/applications/"
            f"{self.application.id}/executions"
        ).get_json()["data"]
        project_b_center = self.client.get(
            f"/api/projects/{self.project_b.id}/pipelines"
        ).get_json()["data"]["items"]
        detail = self.client.get(
            f"/api/projects/{self.project_b.id}/pipelines/"
            f"{inconsistent.pipeline_run_name}/status"
        )

        self.assertNotIn(inconsistent.id, [item["id"] for item in nested])
        self.assertNotIn(inconsistent.id, [item["id"] for item in project_b_center])
        self.assert_not_found(detail, "PIPELINE_EXECUTION_NOT_FOUND")

    def test_application_serialization_ignores_inconsistent_latest_execution(self):
        inconsistent = PipelineExecution(
            application_id=self.application.id,
            project_id=self.project_b.id,
            environment="dev",
            deploy_namespace="payments-dev",
            pipeline_run_name="payments-run-leaked-latest",
        )
        db.session.add(inconsistent)
        db.session.commit()

        list_item = self.client.get(
            f"/api/projects/{self.project_a.id}/applications"
        ).get_json()["data"][0]
        detail = self.client.get(
            f"/api/projects/{self.project_a.id}/applications/{self.application.id}"
        ).get_json()["data"]

        self.assertEqual(list_item["latest_execution"]["id"], self.execution.id)
        self.assertEqual(detail["latest_execution"]["id"], self.execution.id)

    def create_inconsistent_approval(self, image_tag):
        approval = ApprovalRecord(
            application_id=self.application.id,
            project_id=self.project_b.id,
            environment="dev",
            namespace="payments-dev",
            image_name=self.application.image_name,
            image_tag=image_tag,
            applicant="admin",
        )
        db.session.add(approval)
        db.session.commit()
        return approval

    def test_inconsistent_approval_is_hidden_from_project_list(self):
        inconsistent = self.create_inconsistent_approval("approval-list")

        items = self.client.get(
            f"/api/projects/{self.project_b.id}/approvals"
        ).get_json()["data"]["items"]

        self.assertNotIn(inconsistent.id, [item["id"] for item in items])

    def test_inconsistent_approval_is_hidden_from_project_detail(self):
        inconsistent = self.create_inconsistent_approval("approval-detail")

        response = self.client.get(
            f"/api/projects/{self.project_b.id}/approvals/{inconsistent.id}"
        )

        self.assert_not_found(response, "APPROVAL_NOT_FOUND")

    @patch("app.services.approval_service.ApplicationService.deploy")
    @patch("app.routes.approvals.ApprovalService.approve")
    def test_inconsistent_approval_cannot_be_approved(
        self, approve, deploy
    ):
        inconsistent = self.create_inconsistent_approval("approval-approve")
        approve.return_value = inconsistent

        response = csrf_post(
            self.client,
            f"/api/projects/{self.project_b.id}/approvals/"
            f"{inconsistent.id}/approve",
            self.csrf_token,
        )

        self.assert_not_found(response, "APPROVAL_NOT_FOUND")
        approve.assert_not_called()
        deploy.assert_not_called()

    @patch("app.services.approval_service.ApplicationService.deploy")
    @patch("app.routes.approvals.ApprovalService.reject")
    def test_inconsistent_approval_cannot_be_rejected(
        self, reject, deploy
    ):
        inconsistent = self.create_inconsistent_approval("approval-reject")
        reject.return_value = inconsistent

        response = csrf_post(
            self.client,
            f"/api/projects/{self.project_b.id}/approvals/"
            f"{inconsistent.id}/reject",
            self.csrf_token,
            json={"comment": "wrong project"},
        )

        self.assert_not_found(response, "APPROVAL_NOT_FOUND")
        reject.assert_not_called()
        deploy.assert_not_called()

    def test_approval_submission_ignores_inconsistent_duplicate(self):
        inconsistent = self.create_inconsistent_approval("duplicate-tag")

        response = csrf_post(
            self.client,
            f"/api/projects/{self.project_a.id}/approvals",
            self.csrf_token,
            json={
                "application_id": self.application.id,
                "environment": "dev",
                "image_tag": "duplicate-tag",
            },
        )

        self.assertEqual(response.status_code, 201)
        created = response.get_json()["data"]
        self.assertNotEqual(created["id"], inconsistent.id)
        self.assertEqual(created["project_id"], self.project_a.id)

    @patch("app.services.release_service.TektonService")
    def test_project_release_center_synchronizes_only_owned_releases(self, tekton):
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
        self.release.pipeline_run_name = "payments-release-run"
        other_release = ReleaseRecord(
            application_id=other_application.id,
            project_id=self.project_b.id,
            release_type="deploy",
            environment="dev",
            git_repo=other_application.repo_url,
            git_branch="main",
            image_name=other_application.image_name,
            image_tag="v1",
            pipeline_run_name="platform-release-run",
            deploy_namespace="platform-dev",
        )
        db.session.add(other_release)
        db.session.commit()
        tekton.return_value.get_pipeline_run_status.return_value = {
            "status": "Running"
        }

        response = self.client.get(
            f"/api/projects/{self.project_a.id}/releases"
        )

        self.assertEqual(response.status_code, 200)
        tekton.return_value.get_pipeline_run_status.assert_called_once_with(
            self.release.pipeline_run_name, TestConfig.TEKTON_NAMESPACE
        )

    @patch("app.services.release_service.TektonService")
    def test_release_sync_does_not_update_inconsistent_execution(self, tekton):
        self.release.pipeline_run_name = "shared-release-run"
        inconsistent = PipelineExecution(
            application_id=self.application.id,
            project_id=self.project_b.id,
            environment="dev",
            deploy_namespace="payments-dev",
            pipeline_run_name="shared-release-run",
            status="Pending",
        )
        db.session.add(inconsistent)
        db.session.commit()
        tekton.return_value.get_pipeline_run_status.return_value = {
            "status": "Failed",
            "message": "build failed",
        }

        response = self.client.get(
            f"/api/projects/{self.project_a.id}/releases"
        )

        self.assertEqual(response.status_code, 200)
        db.session.refresh(inconsistent)
        self.assertEqual(inconsistent.status, "Pending")
        self.assertEqual(self.release.deploy_status, "Failed")

    def test_config_history_service_scopes_query_by_application(self):
        other_application = Application(
            project_id=self.project_b.id,
            name="history-owner",
            repo_url="https://github.com/example/history-owner.git",
            branch="main",
            language="nodejs",
            framework="express",
            build_type="npm",
            namespace="history-owner-dev",
            image_name="registry.local/history-owner",
            image_tag="latest",
            port=3000,
        )
        db.session.add(other_application)
        db.session.flush()
        other_environment = ApplicationEnvironment(
            application_id=other_application.id,
            environment_name="dev",
            namespace="history-owner-dev",
        )
        db.session.add(other_environment)
        db.session.flush()
        self.config.config_group_id = "shared-history-group"
        other_config = ApplicationConfig(
            config_group_id="shared-history-group",
            application_id=other_application.id,
            environment_id=other_environment.id,
            config_type="env",
            config_key="LOG_LEVEL",
            encrypted_value="debug",
        )
        db.session.add(other_config)
        db.session.commit()

        items = ConfigurationService().history(
            self.application.id, "shared-history-group"
        )

        self.assertEqual([item.id for item in items], [self.config.id])

    def test_config_create_rejects_duplicate_active_key(self):
        response = csrf_post(
            self.client,
            f"/api/projects/{self.project_a.id}/applications/{self.application.id}/configs",
            self.csrf_token,
            json={
                "environment_id": self.environment.id,
                "config_type": "env",
                "config_key": self.config.config_key,
                "value": "debug",
            },
        )

        self.assertEqual(response.status_code, 409)
        body = response.get_json()
        self.assertFalse(body["success"])
        self.assertEqual(body["error"]["code"], "CONFIG_EXISTS")

    def test_config_mutations_require_environment_to_belong_to_application(self):
        other_application = Application(
            project_id=self.project_b.id,
            name="config-environment-owner",
            repo_url="https://github.com/example/config-environment-owner.git",
            branch="main",
            language="nodejs",
            framework="express",
            build_type="npm",
            namespace="config-owner-dev",
            image_name="registry.local/config-owner",
            image_tag="latest",
            port=3000,
        )
        db.session.add(other_application)
        db.session.flush()
        other_environment = ApplicationEnvironment(
            application_id=other_application.id,
            environment_name="dev",
            namespace="config-owner-dev",
        )
        db.session.add(other_environment)
        db.session.flush()
        malformed = []
        for suffix in ("update", "delete", "history"):
            malformed.append(ApplicationConfig(
                config_group_id=f"malformed-{suffix}",
                application_id=self.application.id,
                environment_id=other_environment.id,
                config_type="secret",
                config_key=f"MALFORMED_{suffix.upper()}",
                encrypted_value="ciphertext",
                is_secret=True,
            ))
        db.session.add_all(malformed)
        db.session.commit()

        update = self.client.patch(
            f"/api/projects/{self.project_a.id}/applications/"
            f"{self.application.id}/configs/{malformed[0].id}",
            headers={"X-CSRF-Token": self.csrf_token},
            json={"value": "new-value"},
        )
        delete = self.client.delete(
            f"/api/projects/{self.project_a.id}/applications/"
            f"{self.application.id}/configs/{malformed[1].id}",
            headers={"X-CSRF-Token": self.csrf_token},
        )
        history = self.client.get(
            f"/api/projects/{self.project_a.id}/applications/"
            f"{self.application.id}/configs/{malformed[2].config_group_id}/history"
        )

        self.assert_not_found(update, "CONFIG_NOT_FOUND")
        self.assert_not_found(delete, "CONFIG_NOT_FOUND")
        self.assert_not_found(history, "CONFIG_NOT_FOUND")

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
