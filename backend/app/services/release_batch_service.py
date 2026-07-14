from app.extensions import db
from app.models import ApplicationEnvironment, ApplicationReleaseBatch, ApplicationReleaseTarget
from sqlalchemy.exc import IntegrityError
from app.services.application_service import ApplicationService
from app.services.git_metadata_service import GitMetadataService
from app.utils.errors import ApiError


class ReleaseBatchService:
    def create(self, app, branch, git_commit, environment_ids, user):
        if not branch or not git_commit:
            raise ApiError("必须选择分支和提交", 400, "RELEASE_COMMIT_REQUIRED")
        if not isinstance(environment_ids, list):
            raise ApiError("发布环境选择无效", 400, "RELEASE_ENVIRONMENTS_INVALID")
        try:
            unique_ids = list(dict.fromkeys(int(value) for value in environment_ids))
        except (TypeError, ValueError):
            raise ApiError("发布环境选择无效", 400, "RELEASE_ENVIRONMENTS_INVALID")
        environments = ApplicationEnvironment.query.filter(
            ApplicationEnvironment.application_id == app.id,
            ApplicationEnvironment.id.in_(unique_ids),
        ).all()
        if len(environments) != len(unique_ids):
            raise ApiError("发布环境不存在或不属于当前应用", 404, "ENVIRONMENT_NOT_FOUND")
        commits = GitMetadataService().list_commits(app.repo_url, branch, 20)
        selected = next((item for item in commits if item["sha"] == git_commit), None)
        if not selected:
            raise ApiError("所选提交不属于该分支或已不可用", 422, "GIT_COMMIT_INVALID")
        batch = ApplicationReleaseBatch(
            application_id=app.id, project_id=app.project_id, branch=branch,
            git_commit=git_commit, commit_message=selected["message"],
            commit_author=selected["author"], status="Building", created_by=user,
        )
        db.session.add(batch)
        db.session.flush()
        for environment in environments:
            db.session.add(ApplicationReleaseTarget(batch=batch, environment_id=environment.id, status="Pending"))
        try:
            version = ApplicationService().build(
                app, user, branch=branch, git_commit=git_commit,
                commit_message=selected["message"], commit_author=selected["author"],
                release_batch=batch,
            )
            batch.build_version_id = version.id
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return batch

    def get(self, app, batch_id):
        batch = ApplicationReleaseBatch.query.filter_by(
            id=batch_id, application_id=app.id, project_id=app.project_id
        ).first()
        if not batch:
            raise ApiError("发布批次不存在", 404, "RELEASE_BATCH_NOT_FOUND")
        return batch

    def list(self, app):
        return ApplicationReleaseBatch.query.filter_by(
            application_id=app.id, project_id=app.project_id
        ).order_by(ApplicationReleaseBatch.created_at.desc()).all()

    def add_targets(self, app, batch_id, environment_ids):
        if not isinstance(environment_ids, list) or not environment_ids:
            raise ApiError(
                "至少选择一个发布环境",
                400,
                "RELEASE_ENVIRONMENTS_REQUIRED",
            )
        try:
            unique_ids = list(dict.fromkeys(int(value) for value in environment_ids))
        except (TypeError, ValueError):
            raise ApiError(
                "发布环境选择无效",
                400,
                "RELEASE_ENVIRONMENTS_INVALID",
            ) from None

        batch = self.get(app, batch_id)
        if not batch.build_version or batch.build_version.status != "Succeeded":
            raise ApiError(
                "构建版本尚未成功，不能追加发布环境",
                409,
                "BUILD_VERSION_NOT_READY",
            )
        environments = ApplicationEnvironment.query.filter(
            ApplicationEnvironment.application_id == app.id,
            ApplicationEnvironment.id.in_(unique_ids),
        ).all()
        if len(environments) != len(unique_ids):
            raise ApiError(
                "发布环境不存在或不属于当前应用",
                404,
                "ENVIRONMENT_NOT_FOUND",
            )
        existing_ids = {target.environment_id for target in batch.targets}
        if existing_ids.intersection(unique_ids):
            raise ApiError(
                "发布环境已经关联到该构建版本",
                409,
                "RELEASE_TARGET_EXISTS",
            )
        for environment in environments:
            db.session.add(ApplicationReleaseTarget(
                batch=batch,
                environment_id=environment.id,
                build_version_id=batch.build_version_id,
                status="Pending",
            ))
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise ApiError(
                "发布环境已经关联到该构建版本",
                409,
                "RELEASE_TARGET_EXISTS",
            ) from None
        return batch
