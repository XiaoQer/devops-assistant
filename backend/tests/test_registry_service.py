import unittest

from app import create_app
from app.extensions import db
from app.models import ContainerRegistry
from app.services.registry_service import RegistryService


class TestConfig:
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
    TEKTON_NAMESPACE = "tekton"
    DEFAULT_IMAGE_REGISTRY = "registry.local"
    AUTO_CREATE_SCHEMA = True
    SECRET_KEY = "registry-test-secret"
    TESTING = True


class RegistryServiceTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.context = self.app.app_context()
        self.context.push()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    def test_default_registry_and_encrypted_credentials(self):
        service = RegistryService()
        item = service.create({
            "name": "Company ACR",
            "provider": "acr",
            "server": "https://company.azurecr.io/",
            "namespace": "platform",
            "username": "client-id",
            "password": "client-secret",
        })

        self.assertTrue(item.is_default)
        self.assertEqual(item.image_prefix, "company.azurecr.io/platform")
        self.assertNotEqual(item.encrypted_password, "client-secret")
        self.assertEqual(service.credentials(item)["password"], "client-secret")
        serialized = item.to_dict()
        self.assertFalse(serialized["skip_tls_verify"])
        self.assertEqual(serialized["connection_status"], "untested")
        self.assertIsNone(serialized["last_checked_at"])
        self.assertIsNone(serialized["last_connection_message"])
        self.assertNotIn("encrypted_password", serialized)

    def test_only_one_registry_can_be_default(self):
        service = RegistryService()
        first = service.create({
            "name": "Primary",
            "provider": "acr",
            "server": "primary.azurecr.io",
        })
        second = service.create({
            "name": "Secondary",
            "provider": "harbor",
            "server": "harbor.example.com",
        })

        service.set_default(second)

        self.assertFalse(db.session.get(ContainerRegistry, first.id).is_default)
        self.assertTrue(db.session.get(ContainerRegistry, second.id).is_default)


if __name__ == "__main__":
    unittest.main()
