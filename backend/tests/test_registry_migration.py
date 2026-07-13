import tempfile
import unittest
from pathlib import Path

from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine, inspect, text

from app import create_app
from app.extensions import db


BACKEND_DIR = Path(__file__).resolve().parents[1]


class TestConfig:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    AUTO_CREATE_SCHEMA = False
    SECRET_KEY = "registry-migration-test-secret"
    TEKTON_NAMESPACE = "tekton"
    DEFAULT_IMAGE_REGISTRY = "registry.local"


class RegistryMigrationTest(unittest.TestCase):
    @staticmethod
    def _dispose_app_database(app):
        with app.app_context():
            db.session.remove()
            db.engine.dispose()

    def test_upgrade_and_downgrade_registry_connectivity_columns(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "registry-connectivity.db"

            class DatabaseConfig(TestConfig):
                SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path}"

            app = create_app(DatabaseConfig)
            self.addCleanup(self._dispose_app_database, app)
            alembic_config = AlembicConfig(str(BACKEND_DIR / "migrations/alembic.ini"))
            alembic_config.set_main_option(
                "script_location", str(BACKEND_DIR / "migrations")
            )

            with app.app_context():
                db.session.execute(text(
                    "CREATE TABLE container_registries ("
                    "id INTEGER PRIMARY KEY, project_id INTEGER, "
                    "name VARCHAR(120) NOT NULL, provider VARCHAR(30) NOT NULL, "
                    "server VARCHAR(300) NOT NULL, namespace VARCHAR(200), "
                    "username VARCHAR(300), encrypted_password TEXT, "
                    "email VARCHAR(300), pull_secret_name VARCHAR(253) NOT NULL, "
                    "is_default BOOLEAN NOT NULL, is_active BOOLEAN NOT NULL, "
                    "created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL"
                    ")"
                ))
                db.session.execute(text(
                    "INSERT INTO container_registries "
                    "(id, project_id, name, provider, server, username, "
                    "pull_secret_name, is_default, is_active, created_at, updated_at) "
                    "VALUES (1, 7, 'Existing Harbor', 'harbor', "
                    "'harbor.example.test', 'robot', 'registry-pull', 1, 1, "
                    "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ))
                db.session.commit()
                command.stamp(alembic_config, "d4e5f6a7b8c9")
                command.upgrade(alembic_config, "e5f6a7b8c9d0")

            engine = create_engine(DatabaseConfig.SQLALCHEMY_DATABASE_URI)
            self.addCleanup(engine.dispose)
            columns = {
                column["name"]
                for column in inspect(engine).get_columns("container_registries")
            }
            self.assertTrue({
                "skip_tls_verify",
                "connection_status",
                "last_checked_at",
                "last_connection_message",
            }.issubset(columns))

            with engine.connect() as connection:
                row = connection.execute(text(
                    "SELECT name, skip_tls_verify, connection_status "
                    "FROM container_registries WHERE id = 1"
                )).mappings().one()
            self.assertEqual(row["name"], "Existing Harbor")
            self.assertFalse(row["skip_tls_verify"])
            self.assertEqual(row["connection_status"], "untested")

            with app.app_context():
                command.downgrade(alembic_config, "d4e5f6a7b8c9")

            downgraded = {
                column["name"]
                for column in inspect(engine).get_columns("container_registries")
            }
            self.assertFalse({
                "skip_tls_verify",
                "connection_status",
                "last_checked_at",
                "last_connection_message",
            }.intersection(downgraded))


if __name__ == "__main__":
    unittest.main()
