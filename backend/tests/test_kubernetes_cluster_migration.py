import tempfile
import unittest
from pathlib import Path

from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine, inspect, text

from app import create_app
from app.extensions import db
from app.models import KubernetesCluster, Project


BACKEND_DIR = Path(__file__).resolve().parents[1]


class TestConfig:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    AUTO_CREATE_SCHEMA = False
    SECRET_KEY = "kubernetes-cluster-migration-test-secret"
    TEKTON_NAMESPACE = "tekton"
    DEFAULT_IMAGE_REGISTRY = "registry.local"


class KubernetesClusterMigrationTest(unittest.TestCase):
    @staticmethod
    def _dispose_app_database(app):
        with app.app_context():
            db.session.remove()
            db.engine.dispose()

    def test_upgrade_and_downgrade_cluster_onboarding_columns(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "cluster-onboarding.db"

            class DatabaseConfig(TestConfig):
                SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path}"

            app = create_app(DatabaseConfig)
            self.addCleanup(self._dispose_app_database, app)
            alembic_config = AlembicConfig(str(BACKEND_DIR / "migrations/alembic.ini"))
            alembic_config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))

            with app.app_context():
                db.session.execute(text(
                    "CREATE TABLE kubernetes_clusters ("
                    "id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL, "
                    "name VARCHAR(120) NOT NULL, description TEXT, "
                    "kube_context VARCHAR(200) NOT NULL, namespace_prefix VARCHAR(120), "
                    "api_server VARCHAR(300), is_default BOOLEAN NOT NULL, "
                    "is_active BOOLEAN NOT NULL, created_at DATETIME NOT NULL, "
                    "updated_at DATETIME NOT NULL"
                    ")"
                ))
                db.session.execute(text(
                    "INSERT INTO kubernetes_clusters "
                    "(id, project_id, name, kube_context, is_default, is_active, created_at, updated_at) "
                    "VALUES (1, 1, 'legacy', 'legacy-context', 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ))
                db.session.commit()
                command.stamp(alembic_config, "c3d4e5f6a7b8")
                command.upgrade(alembic_config, "d4e5f6a7b8c9")

            engine = create_engine(DatabaseConfig.SQLALCHEMY_DATABASE_URI)
            self.addCleanup(engine.dispose)
            columns = {column["name"] for column in inspect(engine).get_columns("kubernetes_clusters")}
            self.assertTrue({
                "environment_label",
                "encrypted_kubeconfig",
                "connection_status",
                "last_checked_at",
                "kubernetes_version",
            }.issubset(columns))

            with engine.connect() as connection:
                row = connection.execute(text(
                    "SELECT name, environment_label, encrypted_kubeconfig, connection_status "
                    "FROM kubernetes_clusters WHERE id = 1"
                )).mappings().one()
            self.assertEqual(row["name"], "legacy")
            self.assertIsNone(row["environment_label"])
            self.assertIsNone(row["encrypted_kubeconfig"])
            self.assertEqual(row["connection_status"], "untested")

            with app.app_context():
                command.downgrade(alembic_config, "c3d4e5f6a7b8")

            downgraded = {
                column["name"]
                for column in inspect(engine).get_columns("kubernetes_clusters")
            }
            self.assertFalse({
                "environment_label",
                "encrypted_kubeconfig",
                "connection_status",
                "last_checked_at",
                "kubernetes_version",
            }.intersection(downgraded))


class KubernetesClusterSerializationTest(unittest.TestCase):
    class DatabaseConfig(TestConfig):
        SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
        AUTO_CREATE_SCHEMA = True

    def setUp(self):
        self.app = create_app(self.DatabaseConfig)
        self.context = self.app.app_context()
        self.context.push()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    def test_serialization_exposes_only_safe_kubeconfig_metadata(self):
        project = Project(key="payments", name="Payments")
        db.session.add(project)
        db.session.flush()
        cluster = KubernetesCluster(
            project_id=project.id,
            name="prod",
            kube_context="prod-context",
            environment_label="production",
            encrypted_kubeconfig="ciphertext",
        )
        db.session.add(cluster)
        db.session.commit()

        data = cluster.to_dict()

        self.assertEqual(data["environment_label"], "production")
        self.assertTrue(data["has_kubeconfig"])
        self.assertEqual(data["connection_status"], "untested")
        self.assertNotIn("encrypted_kubeconfig", data)
        self.assertNotIn("kubeconfig", data)


if __name__ == "__main__":
    unittest.main()
