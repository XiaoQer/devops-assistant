import hashlib
import importlib
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import app.config as config_module
from app import create_app
from app.extensions import db
from app.models import User, UserSession
from app.services.auth_service import AuthService
from app.utils.errors import ApiError
from sqlalchemy import delete, inspect, text


class TestConfig:
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
    TEKTON_NAMESPACE = "tekton"
    DEFAULT_IMAGE_REGISTRY = "registry.local"
    AUTO_CREATE_SCHEMA = True
    SECRET_KEY = "auth-model-test-secret"
    TESTING = True
    AUTH_SESSION_HOURS = 13


class AuthModelTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.context = self.app.app_context()
        self.context.push()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    def test_user_hashes_password_and_does_not_serialize_hash(self):
        user = User(username="admin", display_name="Administrator")

        user.set_password("correct horse battery staple")
        db.session.add(user)
        db.session.flush()

        self.assertNotEqual(user.password_hash, "correct horse battery staple")
        self.assertTrue(user.check_password("correct horse battery staple"))
        self.assertFalse(user.check_password("wrong password"))
        self.assertEqual(
            user.to_dict(),
            {
                "id": user.id,
                "username": "admin",
                "display_name": "Administrator",
                "is_active": True,
            },
        )
        self.assertNotIn("password_hash", user.to_dict())

    def test_deleting_user_cascades_to_sessions(self):
        db.session.execute(text("PRAGMA foreign_keys=ON"))
        user = User(username="admin", display_name="Administrator")
        user.set_password("correct horse battery staple")
        user.sessions.append(UserSession(
            token_digest="a" * 64,
            csrf_digest="b" * 64,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=8),
        ))
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        db.session.expunge_all()

        db.session.execute(delete(User).where(User.id == user_id))
        db.session.commit()

        self.assertEqual(UserSession.query.count(), 0)

    def test_unique_fields_do_not_create_redundant_indexes(self):
        inspector = inspect(db.engine)

        self.assertEqual(
            {item["column_names"][0] for item in inspector.get_unique_constraints("users")},
            {"username"},
        )
        self.assertNotIn(
            "username",
            {
                column
                for item in inspector.get_indexes("users")
                for column in item["column_names"]
            },
        )
        self.assertEqual(
            {
                item["column_names"][0]
                for item in inspector.get_unique_constraints("user_sessions")
            },
            {"token_digest"},
        )
        self.assertNotIn(
            "token_digest",
            {
                column
                for item in inspector.get_indexes("user_sessions")
                for column in item["column_names"]
            },
        )


