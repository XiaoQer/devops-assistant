from flask import Blueprint, current_app, g, request

from app.services.application_service import ApplicationService
from app.services.delivery_context_service import DeliveryContextService
from app.services.project_runtime_service import ProjectRuntimeService
from app.services.project_service import ProjectService
from app.services.runtime_operation_service import RuntimeOperationService
from app.services.runtime_exec_service import RuntimeExecService
from app.utils.response import success
from app.utils.validation import json_object
from app.utils.errors import ApiError


bp = Blueprint("runtime", __name__, url_prefix="/api/projects")


@bp.get("/<int:project_id>/runtime")
def project_runtime(project_id):
    project = ProjectService().get(project_id)
    environment = str(request.args.get("environment") or "").strip()
    if not environment:
        raise ApiError("environment 为必填参数", 400, "VALIDATION_ERROR")
    resource = str(request.args.get("resource") or "deployments").strip()
    if resource not in {"deployments", "pods"}:
        raise ApiError("不支持的 Runtime 资源类型", 400, "VALIDATION_ERROR")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    if page < 1 or page_size not in {20, 50, 100}:
        raise ApiError("分页参数无效", 400, "VALIDATION_ERROR")
    return success(ProjectRuntimeService().inventory(
        project, environment, resource, page, page_size,
        request.args.get("query"), request.args.get("status"),
    ))


@bp.get("/<int:project_id>/runtime/environments")
def runtime_environments(project_id):
    project = ProjectService().get(project_id)
    return success(ProjectRuntimeService().environments(project))


def runtime_context(project_id, app_id, environment):
    project = ProjectService().get(project_id)
    application = ApplicationService().get(project_id, app_id)
    return DeliveryContextService().resolve(project, application, environment)


@bp.get(
    "/<int:project_id>/applications/<int:app_id>/environments/<environment>"
    "/runtime/deployments/<deployment_name>/yaml"
)
def deployment_yaml(project_id, app_id, environment, deployment_name):
    context = runtime_context(project_id, app_id, environment)
    return success(
        RuntimeOperationService().deployment_manifest(context, deployment_name)
    )


@bp.post(
    "/<int:project_id>/applications/<int:app_id>/environments/<environment>"
    "/runtime/deployments/<deployment_name>/restart"
)
def restart_deployment(project_id, app_id, environment, deployment_name):
    payload = json_object(request.get_json(silent=True), required=True)
    context = runtime_context(project_id, app_id, environment)
    result = RuntimeOperationService().restart_deployment(
        context,
        deployment_name,
        g.current_user,
        payload.get("confirmed"),
        str(payload.get("reason") or "").strip() or None,
    )
    return success(result, "Deployment 重启已提交")


@bp.delete(
    "/<int:project_id>/applications/<int:app_id>/environments/<environment>"
    "/runtime/pods/<pod_name>"
)
def delete_pod(project_id, app_id, environment, pod_name):
    payload = json_object(request.get_json(silent=True), required=True)
    context = runtime_context(project_id, app_id, environment)
    result = RuntimeOperationService().delete_pod(
        context,
        pod_name,
        g.current_user,
        payload.get("confirmed"),
        str(payload.get("reason") or "").strip() or None,
    )
    return success(result, "Pod 删除已提交")


@bp.post(
    "/<int:project_id>/applications/<int:app_id>/environments/<environment>"
    "/runtime/pods/<pod_name>/exec-sessions"
)
def create_exec_session(project_id, app_id, environment, pod_name):
    payload = json_object(request.get_json(silent=True), required=True)
    if payload.get("confirmed") is not True:
        from app.utils.errors import ApiError

        raise ApiError("终端操作需要显式确认", 409, "CONFIRMATION_REQUIRED")
    context = runtime_context(project_id, app_id, environment)
    result = RuntimeExecService(
        current_app.extensions["runtime_exec_registry"]
    ).create(
        context,
        pod_name,
        str(payload.get("container") or "").strip(),
        g.current_user,
        payload.get("reason"),
    )
    return success(result, "终端会话已创建", 201)
