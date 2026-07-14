from datetime import datetime, timezone

from flask import current_app

from app.extensions import db
from app.models import (
    Application, ReleaseRecord, PipelineExecution, ApplicationEnvironment
)
from app.utils.errors import ApiError
from .application_runtime_service import ApplicationRuntimeService
from .delivery_context_service import DeliveryContextService
from .tekton_service import TektonService


class ReleaseService:
    FINAL_STATUSES = {"Succeeded", "Failed", "Cancelled"}

    def create_deploy_release(self, app, execution, payload, deploy_user):
        release = ReleaseRecord(
            application_id=app.id,
            project_id=app.project_id,
            release_type="deploy",
            environment=payload.get("environment", "dev"),
            git_repo=app.repo_url,
            git_branch=payload.get("git_branch", app.branch),
            git_commit=payload.get("git_commit"),
            image_name=payload.get("image_name", app.image_name),
            image_tag=payload.get("image_tag", app.image_tag),
            pipeline_run_name=execution.pipeline_run_name,
            deploy_namespace=payload.get("namespace", app.namespace),
            deploy_status="Pending",
            deploy_user=deploy_user,
        )
        db.session.add(release)
        return release

    def list_releases(self, app, environment=None, sync=True):
        query = ReleaseRecord.query.filter_by(
            application_id=app.id,
            project_id=app.project_id,
        )
        if environment:
            query = query.filter_by(environment=environment)
        releases = query.order_by(ReleaseRecord.created_at.desc()).all()
        if sync:
            self._sync_pipeline_releases(releases)
        return releases

    def sync_all(self):
        releases = (
            ReleaseRecord.query.join(Application)
            .filter(
                ReleaseRecord.project_id == Application.project_id,
                ReleaseRecord.pipeline_run_name.isnot(None),
                ReleaseRecord.deploy_status.notin_(self.FINAL_STATUSES),
            )
            .all()
        )
        self._sync_pipeline_releases(releases)
        return len(releases)

    def sync_project(self, project_id):
        releases = (
            ReleaseRecord.query.join(Application)
            .filter(
                ReleaseRecord.project_id == project_id,
                Application.project_id == project_id,
                ReleaseRecord.pipeline_run_name.isnot(None),
                ReleaseRecord.deploy_status.notin_(self.FINAL_STATUSES),
            )
            .all()
        )
        self._sync_pipeline_releases(releases)
        return len(releases)

    def rollback(self, app, release_id, environment, deploy_user):
        source = ReleaseRecord.query.filter_by(
            id=release_id,
            application_id=app.id,
            project_id=app.project_id,
        ).first()
        if not source:
            raise ApiError("发布记录不存在", 404, "RELEASE_NOT_FOUND")
        context = DeliveryContextService().resolve(
            app.project,
            app,
            environment or source.environment,
        )
        result = ApplicationRuntimeService().rollback(context, source.image)
        record = ReleaseRecord(
            application_id=app.id,
            project_id=app.project_id,
            release_type="rollback",
            environment=environment or source.environment,
            git_repo=source.git_repo,
            git_branch=source.git_branch,
            git_commit=source.git_commit,
            image_name=source.image_name,
            image_tag=source.image_tag,
            kubernetes_cluster_id=context.cluster.id,
            deploy_namespace=context.namespace,
            deploy_status="Succeeded",
            deploy_user=deploy_user,
            source_release_id=source.id,
            finished_at=datetime.now(timezone.utc),
        )
        app.image_name = source.image_name
        app.image_tag = source.image_tag
        app.status = "deployed"
        db.session.add(record)
        db.session.commit()
        return result, record

    def _sync_pipeline_releases(self, releases):
        pending = [
            release for release in releases
            if release.pipeline_run_name
            and release.deploy_status not in self.FINAL_STATUSES
        ]
        if not pending:
            return
        service = TektonService()
        namespace = current_app.config["TEKTON_NAMESPACE"]
        changed = False
        for release in pending:
            try:
                status = service.get_pipeline_run_status(
                    release.pipeline_run_name, namespace
                )
            except Exception:
                continue
            release.deploy_status = status["status"]
            release.error_message = (
                status.get("message") if status["status"] == "Failed" else None
            )
            if status["status"] in self.FINAL_STATUSES:
                timestamp = status.get("finished_at")
                release.finished_at = (
                    datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    if timestamp else datetime.now(timezone.utc)
                )
            execution = PipelineExecution.query.filter_by(
                pipeline_run_name=release.pipeline_run_name,
                project_id=release.project_id,
                application_id=release.application_id,
            ).first()
            if execution:
                execution.status = status["status"]
                execution.error_message = release.error_message
                if status.get("started_at"):
                    execution.started_at = datetime.fromisoformat(
                        status["started_at"].replace("Z", "+00:00")
                    )
                execution.finished_at = release.finished_at
            if (
                release.application
                and release.application.project_id == release.project_id
            ):
                release.application.status = {
                    "Succeeded": "deployed",
                    "Failed": "failed",
                    "Cancelled": "cancelled",
                }.get(status["status"], "deploying")
            environment = ApplicationEnvironment.query.filter_by(
                application_id=release.application_id,
                environment_name=release.environment,
            ).first()
            if (
                environment
                and release.application
                and release.application.project_id == release.project_id
            ):
                environment.status = {
                    "Succeeded": "Progressing",
                    "Failed": "Failed",
                    "Cancelled": "Failed",
                }.get(status["status"], "Progressing")
            changed = True
        if changed:
            db.session.commit()