class AuthServiceTest(unittest.TestCase):
    password = "correct-horse-battery-staple"

    def setUp(self):
        self.app = create_app(TestConfig)
        self.context = self.app.app_context()
        self.context.push()
        self.user = User(
            username="admin",
            display_name="Administrator",
            is_active=True,
        )
        self.user.set_password(self.password)
        db.session.add(self.user)
        db.session.commit()
        self.service = AuthService()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    def assert_invalid_credentials(self, username, password):
        with self.assertRaises(ApiError) as raised:
            self.service.login(username, password)

        self.assertEqual(raised.exception.status_code, 401)
        self.assertEqual(raised.exception.code, "INVALID_CREDENTIALS")
        self.assertEqual(raised.exception.message, "用户名或密码错误")

    def assert_authentication_required(self, token):
        with self.assertRaises(ApiError) as raised:
            self.service.resolve(token)

        self.assertEqual(raised.exception.status_code, 401)
        self.assertEqual(raised.exception.code, "AUTHENTICATION_REQUIRED")

    def test_digest_uses_sha256_hex_digest(self):
        token = "known-session-token"

        self.assertEqual(
            AuthService.digest(token),
            hashlib.sha256(token.encode("utf-8")).hexdigest(),
        )

    def test_login_creates_session_with_only_token_digests(self):
        before_login = datetime.now(timezone.utc)
        with patch(
            "app.services.auth_service.secrets.token_urlsafe",
            side_effect=["raw-session-token", "raw-csrf-token"],
        ) as token_urlsafe:
            result = self.service.login("admin", self.password)
        after_login = datetime.now(timezone.utc)

        self.assertEqual(result.user.id, self.user.id)
        self.assertEqual(result.session.user_id, self.user.id)
        self.assertEqual(UserSession.query.count(), 1)
        self.assertEqual(
            [item.args for item in token_urlsafe.call_args_list],
            [(32,), (32,)],
        )
        self.assertEqual(result.session_token, "raw-session-token")
        self.assertEqual(result.csrf_token, "raw-csrf-token")
        self.assertEqual(
            result.session.token_digest,
            AuthService.digest("raw-session-token"),
        )
        self.assertEqual(
            result.session.csrf_digest,
            AuthService.digest("raw-csrf-token"),
        )
        self.assertEqual(len(result.session.token_digest), 64)
        self.assertEqual(len(result.session.csrf_digest), 64)
        expires_at = result.session.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        self.assertGreaterEqual(expires_at, before_login + timedelta(hours=13))
        self.assertLessEqual(expires_at, after_login + timedelta(hours=13))

    def test_login_rejects_wrong_username_password_and_disabled_user_identically(self):
        self.assert_invalid_credentials("missing", self.password)
        self.assert_invalid_credentials("admin", "wrong-password")
        self.user.is_active = False
        db.session.commit()
        self.assert_invalid_credentials("admin", self.password)

    def test_resolve_returns_valid_session_and_user(self):
        result = self.service.login("admin", self.password)

        resolved = self.service.resolve(result.session_token)

        self.assertEqual(resolved.id, result.session.id)
        self.assertEqual(resolved.user.id, self.user.id)

    def test_resolve_rejects_empty_and_unknown_tokens(self):
        self.assert_authentication_required("")
        self.assert_authentication_required("unknown-token")

    def test_resolve_rejects_expired_revoked_and_disabled_sessions(self):
        expired = self.service.login("admin", self.password)
        expired.session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.session.commit()
        self.assert_authentication_required(expired.session_token)

        revoked = self.service.login("admin", self.password)
        revoked.session.revoked_at = datetime.now(timezone.utc)
        db.session.commit()
        self.assert_authentication_required(revoked.session_token)

        disabled = self.service.login("admin", self.password)
        self.user.is_active = False
        db.session.commit()
        self.assert_authentication_required(disabled.session_token)

    def test_verify_csrf_hashes_candidate_and_uses_constant_time_comparison(self):
        result = self.service.login("admin", self.password)

        with patch(
            "app.services.auth_service.secrets.compare_digest",
            wraps=__import__("secrets").compare_digest,
        ) as compare_digest:
            self.assertTrue(
                self.service.verify_csrf(result.session, result.csrf_token)
            )
            self.assertFalse(self.service.verify_csrf(result.session, "wrong-token"))

        self.assertEqual(compare_digest.call_count, 2)
        self.assertEqual(
            compare_digest.call_args_list[0].args,
            (result.session.csrf_digest, AuthService.digest(result.csrf_token)),
        )
        self.assertFalse(self.service.verify_csrf(result.session, ""))

    def test_revoke_persists_revoked_timestamp(self):
        result = self.service.login("admin", self.password)

        self.service.revoke(result.session)
        db.session.expire_all()
        persisted = db.session.get(UserSession, result.session.id)

        self.assertIsNotNone(persisted.revoked_at)


class AuthConfigTest(unittest.TestCase):
    def tearDown(self):
        importlib.reload(config_module)

    def test_auth_config_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            config = importlib.reload(config_module).Config

            self.assertEqual(config.AUTH_SESSION_HOURS, 8)
            self.assertEqual(config.AUTH_COOKIE_NAME, "aegis_session")
            self.assertEqual(config.AUTH_CSRF_COOKIE_NAME, "aegis_csrf")
            self.assertFalse(config.AUTH_COOKIE_SECURE)
            self.assertEqual(config.CORS_ORIGINS, ["http://localhost:5173"])

    def test_auth_config_parses_environment_values(self):
        environment = {
            "AUTH_SESSION_HOURS": "12",
            "AUTH_COOKIE_NAME": "custom_session",
            "AUTH_CSRF_COOKIE_NAME": "custom_csrf",
            "AUTH_COOKIE_SECURE": "TrUe",
            "CORS_ORIGINS": " https://one.example,https://two.example , ",
        }
        with patch.dict(os.environ, environment, clear=True):
            config = importlib.reload(config_module).Config

            self.assertEqual(config.AUTH_SESSION_HOURS, 12)
            self.assertEqual(config.AUTH_COOKIE_NAME, "custom_session")
            self.assertEqual(config.AUTH_CSRF_COOKIE_NAME, "custom_csrf")
            self.assertTrue(config.AUTH_COOKIE_SECURE)
            self.assertEqual(
                config.CORS_ORIGINS,
                ["https://one.example", "https://two.example"],
            )


if __name__ == "__main__":
    unittest.main()
