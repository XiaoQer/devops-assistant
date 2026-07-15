import tempfile
import unittest
from pathlib import Path

from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine, inspect

from app import create_app
from app.extensions import db


BACKEND_DIR = Path(__file__).resolve().parents[1]


class TestConfig:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    AUTO_CREATE_SCHEMA = False
    SECRET_KEY = "runtime-audit-migration-test-secret"
    TEKTON_NAMESPACE = "tekton"
    DEFAULT_IMAGE_REGISTRY = "registry.local"


class RuntimeOperationAuditMigrationTest(unittest.TestCase):
    @staticmethod
    def _dispose_app_database(app):
        with app.app_context():
            db.session.remove()
            db.engine.dispose()

    def test_upgrade_and_downgrade_runtime_operation_audits(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "runtime-audits.db"

            class DatabaseConfig(TestConfig):
                SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path}"

            app = create_app(DatabaseConfig)
            self.addCleanup(self._dispose_app_database, app)
            alembic_config = AlembicConfig(str(BACKEND_DIR / "migrations/alembic.ini"))
            alembic_config.set_main_option(
                "script_location", str(BACKEND_DIR / "migrations")
            )

            with app.app_context():
                command.stamp(alembic_config, "h8c9d0e1f2a3")
                command.upgrade(alembic_config, "i9d0e1f2a3b4")

            engine = create_engine(DatabaseConfig.SQLALCHEMY_DATABASE_URI)
            self.addCleanup(engine.dispose)
            inspector = inspect(engine)
            self.assertIn("runtime_operation_audits", inspector.get_table_names())
            self.assertEqual(
                {
                    (index["name"], tuple(index["column_names"]))
                    for index in inspector.get_indexes("runtime_operation_audits")
                },
                {
                    ("ix_runtime_audits_application_id", ("application_id",)),
                    ("ix_runtime_audits_project_id", ("project_id",)),
                    ("ix_runtime_audits_started_at", ("started_at",)),
                    ("ix_runtime_audits_status", ("status",)),
                    ("ix_runtime_audits_user_id", ("user_id",)),
                },
            )

            with app.app_context():
                command.downgrade(alembic_config, "h8c9d0e1f2a3")

            self.assertNotIn(
                "runtime_operation_audits", inspect(engine).get_table_names()
            )

    def test_audit_serialization_contains_metadata_only(self):
        from app.models import RuntimeOperationAudit

        audit = RuntimeOperationAudit.start(
            user_id=11,
            project_id=12,
            application_id=13,
            environment="prod",
            cluster_id=14,
            namespace="payments",
            resource_kind="Pod",
            resource_name="payments-abc",
            container="api",
            action="exec",
            reason="investigate incident",
        )
        audit.finish("Succeeded")

        serialized = audit.to_dict()
        self.assertEqual(serialized["reason"], "investigate incident")
        self.assertEqual(serialized["status"], "Succeeded")
        self.assertIsNotNone(serialized["finished_at"])
        self.assertNotIn("terminal_input", serialized)
        self.assertNotIn("terminal_output", serialized)
        self.assertNotIn("resource_yaml", serialized)


if __name__ == "__main__":
    unittest.main()
