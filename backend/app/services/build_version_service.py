from app.models import ApplicationBuildVersion
from app.utils.errors import ApiError
from .tekton_service import TektonService
from flask import current_app


class BuildVersionService:
    def list(self, app):
        changed = False
        namespace = current_app.config.get("TEKTON_NAMESPACE")
        for item in app.build_versions:
            if item.status in {"Pending", "Running"} and item.pipeline_run_name and namespace:
                try:
                    result = TektonService().get_pipeline_run_status(item.pipeline_run_name, namespace)
                except Exception:
                    continue
                status = result.get("status", item.status)
                if status != item.status:
                    item.status = status
                    item.error_message = result.get("message") if status == "Failed" else None
                    changed = True
                if result.get("finished_at") and not item.finished_at:
                    from datetime import datetime
                    item.finished_at = datetime.fromisoformat(result["finished_at"].replace("Z", "+00:00"))
                    changed = True
        if changed:
            from app.extensions import db
            db.session.commit()
        return [item.to_dict() for item in app.build_versions]

    def get(self, app, build_version_id):
        item = ApplicationBuildVersion.query.filter_by(
            id=build_version_id, application_id=app.id, project_id=app.project_id
        ).first()
        if not item:
            raise ApiError("构建版本不存在", 404, "BUILD_VERSION_NOT_FOUND")
        return item

    def require_publishable(self, app, build_version_id):
        item = self.get(app, build_version_id)
        if item.status != "Succeeded":
            raise ApiError("只有构建成功的版本才能发布", 409, "BUILD_VERSION_NOT_READY")
        if not item.image_name or not item.image_tag:
            raise ApiError("构建版本缺少镜像信息", 409, "BUILD_VERSION_IMAGE_MISSING")
        return item
