import unittest
from unittest.mock import patch

from sqlalchemy.exc import IntegrityError

from app import create_app
from app.extensions import db
from app.models import (
    Application,
    ApplicationBuildVersion,
    ApplicationEnvironment,
    ApplicationReleaseBatch,
    ApplicationReleaseTarget,
    Project,
)
from app.services.release_batch_service import ReleaseBatchService
from app.utils.errors import ApiError


class TestConfig:
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    AUTO_CREATE_SCHEMA = True
    SECRET_KEY = "release-batch-service-test-secret"
    TESTING = True


class ReleaseBatchServiceTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.context = self.app.app_context()
        self.context.push()
        self.project = Project(key="delivery", name="Delivery")
        self.other_project = Project(key="other", name="Other")
        db.session.add_all([self.project, self.other_project])
        db.session.flush()
        self.application = Application(
            project_id=self.project.id,
            name="payments",
            repo_url="https://github.com/example/payments.git",
            branch="main",
            language="java",
            framework="spring-boot",
            build_type="maven",
            namespace="payments-dev",
            image_name="registry.local/payments",
            image_tag="latest",
            port=8080,
        )
        self.other_application = Application(
            project_id=self.other_project.id,
            name="other",
            repo_url="https://github.com/example/other.git",
            branch="main",
            language="nodejs",
            framework="express",
            build_type="npm",
            namespace="other-dev",
            image_name="registry.local/other",
            image_tag="latest",
            port=3000,
        )
        db.session.add_all([self.application, self.other_application])
        db.session.flush()
        self.dev = ApplicationEnvironment(
            application_id=self.application.id,
            environment_name="dev",
            namespace="payments-dev",
        )
        self.prod = ApplicationEnvironment(
            application_id=self.application.id,
            environment_name="prod",
            namespace="payments-prod",
            approval_required=True,
        )
        self.foreign_environment = ApplicationEnvironment(
            application_id=self.other_application.id,
            environment_name="dev",
            namespace="other-dev",
        )
        db.session.add_all([self.dev, self.prod, self.foreign_environment])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    def persist_build(self, app, user, **kwargs):
        version = ApplicationBuildVersion(
            application_id=app.id,
            project_id=app.project_id,
            version=kwargs.get("git_commit", "abc123"),
            git_repo=app.repo_url,
            git_branch=kwargs.get("branch", app.branch),
            git_commit=kwargs.get("git_commit", "abc123"),
            image_name=app.image_name,
            image_tag=kwargs.get("git_commit", "abc123"),
            status="Pending",
            created_by=user,
        )
        db.session.add(version)
        db.session.flush()
        return version

    @patch("app.services.release_batch_service.ApplicationService.build")
    @patch("app.services.release_batch_service.GitMetadataService.list_commits")
    def test_create_allows_build_only_batch(self, list_commits, build):
        list_commits.return_value = [
            {"sha": "abc123", "message": "build only", "author": "Dev"}
        ]
        build.side_effect = self.persist_build

        batch = ReleaseBatchService().create(
            self.application, "main", "abc123", [], "admin"
        )

        self.assertEqual(batch.targets, [])
        self.assertEqual(batch.git_commit, "abc123")
        self.assertIsNotNone(batch.build_version_id)
        build.assert_called_once()

    def create_batch(self, build_status="Succeeded", with_dev_target=False):
        version = ApplicationBuildVersion(
            application_id=self.application.id,
            project_id=self.project.id,
            version="abc123",
            git_repo=self.application.repo_url,
            git_branch="main",
            git_commit="abc123",
            image_name=self.application.image_name,
            image_tag="abc123",
            status=build_status,
            created_by="admin",
        )
        batch = ApplicationReleaseBatch(
            application_id=self.application.id,
            project_id=self.project.id,
            branch="main",
            git_commit="abc123",
            status="Succeeded" if build_status == "Succeeded" else "Building",
            created_by="admin",
            build_version=version,
        )
        db.session.add(batch)
        db.session.flush()
        if with_dev_target:
            db.session.add(ApplicationReleaseTarget(
                batch=batch,
                environment_id=self.dev.id,
                build_version_id=version.id,
                status="Succeeded",
            ))
        db.session.commit()
        return batch

    def test_add_targets_to_succeeded_build(self):
        batch = self.create_batch()

        updated = ReleaseBatchService().add_targets(
            self.application, batch.id, [self.dev.id, self.prod.id]
        )

        self.assertEqual(
            {target.environment_id for target in updated.targets},
            {self.dev.id, self.prod.id},
        )
        self.assertTrue(all(target.status == "Pending" for target in updated.targets))
        self.assertTrue(all(
            target.build_version_id == batch.build_version_id
            for target in updated.targets
        ))

    def test_add_targets_rejects_build_that_has_not_succeeded(self):
        batch = self.create_batch(build_status="Running")

        with self.assertRaises(ApiError) as error:
            ReleaseBatchService().add_targets(
                self.application, batch.id, [self.dev.id]
            )

        self.assertEqual(error.exception.code, "BUILD_VERSION_NOT_READY")

    def test_add_targets_rejects_existing_target(self):
        batch = self.create_batch(with_dev_target=True)

        with self.assertRaises(ApiError) as error:
            ReleaseBatchService().add_targets(
                self.application, batch.id, [self.dev.id]
            )

        self.assertEqual(error.exception.code, "RELEASE_TARGET_EXISTS")

    def test_add_targets_rejects_foreign_environment(self):
        batch = self.create_batch()

        with self.assertRaises(ApiError) as error:
            ReleaseBatchService().add_targets(
                self.application, batch.id, [self.foreign_environment.id]
            )

        self.assertEqual(error.exception.code, "ENVIRONMENT_NOT_FOUND")

    def test_add_targets_requires_at_least_one_environment(self):
        batch = self.create_batch()

        with self.assertRaises(ApiError) as error:
            ReleaseBatchService().add_targets(self.application, batch.id, [])

        self.assertEqual(error.exception.code, "RELEASE_ENVIRONMENTS_REQUIRED")

    def test_add_targets_translates_unique_constraint_race(self):
        batch = self.create_batch()
        database_error = IntegrityError(
            "insert release target",
            {},
            Exception("uq_release_target_environment"),
        )

        with patch.object(db.session, "commit", side_effect=database_error), patch.object(
            db.session, "rollback"
        ) as rollback:
            with self.assertRaises(ApiError) as error:
                ReleaseBatchService().add_targets(
                    self.application, batch.id, [self.dev.id]
                )

        self.assertEqual(error.exception.code, "RELEASE_TARGET_EXISTS")
        rollback.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
