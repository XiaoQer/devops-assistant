import ssl
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from kubernetes.client.exceptions import ApiException

from app import create_app
from app.extensions import db
from app.models import (
    Application,
    ApplicationEnvironment,
    KubernetesCluster,
    Project,
)
from app.services.cluster_credential_materializer import ClusterCredentialMaterializer
from app.services.kubernetes_cluster_service import KubernetesClusterService
from app.services.kubernetes_service import KubernetesService
from app.utils.errors import ApiError


VALID_KUBECONFIG = """
apiVersion: v1
kind: Config
current-context: dev
clusters:
  - name: dev-cluster
    cluster:
      server: https://kubernetes.example.test
      certificate-authority-data: dGVzdA==
users:
  - name: dev-user
    user:
      token: test-token-not-a-real-secret
contexts:
  - name: dev
    context:
      cluster: dev-cluster
      user: dev-user
"""

REPLACEMENT_KUBECONFIG = VALID_KUBECONFIG.replace(
    "kubernetes.example.test", "replacement.example.test"
).replace("test-token-not-a-real-secret", "replacement-token")


class TestConfig:
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    AUTO_CREATE_SCHEMA = True
    SECRET_KEY = "kubernetes-cluster-service-test-secret"
    TEKTON_NAMESPACE = "tekton"
    DEFAULT_IMAGE_REGISTRY = "registry.local"
    TESTING = True


class KubernetesClusterServiceTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.context = self.app.app_context()
        self.context.push()
        self.project = Project(key="payments", name="Payments")
        db.session.add(self.project)
        db.session.commit()
        self.service = KubernetesClusterService()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    def payload(self, **overrides):
        return {
            "name": "payments-dev",
            "environment_label": "development",
            "kubeconfig": VALID_KUBECONFIG,
            "kube_context": "dev",
            **overrides,
        }

    def test_create_encrypts_kubeconfig_and_serializes_only_safe_metadata(self):
        cluster = self.service.create(
            self.project,
            self.payload(api_server="https://spoofed.example.test"),
        )

        self.assertNotEqual(cluster.encrypted_kubeconfig, VALID_KUBECONFIG)
        self.assertEqual(self.service.credentials(cluster), (VALID_KUBECONFIG, "dev"))
        self.assertIsNone(cluster.api_server)
        self.assertTrue(cluster.to_dict()["has_kubeconfig"])
        self.assertNotIn("encrypted_kubeconfig", cluster.to_dict())
        self.assertNotIn("kubeconfig", cluster.to_dict())

    def test_blank_update_preserves_credentials_and_replacement_resets_status(self):
        cluster = self.service.create(self.project, self.payload())
        original_ciphertext = cluster.encrypted_kubeconfig
        cluster.connection_status = "connected"
        cluster.kubernetes_version = "v1.30.0"
        db.session.commit()

        preserved = self.service.update(cluster, {
            "description": "preserved",
            "kubeconfig": "",
        })
        self.assertEqual(preserved.encrypted_kubeconfig, original_ciphertext)
        self.assertEqual(preserved.connection_status, "connected")

        replaced = self.service.update(cluster, {
            "kubeconfig": REPLACEMENT_KUBECONFIG,
            "kube_context": "dev",
            "environment_label": "performance",
        })
        self.assertNotEqual(replaced.encrypted_kubeconfig, original_ciphertext)
        self.assertEqual(replaced.connection_status, "untested")
        self.assertIsNone(replaced.kubernetes_version)
        self.assertEqual(replaced.environment_label, "performance")

    def test_rejects_invalid_or_unsafe_kubeconfig(self):
        unsafe_values = {
            "oversized": "x" * (1024 * 1024 + 1),
            "missing-context": VALID_KUBECONFIG.replace("name: dev\n    context:", "name: other\n    context:"),
            "http-server": VALID_KUBECONFIG.replace("https://", "http://"),
            "exec-auth": VALID_KUBECONFIG.replace(
                "token: test-token-not-a-real-secret",
                "exec:\n        command: steal-secrets",
            ),
            "certificate-file": VALID_KUBECONFIG.replace(
                "token: test-token-not-a-real-secret",
                "client-certificate: /etc/passwd",
            ),
            "key-file": VALID_KUBECONFIG.replace(
                "token: test-token-not-a-real-secret",
                "client-key: /etc/passwd",
            ),
            "token-file": VALID_KUBECONFIG.replace(
                "token: test-token-not-a-real-secret",
                "tokenFile: /etc/passwd",
            ),
            "ca-file": VALID_KUBECONFIG.replace(
                "certificate-authority-data: dGVzdA==",
                "certificate-authority: /etc/passwd",
            ),
        }

        for name, kubeconfig in unsafe_values.items():
            with self.subTest(name=name), self.assertRaises(ApiError) as raised:
                self.service.create(
                    self.project,
                    self.payload(name=f"cluster-{name}", kubeconfig=kubeconfig),
                )
            self.assertEqual(raised.exception.status_code, 400)
            self.assertNotIn("/etc/passwd", raised.exception.message)
            self.assertNotIn("steal-secrets", raised.exception.message)

    def test_rejects_missing_environment_label(self):
        with self.assertRaises(ApiError) as raised:
            self.service.create(self.project, self.payload(environment_label=""))

        self.assertEqual(raised.exception.code, "CLUSTER_ENVIRONMENT_LABEL_REQUIRED")

    @patch.object(KubernetesService, "from_kubeconfig")
    def test_transient_connection_success_returns_safe_metadata(self, from_kubeconfig):
        adapter = Mock()
        adapter.version.return_value = {
            "server": "https://kubernetes.example.test",
            "version": "v1.31.2",
        }
        from_kubeconfig.return_value = adapter

        result = self.service.test_connection(VALID_KUBECONFIG, "dev")

        self.assertEqual(result, {
            "connected": True,
            "message": "Kubernetes API 连接成功",
            "api_server": "https://kubernetes.example.test",
            "kubernetes_version": "v1.31.2",
        })

    @patch.object(KubernetesService, "from_kubeconfig")
    def test_connection_failures_are_safely_classified(self, from_kubeconfig):
        failures = [
            (ApiException(status=401, reason="leaked-token"), "Kubernetes 认证失败"),
            (ssl.SSLCertVerificationError("leaked-certificate"), "Kubernetes 证书校验失败"),
            (TimeoutError("leaked-timeout"), "Kubernetes 连接超时"),
            (OSError("leaked-network"), "Kubernetes 网络不可达"),
        ]

        for failure, expected_message in failures:
            with self.subTest(expected_message=expected_message):
                adapter = Mock()
                adapter.version.side_effect = failure
                from_kubeconfig.return_value = adapter

                result = self.service.test_connection(VALID_KUBECONFIG, "dev")

                self.assertFalse(result["connected"])
                self.assertEqual(result["message"], expected_message)
                self.assertNotIn("leaked", str(result))
                self.assertNotIn("test-token-not-a-real-secret", str(result))

    @patch.object(KubernetesClusterService, "test_connection")
    def test_saved_connection_persists_only_summary(self, test_connection):
        cluster = self.service.create(self.project, self.payload())
        test_connection.return_value = {
            "connected": True,
            "message": "Kubernetes API 连接成功",
            "api_server": "https://kubernetes.example.test",
            "kubernetes_version": "v1.31.2",
        }

        result = self.service.test_saved_connection(cluster)

        self.assertTrue(result["connected"])
        self.assertEqual(cluster.connection_status, "connected")
        self.assertIsNotNone(cluster.last_checked_at)
        self.assertEqual(cluster.kubernetes_version, "v1.31.2")
        self.assertEqual(cluster.api_server, "https://kubernetes.example.test")

        test_connection.return_value = {
            "connected": False,
            "message": "Kubernetes 网络不可达",
        }
        self.service.test_saved_connection(cluster)
        self.assertEqual(cluster.connection_status, "failed")
        self.assertIsNone(cluster.kubernetes_version)

    @patch.object(KubernetesService, "from_kubeconfig")
    def test_builds_target_client_from_decrypted_document(self, from_kubeconfig):
        cluster = self.service.create(self.project, self.payload())
        target = Mock()
        from_kubeconfig.return_value = target

        result = self.service.client(cluster)

        self.assertIs(result, target)
        document, context = from_kubeconfig.call_args.args
        self.assertEqual(document["current-context"], "dev")
        self.assertEqual(context, "dev")

    @patch.object(ClusterCredentialMaterializer, "delete")
    def test_delete_rejects_cluster_bound_to_environment_before_cleanup(
        self, cleanup
    ):
        cluster = self.service.create(self.project, self.payload())
        application = Application(
            project_id=self.project.id,
            name="payments-api",
            repo_url="https://example.test/payments.git",
        )
        db.session.add(application)
        db.session.flush()
        db.session.add(
            ApplicationEnvironment(
                application_id=application.id,
                kubernetes_cluster_id=cluster.id,
                environment_name="production",
                namespace="payments-prod",
            )
        )
        db.session.commit()

        with self.assertRaises(ApiError) as raised:
            self.service.delete(cluster, Mock())

        self.assertEqual(raised.exception.code, "CLUSTER_IN_USE")
        cleanup.assert_not_called()
        self.assertIsNotNone(db.session.get(KubernetesCluster, cluster.id))

    @patch.object(ClusterCredentialMaterializer, "delete")
    def test_delete_cleans_central_secret_before_database_record(self, cleanup):
        cluster = self.service.create(self.project, self.payload())
        cluster_id = cluster.id
        central = Mock()

        self.service.delete(cluster, central)

        cleanup.assert_called_once_with(self.project, cluster, central)
        self.assertIsNone(db.session.get(KubernetesCluster, cluster_id))

    @patch.object(ClusterCredentialMaterializer, "delete")
    def test_delete_cleanup_failure_is_sanitized_and_preserves_record(self, cleanup):
        cluster = self.service.create(self.project, self.payload())
        cluster_id = cluster.id
        cleanup.side_effect = RuntimeError("leaked central endpoint and credentials")

        with self.assertRaises(ApiError) as raised:
            self.service.delete(cluster, Mock())

        self.assertEqual(raised.exception.code, "CLUSTER_CREDENTIAL_CLEANUP_FAILED")
        self.assertNotIn("leaked", raised.exception.message)
        self.assertIsNotNone(db.session.get(KubernetesCluster, cluster_id))


