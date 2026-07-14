from flask import Blueprint, request

from app.models import Application, ReleaseRecord
from app.utils.response import success
from app.services.release_service import ReleaseService
from app.services.project_service import ProjectService

bp = Blueprint(
    "release_center",
    __name__,
    url_prefix="/api/projects/<int:project_id>/releases",
)


@bp.get("")
def release_center(project_id):
    ProjectService().get(project_id)
    ReleaseService().sync_project(project_id)
    page = max(request.args.get("page", 1, type=int), 1)
    page_size = min(max(request.args.get("pageSize", 20, type=int), 1), 100)
    query = ReleaseRecord.query.join(Application).filter(
        ReleaseRecord.project_id == project_id,
        Application.project_id == project_id,
    )
    if request.args.get("environment"):
        query = query.filter(
            ReleaseRecord.environment == request.args["environment"]
        )
    if request.args.get("status"):
        query = query.filter(
            ReleaseRecord.deploy_status == request.args["status"]
        )
    pagination = query.order_by(ReleaseRecord.created_at.desc()).paginate(
        page=page, per_page=page_size, error_out=False
    )
    return success({
        "items": [item.to_dict() for item in pagination.items],
        "page": page,
        "pageSize": page_size,
        "total": pagination.total,
    })
