from flask import Blueprint, current_app, request

from app.models import Application, ApplicationBuildVersion, PipelineExecution
from app.services.project_service import ProjectService
from app.services.tekton_service import TektonService
from app.utils.errors import ApiError
from app.utils.response import success

bp = Blueprint(
    "pipelines",
    __name__,
    url_prefix="/api/projects/<int:project_id>/pipelines",
)


def namespace():
    return current_app.config["TEKTON_NAMESPACE"]


def get_execution(project_id, pipeline_run_name):
    execution = (
        PipelineExecution.query.join(Application)
        .filter(
            PipelineExecution.project_id == project_id,
            PipelineExecution.pipeline_run_name == pipeline_run_name,
            Application.project_id == project_id,
        )
        .first()
    )
    if execution:
        return execution
    build = (
        ApplicationBuildVersion.query.join(Application)
        .filter(
            ApplicationBuildVersion.project_id == project_id,
            ApplicationBuildVersion.pipeline_run_name == pipeline_run_name,
            Application.project_id == project_id,
        )
        .first()
    )
    if not build:
        raise ApiError(
            "PipelineExecution 不存在",
            404,
            "PIPELINE_EXECUTION_NOT_FOUND",
        )
    return build


@bp.get("")
def list_pipelines(project_id):
    ProjectService().get(project_id)
    page = max(request.args.get("page", 1, type=int), 1)
    page_size = min(max(request.args.get("pageSize", 20, type=int), 1), 100)
    query = PipelineExecution.query.join(Application).filter(
        PipelineExecution.project_id == project_id,
        Application.project_id == project_id,
    )
    status = request.args.get("status")
    if status:
        query = query.filter(PipelineExecution.status == status)
    search = request.args.get("query", "").strip()
    if search:
        query = query.filter(PipelineExecution.pipeline_run_name.ilike(f"%{search}%"))
    pagination = query.order_by(PipelineExecution.created_at.desc()).paginate(
        page=page, per_page=page_size, error_out=False
    )
    return success({
        "items": [item.to_dict() for item in pagination.items],
        "page": page,
        "pageSize": page_size,
        "total": pagination.total,
    })


@bp.get("/<pipeline_run_name>/status")
def pipeline_status(project_id, pipeline_run_name):
    get_execution(project_id, pipeline_run_name)
    service = TektonService()
    data = service.get_pipeline_run_status(pipeline_run_name, namespace())
    data["task_runs"] = service.list_task_runs(pipeline_run_name, namespace())
    return success(data)


@bp.get("/<pipeline_run_name>/logs")
def pipeline_logs(project_id, pipeline_run_name):
    get_execution(project_id, pipeline_run_name)
    service = TektonService()
    data = service.get_pipeline_run_log_details(pipeline_run_name, namespace())
    data["logs"] = service.get_pipeline_run_logs(pipeline_run_name, namespace())
    return success(data)


@bp.post("/<pipeline_run_name>/retry")
def retry_pipeline(project_id, pipeline_run_name):
    get_execution(project_id, pipeline_run_name)
    try:
        data = TektonService().retry_pipeline_run(pipeline_run_name, namespace())
    except ValueError as exc:
        raise ApiError(str(exc), 409, "PIPELINE_RETRY_NOT_ALLOWED") from exc
    return success(data, "PipelineRun 重试已提交", 201)
