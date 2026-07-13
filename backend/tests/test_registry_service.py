import unittest
from datetime import datetime, timezone

from app import create_app
from app.extensions import db
from app.models import ContainerRegistry, Project
from app.services.registry_service import RegistryService
from app.utils.errors import ApiError


class TestConfig:
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
    TEKTON_NAMESPACE = "tekton"
    DEFAULT_IMAGE_REGISTRY = "registry.local"
    AUTO_CREATE_SCHEMA = True
    SECRET_KEY = "registry-test-secret"
    TESTING = True


class FakeConnectivityClient:
    def __init__(self, result=None):
        self.result = result or {
            "connected": True,
            "message": "Registry 连接与认证成功",
            "tls_verified": True,
            "auth_method": "bearer",
        }
        self.calls = []

    def test(self, server, username, token, skip_tls_verify=False):
        self.calls.append({
            "server": server,
            "username": username,
            "token": token,
            "skip_tls_verify": skip_tls_verify,
        })
        return dict(self.result)


class RegistryServiceTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.context = self.app.app_context()
        self.context.push()
        self.project = Project(key="payments", name="Payments")
        self.other_project = Project(key="platform", name="Platform")
        db.session.add_all([self.project, self.other_project])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    @staticmethod
    def payload(name="Company ACR", **overrides):
        values = {
            "name": name,
            "provider": "acr",
            "server": "https://company.azurecr.io/",
            "namespace": "platform",
            "username": "client-id",
            "password": "client-secret",
        }
        values.update(overrides)
        return values

    def test_default_registry_and_encrypted_credentials(self):
        service = RegistryService()
        item = service.create(self.project, self.payload())

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
        self.assertNotIn("password", serialized)
        self.assertNotIn("client-secret", str(serialized))

    def test_only_one_registry_can_be_default_inside_project(self):
        service = RegistryService()
        first = service.create(self.project, self.payload("Primary"))
        second = service.create(self.project, self.payload(
            "Secondary",
            provider="harbor",
            server="harbor.example.com",
        ))
        other = service.create(self.other_project, self.payload("Other"))

        service.set_default(second)

        self.assertFalse(db.session.get(ContainerRegistry, first.id).is_default)
        self.assertTrue(db.session.get(ContainerRegistry, second.id).is_default)
        self.assertTrue(db.session.get(ContainerRegistry, other.id).is_default)

    def test_list_and_get_are_project_scoped(self):
        service = RegistryService()
        item = service.create(self.project, self.payload())
        service.create(self.other_project, self.payload())

        self.assertEqual(service.list(self.project), [item])
        self.assertEqual(service.get(self.project, item.id), item)
        with self.assertRaises(ApiError) as error:
            service.get(self.other_project, item.id)
        self.assertEqual(error.exception.code, "REGISTRY_NOT_FOUND")
        self.assertEqual(error.exception.status_code, 404)

    def test_create_requires_credentials_and_accepts_ghcr(self):
        service = RegistryService()
        for field in ("username", "password"):
            with self.subTest(field=field):
                payload = self.payload(**{field: ""})
                with self.assertRaises(ApiError):
                    service.create(self.project, payload)

        item = service.create(self.project, self.payload(
            provider="ghcr",
            server="ghcr.io",
            username="octocat",
            password="github-pat",
        ))
        self.assertEqual(item.provider, "ghcr")

    def test_http_registry_is_rejected_instead_of_silently_upgraded(self):
        service = RegistryService(FakeConnectivityClient())

        with self.assertRaises(ApiError) as create_error:
            service.create(self.project, self.payload(
                server="http://harbor.example.test"
            ))
        self.assertEqual(create_error.exception.code, "REGISTRY_SERVER_INVALID")

        with self.assertRaises(ApiError) as test_error:
            service.test_connection({
                "server": "http://harbor.example.test",
                "username": "robot",
                "password": "client-secret",
            })
        self.assertEqual(test_error.exception.code, "REGISTRY_SERVER_INVALID")

        for server in (
            "harbor.example.test/team",
            "harbor.example.test?scope=admin",
        ):
            with self.subTest(server=server):
                with self.assertRaises(ApiError) as malformed_error:
                    service.test_connection({
                        "server": server,
                        "username": "robot",
                        "password": "client-secret",
                    })
                self.assertEqual(
                    malformed_error.exception.code,
                    "REGISTRY_SERVER_INVALID",
                )

    def test_skip_tls_verify_requires_a_json_boolean(self):
        service = RegistryService(FakeConnectivityClient())
        item = service.create(self.project, self.payload())

        for operation in (
            lambda: service.create(
                self.other_project,
                self.payload(skip_tls_verify="false"),
            ),
            lambda: service.update(item, {"skip_tls_verify": "false"}),
            lambda: service.test_connection({
                "server": "ghcr.io",
                "username": "octocat",
                "password": "github-pat",
                "skip_tls_verify": "false",
            }),
            lambda: service.test_connection(
                {"skip_tls_verify": "false"},
                current=item,
            ),
        ):
            with self.subTest(operation=operation):
                with self.assertRaises(ApiError) as error:
                    operation()
                self.assertEqual(
                    error.exception.code,
                    "REGISTRY_TLS_VERIFY_INVALID",
                )

    def test_update_keeps_existing_token_when_password_is_blank(self):
        service = RegistryService()
        item = service.create(self.project, self.payload())
        encrypted_password = item.encrypted_password

        service.update(item, {"name": "Renamed", "password": ""})

        self.assertEqual(item.encrypted_password, encrypted_password)
        self.assertEqual(service.credentials(item)["password"], "client-secret")

    def test_transient_connection_does_not_persist(self):
        connectivity = FakeConnectivityClient()
        service = RegistryService(connectivity)

        result = service.test_connection({
            "server": "ghcr.io",
            "username": "octocat",
            "password": "github-pat",
            "skip_tls_verify": False,
        })

        self.assertTrue(result["connected"])
        self.assertEqual(ContainerRegistry.query.count(), 0)
        self.assertEqual(connectivity.calls[0]["token"], "github-pat")

    def test_edit_connection_uses_saved_token_without_persisting_result(self):
        connectivity = FakeConnectivityClient()
        service = RegistryService(connectivity)
        item = service.create(self.project, self.payload())

        result = service.test_connection({
            "server": "new.azurecr.io",
            "username": "new-client",
            "password": "",
            "skip_tls_verify": True,
        }, current=item)

        self.assertTrue(result["connected"])
        self.assertEqual(connectivity.calls[0]["token"], "client-secret")
        self.assertEqual(connectivity.calls[0]["server"], "new.azurecr.io")
        self.assertTrue(connectivity.calls[0]["skip_tls_verify"])
        self.assertEqual(item.connection_status, "untested")
        self.assertIsNone(item.last_checked_at)

    def test_saved_connection_persists_safe_success_and_failure(self):
        connectivity = FakeConnectivityClient()
        service = RegistryService(connectivity)
        item = service.create(self.project, self.payload())

        result = service.test_saved_connection(item)

        self.assertTrue(result["connected"])
        self.assertEqual(item.connection_status, "connected")
        self.assertIsNotNone(item.last_checked_at)
        self.assertEqual(item.last_connection_message, result["message"])

        connectivity.result = {
            "connected": False,
            "message": "Registry 用户名或 Token 无效",
            "tls_verified": True,
            "failure_reason": "authentication_failed",
        }
        service.test_saved_connection(item)
        self.assertEqual(item.connection_status, "failed")
        self.assertEqual(
            item.last_connection_message,
            "Registry 用户名或 Token 无效",
        )

    def test_connection_field_updates_reset_saved_status(self):
        service = RegistryService()
        cases = [
            {"server": "new.azurecr.io"},
            {"username": "new-client"},
            {"password": "new-secret"},
            {"skip_tls_verify": True},
        ]
        for index, change in enumerate(cases):
            with self.subTest(change=change):
                item = service.create(self.project, self.payload(f"Registry {index}"))
                item.connection_status = "connected"
                item.last_checked_at = datetime.now(timezone.utc)
                item.last_connection_message = "Registry 连接与认证成功"
                db.session.commit()

                service.update(item, change)

                self.assertEqual(item.connection_status, "untested")
                self.assertIsNone(item.last_checked_at)
                self.assertIsNone(item.last_connection_message)

    def test_non_connection_updates_keep_saved_status(self):
        service = RegistryService()
        item = service.create(self.project, self.payload())
        checked_at = datetime.now(timezone.utc)
        item.connection_status = "connected"
        item.last_checked_at = checked_at
        item.last_connection_message = "Registry 连接与认证成功"
        db.session.commit()
        checked_at = item.last_checked_at

        service.update(item, {
            "name": "Renamed",
            "namespace": "new-team",
            "email": "platform@example.test",
            "pull_secret_name": "new-pull-secret",
            "is_active": False,
        })

        self.assertEqual(item.connection_status, "connected")
        self.assertEqual(item.last_checked_at, checked_at)
        self.assertEqual(
            item.last_connection_message,
            "Registry 连接与认证成功",
        )


if __name__ == "__main__":
    unittest.main()