class KubernetesServiceKubeconfigTest(unittest.TestCase):
    @patch("app.services.kubernetes_service.client.VersionApi")
    @patch("app.services.kubernetes_service.client.CustomObjectsApi")
    @patch("app.services.kubernetes_service.client.NetworkingV1Api")
    @patch("app.services.kubernetes_service.client.AppsV1Api")
    @patch("app.services.kubernetes_service.client.CoreV1Api")
    @patch("app.services.kubernetes_service.config.load_kube_config_from_dict")
    def test_builds_complete_isolated_client(
        self,
        load_config,
        core_api,
        apps_api,
        networking_api,
        custom_api,
        version_api,
    ):
        version_api.return_value.get_code.return_value = SimpleNamespace(git_version="v1.31.2")
        document = {"apiVersion": "v1"}

        service = KubernetesService.from_kubeconfig(document, "dev")
        service.api_client.configuration.host = "https://kubernetes.example.test"
        result = service.version()

        load_config.assert_called_once()
        self.assertEqual(load_config.call_args.kwargs["context"], "dev")
        self.assertFalse(load_config.call_args.kwargs["persist_config"])
        self.assertIs(service.core_api, core_api.return_value)
        self.assertIs(service.apps_api, apps_api.return_value)
        self.assertIs(service.networking_api, networking_api.return_value)
        self.assertIs(service.custom_api, custom_api.return_value)
        self.assertIs(service.version_api, version_api.return_value)
        version_api.return_value.get_code.assert_called_once_with(_request_timeout=5)
        self.assertEqual(result, {
            "server": "https://kubernetes.example.test",
            "version": "v1.31.2",
        })


if __name__ == "__main__":
    unittest.main()
