import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app import create_app
from app.services.cluster_credential_materializer import ClusterCredentialMaterializer
from app.services.configuration_service import ConfigurationService


class TestConfig:
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    AUTO_CREATE_SCHEMA = True
    SECRET_KEY = "credential-materializer-test-secret"
    TEKTON_NAMESPACE = "tekton"
    DEFAULT_IMAGE_REGISTRY = "registry.local"
    TESTING = True


class ClusterCredentialMaterializerTest(unittest.TestCase):
    def setUp(self):
        self.app_context = create_app(TestConfig).app_context()
        self.app_context.push()
        self.project = SimpleNamespace(id=12)
        self.cluster = SimpleNamespace(id=34, kube_context="prod")
        self.central = Mock()

    def tearDown(self):
        self.app_context.pop()

    @patch(
        "app.services.cluster_credential_materializer.KubernetesClusterService.credentials",
        return_value=("apiVersion: v1\nusers: []", "prod"),
    )
    def test_materializes_deterministic_safe_central_secret(self, credentials):
        name = ClusterCredentialMaterializer().materialize(
            self.project, self.cluster, self.central
        )

        self.assertEqual(name, "aegis-kubeconfig-p12-c34")
        credentials.assert_called_once_with(self.cluster)
        self.central.ensure_namespace.assert_called_once_with("tekton")
        self.central.apply_secret.assert_called_once_with(
            name,
            "tekton",
            {"config": "apiVersion: v1\nusers: []"},
            labels={
                "app.kubernetes.io/managed-by": "aegis",
                "aegis.dev/project-id": "12",
                "aegis.dev/cluster-id": "34",
            },
        )
        self.assertNotIn("apiVersion", name)

    def test_deletes_deterministic_secret(self):
        ClusterCredentialMaterializer().delete(
            self.project, self.cluster, self.central
        )

        self.central.delete_secret.assert_called_once_with(
            "aegis-kubeconfig-p12-c34", "tekton"
        )


class ConfigurationClientSeparationTest(unittest.TestCase):
    def setUp(self):
        self.app_context = create_app(TestConfig).app_context()
        self.app_context.push()
        self.service = ConfigurationService()
        self.application = SimpleNamespace(id=1, name="payments-api")
        self.environment = SimpleNamespace(id=2, namespace="payments-prod")
        self.registry = SimpleNamespace(id=3)
        self.target = Mock()
        self.central = Mock()
        self.credentials = {
            "server": "ghcr.io",
            "username": "robot",
            "password": "test-token",
            "email": "",
            "secret_name": "payments-registry",
        }

    def tearDown(self):
        self.app_context.pop()

    @patch("app.services.configuration_service.RegistryService.credentials")
    @patch.object(ConfigurationService, "list", return_value=[])
    def test_target_materialization_never_writes_tekton_namespace(
        self, _list, credentials
    ):
        credentials.return_value = self.credentials

        resources = self.service.materialize(
            self.application,
            self.environment,
            self.target,
            registry=self.registry,
        )

        self.assertEqual(resources["registry_secret_name"], "payments-registry")
        namespaces = [call.args[1] for call in self.target.apply_secret.call_args_list]
        registry_namespaces = [
            call.args[1] for call in self.target.apply_registry_secret.call_args_list
        ]
        self.assertNotIn("tekton", namespaces + registry_namespaces)
        self.target.apply_registry_secret.assert_called_once()
        self.central.assert_not_called()

    @patch("app.services.configuration_service.RegistryService.credentials")
    def test_build_registry_materialization_writes_only_central_namespace(
        self, credentials
    ):
        credentials.return_value = self.credentials

        name = self.service.materialize_build_registry(
            self.registry, self.central, "tekton"
        )

        self.assertEqual(name, "payments-registry")
        self.central.ensure_namespace.assert_called_once_with("tekton")
        self.central.apply_registry_secret.assert_called_once_with(
            "payments-registry",
            "tekton",
            "ghcr.io",
            "robot",
            "test-token",
            "",
        )
        self.target.assert_not_called()


if __name__ == "__main__":
    unittest.main()
