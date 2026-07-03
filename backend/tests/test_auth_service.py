import unittest
from datetime import datetime, timedelta, timezone

from app import create_app
from app.extensions import db
from app.models import User, UserSession
from sqlalchemy import inspect


class TestConfig:
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
    TEKTON_NAMESPACE = "tekton"
    DEFAULT_IMAGE_REGISTRY = "registry.local"
    AUTO_CREATE_SCHEMA = True
    SECRET_KEY = "auth-model-test-secret"
    TESTING = True


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
        user = User(username="admin", display_name="Administrator")
        user.set_password("correct horse battery staple")
        user.sessions.append(UserSession(
            token_digest="a" * 64,
            csrf_digest="b" * 64,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=8),
        ))
        db.session.add(user)
        db.session.commit()

        db.session.delete(user)
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


if __name__ == "__main__":
    unittest.main()
