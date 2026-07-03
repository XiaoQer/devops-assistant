import unittest
from unittest.mock import patch

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
        with patch("click.prompt") as prompt:
            result = self.runner.invoke(args=["create-admin"], env=environment)
        prompt.assert_not_called()
        return result

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


if __name__ == "__main__":
    unittest.main()
