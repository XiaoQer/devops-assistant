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
    SECRET_KEY = "application-delivery-migration-test-secret"
    TEKTON_NAMESPACE = "tekton"
    DEFAULT_IMAGE_REGISTRY = "registry.local"


class ApplicationDeliveryMigrationTest(unittest.TestCase):
    @staticmethod
    def _dispose_app_database(app):
        with app.app_context():
            db.session.remove()
            db.engine.dispose()

    def test_upgrade_and_downgrade_application_delivery_scope(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "application-delivery.db"

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
                    "CREATE TABLE projects ("
                    "id INTEGER PRIMARY KEY, `key` VARCHAR(64) NOT NULL UNIQUE"
                    ")"
                ))
                db.session.execute(text(
                    "CREATE TABLE kubernetes_clusters (id INTEGER PRIMARY KEY)"
                ))
                db.session.execute(text(
                    "CREATE TABLE applications ("
                    "id INTEGER PRIMARY KEY, project_id INTEGER, "
                    "FOREIGN KEY(project_id) REFERENCES projects(id)"
                    ")"
                ))
                db.session.execute(text(
                    "CREATE TABLE pipeline_executions ("
                    "id INTEGER PRIMARY KEY, application_id INTEGER NOT NULL, "
                    "FOREIGN KEY(application_id) REFERENCES applications(id)"
                    ")"
                ))
                db.session.execute(text(
                    "CREATE TABLE release_records ("
                    "id INTEGER PRIMARY KEY, application_id INTEGER NOT NULL, "
                    "project_id INTEGER, environment VARCHAR(30) NOT NULL, "
                    "deploy_namespace VARCHAR(120) NOT NULL, "
                    "FOREIGN KEY(application_id) REFERENCES applications(id), "
                    "FOREIGN KEY(project_id) REFERENCES projects(id)"
                    ")"
                ))
                db.session.execute(text(
                    "CREATE TABLE approval_records ("
                    "id INTEGER PRIMARY KEY, application_id INTEGER NOT NULL, "
                    "project_id INTEGER, environment VARCHAR(30) NOT NULL, "
                    "namespace VARCHAR(120) NOT NULL, "
                    "FOREIGN KEY(application_id) REFERENCES applications(id), "
                    "FOREIGN KEY(project_id) REFERENCES projects(id)"
                    ")"
                ))
                db.session.execute(text(
                    "INSERT INTO projects (id, `key`) VALUES (1, 'default')"
                ))
                db.session.execute(text(
                    "INSERT INTO applications (id, project_id) VALUES (10, NULL)"
                ))
                db.session.execute(text(
                    "INSERT INTO pipeline_executions (id, application_id) "
                    "VALUES (20, 10)"
                ))
                db.session.execute(text(
                    "INSERT INTO release_records "
                    "(id, application_id, project_id, environment, deploy_namespace) "
                    "VALUES (30, 10, NULL, 'prod', 'production')"
                ))
                db.session.execute(text(
                    "INSERT INTO approval_records "
                    "(id, application_id, project_id, environment, namespace) "
                    "VALUES (40, 10, NULL, 'prod', 'production')"
                ))
                db.session.commit()
                command.stamp(alembic_config, "e5f6a7b8c9d0")
                command.upgrade(alembic_config, "f6a7b8c9d0e1")

            engine = create_engine(DatabaseConfig.SQLALCHEMY_DATABASE_URI)
            self.addCleanup(engine.dispose)
            with engine.connect() as connection:
                application = connection.execute(text(
                    "SELECT project_id FROM applications WHERE id = 10"
                )).mappings().one()
                execution = connection.execute(text(
                    "SELECT project_id, environment, kubernetes_cluster_id, "
                    "deploy_namespace FROM pipeline_executions WHERE id = 20"
                )).mappings().one()
                release = connection.execute(text(
                    "SELECT project_id, kubernetes_cluster_id "
                    "FROM release_records WHERE id = 30"
                )).mappings().one()
                approval = connection.execute(text(
                    "SELECT project_id, kubernetes_cluster_id "
                    "FROM approval_records WHERE id = 40"
                )).mappings().one()

            self.assertEqual(application["project_id"], 1)
            self.assertEqual(execution["project_id"], 1)
            self.assertEqual(execution["environment"], "dev")
            self.assertIsNone(execution["kubernetes_cluster_id"])
            self.assertEqual(execution["deploy_namespace"], "default")
            self.assertEqual(release["project_id"], 1)
            self.assertIsNone(release["kubernetes_cluster_id"])
            self.assertEqual(approval["project_id"], 1)
            self.assertIsNone(approval["kubernetes_cluster_id"])
            for table_name in (
                "applications",
                "pipeline_executions",
                "release_records",
                "approval_records",
            ):
                columns = {
                    column["name"]: column
                    for column in inspect(engine).get_columns(table_name)
                }
                self.assertFalse(columns["project_id"]["nullable"])

            with app.app_context():
                command.downgrade(alembic_config, "e5f6a7b8c9d0")

            pipeline_columns = {
                column["name"]
                for column in inspect(engine).get_columns("pipeline_executions")
            }
            self.assertFalse({
                "project_id",
                "environment",
                "kubernetes_cluster_id",
                "deploy_namespace",
            }.intersection(pipeline_columns))
            release_columns = {
                column["name"]
                for column in inspect(engine).get_columns("release_records")
            }
            approval_columns = {
                column["name"]
                for column in inspect(engine).get_columns("approval_records")
            }
            self.assertNotIn("kubernetes_cluster_id", release_columns)
            self.assertNotIn("kubernetes_cluster_id", approval_columns)
            for table_name in (
                "applications",
                "release_records",
                "approval_records",
            ):
                columns = {
                    column["name"]: column
                    for column in inspect(engine).get_columns(table_name)
                }
                self.assertTrue(columns["project_id"]["nullable"])

            with engine.connect() as connection:
                remaining_ids = {
                    "application": connection.execute(text(
                        "SELECT id FROM applications WHERE id = 10"
                    )).scalar_one(),
                    "execution": connection.execute(text(
                        "SELECT id FROM pipeline_executions WHERE id = 20"
                    )).scalar_one(),
                    "release": connection.execute(text(
                        "SELECT id FROM release_records WHERE id = 30"
                    )).scalar_one(),
                    "approval": connection.execute(text(
                        "SELECT id FROM approval_records WHERE id = 40"
                    )).scalar_one(),
                }
            self.assertEqual(remaining_ids, {
                "application": 10,
                "execution": 20,
                "release": 30,
                "approval": 40,
            })


if __name__ == "__main__":
    unittest.main()
