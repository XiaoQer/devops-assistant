from flask import Blueprint, current_app, request

from app.extensions import db
from app.models import Application, ApplicationBuildVersion, ApplicationReleaseBatch, ApplicationReleaseTarget, PipelineExecution
from app.services.cicd_workbench_service import CicdWorkbenchService
from app.services.delivery_reconciler import DeliveryReconciler
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


@bp.get("/workbench")
def workbench(project_id):
    ProjectService().get(project_id)
    return success({
        "items": CicdWorkbenchService().list_applications(
            project_id,
            query=request.args.get("query", "").strip() or None,
            status=request.args.get("status", "").strip() or None,
        )
    })


@bp.get("/<pipeline_run_name>/status")
def pipeline_status(project_id, pipeline_run_name):
    get_execution(project_id, pipeline_run_name)
    service = TektonService()
    data = service.get_pipeline_run_status(pipeline_run_name, namespace())
    data["task_runs"] = service.list_task_runs(pipeline_run_name, namespace())
    return success(data)


@bp.get("/<pipeline_run_name>/flow")
def pipeline_flow(project_id, pipeline_run_name):
    """Return the CI build and its associated multi-environment CD targets."""
    execution = get_execution(project_id, pipeline_run_name)
    build = execution if isinstance(execution, ApplicationBuildVersion) else None
    if build is None and getattr(execution, "build_version_id", None):
        build = ApplicationBuildVersion.query.get(execution.build_version_id)
    batch = ApplicationReleaseBatch.query.filter_by(
        project_id=project_id,
        build_version_id=build.id if build else None,
    ).first() if build else None
    if batch is None:
        target = ApplicationReleaseTarget.query.filter_by(
            pipeline_run_name=pipeline_run_name,
        ).first()
        batch = target.batch if target and target.batch.project_id == project_id else None
        if batch and not build:
            build = batch.build_version
    if batch:
        # Pipeline detail is also a reconciliation entry point. Without this,
        # a completed build can remain Pending until another application API is
        # opened, leaving all Deploy-only targets without a PipelineRun/logs.
        DeliveryReconciler().reconcile_batch(batch.id)
        batch = db.session.get(ApplicationReleaseBatch, batch.id)
        if batch and not build:
            build = batch.build_version
    build_data = build.to_dict() if build else None
    if build_data and build.application:
        build_data["build_type"] = build.application.build_type
    return success({
        "current_run": pipeline_run_name,
        "build": build_data,
        "batch": batch.to_dict() if batch else None,
    })


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
