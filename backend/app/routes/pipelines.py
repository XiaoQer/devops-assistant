from flask import Blueprint, current_app, request

from app.services.tekton_service import TektonService
from app.utils.errors import ApiError
from app.utils.response import success

bp = Blueprint("pipelines", __name__, url_prefix="/api/pipelines")


def namespace():
    return request.args.get("namespace", current_app.config["TEKTON_NAMESPACE"])


@bp.get("")
def list_pipelines():
    page = max(request.args.get("page", 1, type=int), 1)
    page_size = min(max(request.args.get("pageSize", 20, type=int), 1), 100)
    items = TektonService().list_pipeline_runs(namespace())
    status = request.args.get("status")
    query = request.args.get("query", "").lower()
    if status:
        items = [item for item in items if item["status"] == status]
    if query:
        items = [
            item for item in items
            if query in " ".join(str(item.get(key) or "") for key in (
                "name", "application", "pipeline", "repo_url"
            )).lower()
        ]
    total = len(items)
    start = (page - 1) * page_size
    return success({
        "items": items[start:start + page_size],
        "page": page,
        "pageSize": page_size,
        "total": total,
    })


@bp.get("/<pipeline_run_name>/status")
def pipeline_status(pipeline_run_name):
    service = TektonService()
    data = service.get_pipeline_run_status(pipeline_run_name, namespace())
    data["task_runs"] = service.list_task_runs(pipeline_run_name, namespace())
    return success(data)


@bp.get("/<pipeline_run_name>/logs")
def pipeline_logs(pipeline_run_name):
    service = TektonService()
    data = service.get_pipeline_run_log_details(pipeline_run_name, namespace())
    data["logs"] = service.get_pipeline_run_logs(pipeline_run_name, namespace())
    return success(data)


@bp.post("/<pipeline_run_name>/retry")
def retry_pipeline(pipeline_run_name):
    try:
        data = TektonService().retry_pipeline_run(pipeline_run_name, namespace())
    except ValueError as exc:
        raise ApiError(str(exc), 409, "PIPELINE_RETRY_NOT_ALLOWED") from exc
    return success(data, "PipelineRun 重试已提交", 201)

