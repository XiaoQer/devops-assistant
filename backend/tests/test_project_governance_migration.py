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
    SECRET_KEY = "project-governance-migration-test-secret"
    TEKTON_NAMESPACE = "tekton"
    DEFAULT_IMAGE_REGISTRY = "registry.local"


class ProjectGovernanceMigrationTest(unittest.TestCase):
    @staticmethod
    def _dispose_app_database(app):
        with app.app_context():
            db.session.remove()
            db.engine.dispose()

    def test_upgrade_and_downgrade_project_governance_columns(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "project-governance.db"

            class DatabaseConfig(TestConfig):
                SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path}"

            app = create_app(DatabaseConfig)
            self.addCleanup(self._dispose_app_database, app)
            alembic_config = AlembicConfig(str(BACKEND_DIR / "migrations/alembic.ini"))
            alembic_config.set_main_option(
                "script_location",
                str(BACKEND_DIR / "migrations"),
            )

            with app.app_context():
                db.session.execute(text(
                    "CREATE TABLE projects ("
                    "id INTEGER PRIMARY KEY, "
                    "`key` VARCHAR(64) NOT NULL, "
                    "name VARCHAR(120) NOT NULL, "
                    "description TEXT, "
                    "created_at DATETIME NOT NULL, "
                    "updated_at DATETIME NOT NULL"
                    ")"
                ))
                db.session.execute(text("CREATE UNIQUE INDEX ix_projects_key ON projects (`key`)"))
                db.session.commit()
                command.stamp(alembic_config, "a7c8d9e0f1a2")
                command.upgrade(alembic_config, "c3d4e5f6a7b8")

            engine = create_engine(DatabaseConfig.SQLALCHEMY_DATABASE_URI)
            self.addCleanup(engine.dispose)
            inspector = inspect(engine)
            project_columns = {
                column["name"]: column
                for column in inspector.get_columns("projects")
            }
            for column in (
                "status",
                "business_owner",
                "billing_owner",
                "github_group",
                "github_default_visibility",
                "aliyun_account_id",
                "aliyun_resource_group_id",
                "aliyun_region",
                "aliyun_vpc_id",
                "aliyun_binding_status",
            ):
                self.assertIn(column, project_columns)
            self.assertFalse(project_columns["status"]["nullable"])
            self.assertFalse(project_columns["github_default_visibility"]["nullable"])
            self.assertFalse(project_columns["aliyun_binding_status"]["nullable"])
            self.assertEqual(
                {
                    (index["name"], tuple(index["column_names"]))
                    for index in inspector.get_indexes("projects")
                    if index["name"] in {
                        "ix_projects_status",
                        "ix_projects_aliyun_binding_status",
                    }
                },
                {
                    ("ix_projects_status", ("status",)),
                    ("ix_projects_aliyun_binding_status", ("aliyun_binding_status",)),
                },
            )

            with app.app_context():
                command.downgrade(alembic_config, "a7c8d9e0f1a2")

            downgraded_columns = {
                column["name"]
                for column in inspect(engine).get_columns("projects")
            }
            self.assertNotIn("status", downgraded_columns)
            self.assertNotIn("aliyun_binding_status", downgraded_columns)


if __name__ == "__main__":
    unittest.main()
