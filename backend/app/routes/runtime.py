from flask import Blueprint

from app.services.project_runtime_service import ProjectRuntimeService
from app.services.project_service import ProjectService
from app.utils.response import success


bp = Blueprint("runtime", __name__, url_prefix="/api/projects")


@bp.get("/<int:project_id>/runtime")
def project_runtime(project_id):
    project = ProjectService().get(project_id)
    return success(ProjectRuntimeService().overview(project))
