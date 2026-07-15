from flask import Blueprint, g, request

from app.services.application_service import ApplicationService
from app.services.delivery_context_service import DeliveryContextService
from app.services.project_runtime_service import ProjectRuntimeService
from app.services.project_service import ProjectService
from app.services.runtime_operation_service import RuntimeOperationService
from app.utils.response import success
from app.utils.validation import json_object


bp = Blueprint("runtime", __name__, url_prefix="/api/projects")


@bp.get("/<int:project_id>/runtime")
def project_runtime(project_id):
    project = ProjectService().get(project_id)
    return success(ProjectRuntimeService().overview(project))


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
