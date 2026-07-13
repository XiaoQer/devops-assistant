import unittest
from unittest.mock import patch

from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.orm import Query

from app import create_app
from app.extensions import db
from app.models import User


class TestConfig:
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    AUTO_CREATE_SCHEMA = True
    SECRET_KEY = "admin-cli-test-secret"
    TESTING = True


class CreateAdminCliTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.context = self.app.app_context()
        self.context.push()
        self.runner = self.app.test_cli_runner()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    def invoke(self, **overrides):
        environment = {
            "AEGIS_ADMIN_USERNAME": "  platform-admin  ",
            "AEGIS_ADMIN_DISPLAY_NAME": "  Platform Administrator  ",
            "AEGIS_ADMIN_PASSWORD": "safe-password-value",
        }
        environment.update(overrides)
        with (
            patch("builtins.input", side_effect=AssertionError("stdin used")),
            patch("getpass.getpass", side_effect=AssertionError("getpass used")),
            patch("click.prompt", side_effect=AssertionError("prompt used")),
        ):
            result = self.runner.invoke(args=["create-admin"], env=environment)
        return result

    def assert_secret_absent(self, result, *secrets):
        rendered = "\n".join(
            (
                result.output,
                getattr(result, "stdout", ""),
                getattr(result, "stderr", ""),
                str(result.exception),
            )
        )
        for secret in secrets:
            self.assertNotIn(secret, rendered)

    def test_create_admin_hashes_password_and_prints_only_safe_confirmation(self):
        result = self.invoke()

        self.assertEqual(result.exit_code, 0, result.output)
        user = User.query.one()
        self.assertEqual(user.username, "platform-admin")
        self.assertEqual(user.display_name, "Platform Administrator")
        self.assertTrue(user.check_password("safe-password-value"))
        self.assertNotEqual(user.password_hash, "safe-password-value")
        self.assertIn("platform-admin", result.output)
        self.assertNotIn("safe-password-value", result.output)
        self.assertNotIn(user.password_hash, result.output)

    def test_create_admin_requires_every_environment_variable(self):
        for variable in (
            "AEGIS_ADMIN_USERNAME",
            "AEGIS_ADMIN_DISPLAY_NAME",
            "AEGIS_ADMIN_PASSWORD",
        ):
            with self.subTest(variable=variable):
                result = self.invoke(**{variable: ""})

                self.assertNotEqual(result.exit_code, 0)
                self.assertEqual(User.query.count(), 0)

    def test_create_admin_rejects_password_shorter_than_twelve_characters(self):
        result = self.invoke(AEGIS_ADMIN_PASSWORD="short-pass")

        self.assertNotEqual(result.exit_code, 0)
        self.assertEqual(User.query.count(), 0)
        self.assertNotIn("short-pass", result.output)

    def test_create_admin_rejects_oversized_fields_and_blank_password_without_hashing(self):
        cases = (
            {"AEGIS_ADMIN_USERNAME": "u" * 121},
            {"AEGIS_ADMIN_DISPLAY_NAME": "d" * 121},
            {"AEGIS_ADMIN_PASSWORD": "p" * 4097},
            {"AEGIS_ADMIN_PASSWORD": " " * 12},
        )
        with patch.object(User, "set_password") as set_password:
            for overrides in cases:
                with self.subTest(field=next(iter(overrides))):
                    result = self.invoke(**overrides)

                    self.assertNotEqual(result.exit_code, 0)
                    self.assertEqual(User.query.count(), 0)
                    self.assert_secret_absent(result, next(iter(overrides.values())))

        set_password.assert_not_called()

    def test_create_admin_rejects_existing_username_without_changing_password(self):
        existing = User(
            username="platform-admin",
            display_name="Original Administrator",
        )
        existing.set_password("original-password")
        db.session.add(existing)
        db.session.commit()
        original_hash = existing.password_hash

        result = self.invoke(AEGIS_ADMIN_PASSWORD="replacement-password")

        self.assertNotEqual(result.exit_code, 0)
        db.session.refresh(existing)
        self.assertEqual(existing.display_name, "Original Administrator")
        self.assertEqual(existing.password_hash, original_hash)
        self.assertTrue(existing.check_password("original-password"))
        self.assertFalse(existing.check_password("replacement-password"))
        self.assertNotIn("replacement-password", result.output)

    def test_create_admin_rolls_back_integrity_error_without_leaking_database_details(self):
        password = "race-password-value"
        sensitive_hash = "scrypt:sensitive-password-hash"
        sensitive_params = "username=platform-admin,password_hash=sensitive"
        error = IntegrityError(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            sensitive_params,
            Exception(sensitive_hash),
        )

        with (
            patch.object(db.session, "commit", side_effect=error),
            patch.object(db.session, "rollback", wraps=db.session.rollback) as rollback,
        ):
            result = self.invoke(AEGIS_ADMIN_PASSWORD=password)

        self.assertNotEqual(result.exit_code, 0)
        rollback.assert_called_once_with()
        self.assert_secret_absent(
            result,
            password,
            sensitive_hash,
            sensitive_params,
            "INSERT INTO users",
        )
        self.assertEqual(User.query.count(), 0)

    def test_create_admin_rolls_back_other_database_errors_with_safe_message(self):
        password = "database-password-value"
        sensitive_detail = "connection failed with password=database-password-value"
        error = SQLAlchemyError(sensitive_detail)

        with (
            patch.object(db.session, "commit", side_effect=error),
            patch.object(db.session, "rollback", wraps=db.session.rollback) as rollback,
        ):
            result = self.invoke(AEGIS_ADMIN_PASSWORD=password)

        self.assertNotEqual(result.exit_code, 0)
        rollback.assert_called_once_with()
        self.assert_secret_absent(result, password, sensitive_detail)
        self.assertEqual(User.query.count(), 0)

    def test_create_admin_safely_handles_database_error_during_username_lookup(self):
        password = "lookup-password-value"
        sensitive_sql = "SELECT * FROM users WHERE password_hash=:secret"
        sensitive_params = {"secret": password}
        error = OperationalError(
            sensitive_sql,
            sensitive_params,
            Exception("database-password=lookup-password-value"),
        )

        with (
            patch.object(Query, "first", side_effect=error),
            patch.object(db.session, "rollback", wraps=db.session.rollback) as rollback,
        ):
            result = self.invoke(AEGIS_ADMIN_PASSWORD=password)

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("failed to create admin", result.output)
        rollback.assert_called_once_with()
        self.assert_secret_absent(
            result,
            password,
            sensitive_sql,
            str(sensitive_params),
            "database-password",
        )
        self.assertEqual(User.query.count(), 0)


if __name__ == "__main__":
    unittest.main()
