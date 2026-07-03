import tempfile
import unittest
from pathlib import Path

from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine, inspect

from app import create_app


BACKEND_DIR = Path(__file__).resolve().parents[1]


class TestConfig:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    AUTO_CREATE_SCHEMA = False
    SECRET_KEY = "auth-migration-test-secret"
    TEKTON_NAMESPACE = "tekton"
    DEFAULT_IMAGE_REGISTRY = "registry.local"


class AuthMigrationTest(unittest.TestCase):
    def test_upgrade_and_downgrade_authentication_tables(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "auth-migration.db"

            class DatabaseConfig(TestConfig):
                SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path}"

            app = create_app(DatabaseConfig)
            alembic_config = AlembicConfig(str(BACKEND_DIR / "migrations/alembic.ini"))
            alembic_config.set_main_option(
                "script_location",
                str(BACKEND_DIR / "migrations"),
            )

            with app.app_context():
                command.stamp(alembic_config, "f1a2b3c4d5e6")
                command.upgrade(alembic_config, "a7c8d9e0f1a2")

            engine = create_engine(DatabaseConfig.SQLALCHEMY_DATABASE_URI)
            inspector = inspect(engine)
            self.assertTrue({"users", "user_sessions"} <= set(inspector.get_table_names()))
            self.assertEqual(
                {
                    (constraint["name"], tuple(constraint["column_names"]))
                    for constraint in inspector.get_unique_constraints("users")
                },
                {("uq_users_username", ("username",))},
            )
            self.assertEqual(
                {
                    (constraint["name"], tuple(constraint["column_names"]))
                    for constraint in inspector.get_unique_constraints("user_sessions")
                },
                {("uq_user_sessions_token_digest", ("token_digest",))},
            )
            self.assertEqual(
                {
                    (index["name"], tuple(index["column_names"]))
                    for index in inspector.get_indexes("users")
                },
                {("ix_users_is_active", ("is_active",))},
            )
            self.assertEqual(
                {
                    (index["name"], tuple(index["column_names"]))
                    for index in inspector.get_indexes("user_sessions")
                },
                {
                    ("ix_user_sessions_user_id", ("user_id",)),
                    ("ix_user_sessions_expires_at", ("expires_at",)),
                    ("ix_user_sessions_revoked_at", ("revoked_at",)),
                },
            )
            foreign_keys = inspector.get_foreign_keys("user_sessions")
            self.assertEqual(len(foreign_keys), 1)
            self.assertEqual(
                (
                    foreign_keys[0]["name"],
                    tuple(foreign_keys[0]["constrained_columns"]),
                    foreign_keys[0]["referred_table"],
                    foreign_keys[0]["options"].get("ondelete"),
                ),
                (
                    "fk_user_sessions_user_id_users",
                    ("user_id",),
                    "users",
                    "CASCADE",
                ),
            )

            with app.app_context():
                command.downgrade(alembic_config, "f1a2b3c4d5e6")

            remaining_tables = set(inspect(engine).get_table_names())
            self.assertNotIn("users", remaining_tables)
            self.assertNotIn("user_sessions", remaining_tables)
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
