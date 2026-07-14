from flask import Blueprint, g, request

from app.models import Application, ApplicationEnvironment
from app.services.application_service import ApplicationService
from app.services.deployment_plan_service import DeploymentPlanService
from app.services.kubernetes_service import KubernetesService
from app.services.release_service import ReleaseService
from app.services.approval_service import ApprovalService
from app.services.project_service import ProjectService
from app.utils.errors import ApiError
from app.utils.response import success
from app.utils.validation import (
    json_object,
    require_fields,
    require_positive_int,
    require_string,
)
from app.extensions import db

bp = Blueprint(
    "applications",
    __name__,
    url_prefix="/api/projects/<int:project_id>/applications",
)


def get_application(project_id, app_id):
    return ApplicationService().get(project_id, app_id)


@bp.get("")
def list_applications(project_id):
    ProjectService().get(project_id)
    apps = (
        Application.query.filter_by(project_id=project_id)
        .order_by(Application.created_at.desc())
        .all()
    )
    return success([app.to_dict(include_spec=False) for app in apps])


@bp.post("")
def create_application(project_id):
    payload = json_object(request.get_json(silent=True), required=True)
    require_fields(payload, "name", "repo_url")
    project = ProjectService().get(project_id)
    app = ApplicationService().create(project, payload)
    return success(app.to_dict(), "应用分析完成", 201)


@bp.get("/<int:app_id>")
def application_detail(project_id, app_id):
    return success(get_application(project_id, app_id).to_dict())


@bp.post("/<int:app_id>/deploy")
def deploy_application(project_id, app_id):
    payload = json_object(request.get_json(silent=True))
    app = get_application(project_id, app_id)
    environment_name = require_string(payload, "environment")
    payload["environment"] = environment_name
    plan = DeploymentPlanService().build_plan(app, payload)
    if not plan["can_deploy"]:
        raise ApiError(
            "发布前检查未通过",
            409,
            "DEPLOYMENT_PRECHECK_FAILED",
            plan,
        )
    environment = ApplicationEnvironment.query.filter_by(
        application_id=app.id, environment_name=environment_name
    ).first()
    if environment and environment.approval_required:
        approval = ApprovalService().submit(
            app, payload, g.current_user.username
        )
        return success(
            {
                "approval_required": True,
                "approval": approval.to_dict(),
            },
            "Production 发布需要审批",
            202,
        )
    execution, release = ApplicationService().deploy(
        app,
        payload,
        g.current_user.username,
    )
    data = execution.to_dict()
    data["release"] = release.to_dict()
    return success(data, "PipelineRun 已创建", 201)


@bp.post("/<int:app_id>/deploy/plan")
def deployment_plan(project_id, app_id):
    payload = json_object(request.get_json(silent=True))
    app = get_application(project_id, app_id)
    payload["environment"] = require_string(payload, "environment")
    return success(DeploymentPlanService().build_plan(app, payload), "发布计划生成完成")


@bp.get("/<int:app_id>/executions")
def list_executions(project_id, app_id):
    app = get_application(project_id, app_id)
    return success([
        execution.to_dict()
        for execution in app.executions
        if execution.project_id == project_id
    ])


@bp.get("/<int:app_id>/releases")
def list_releases(project_id, app_id):
    releases = ReleaseService().list_releases(
        get_application(project_id, app_id), request.args.get("environment")
    )
    return success([release.to_dict() for release in releases])


@bp.post("/<int:app_id>/rollback")
def rollback_application(project_id, app_id):
    payload = json_object(request.get_json(silent=True), required=True)
    release_id = require_positive_int(payload, "release_id")
    environment_name = require_string(payload, "environment") if "environment" in payload else "dev"
    result, release = ReleaseService().rollback(
        get_application(project_id, app_id),
        release_id,
        environment_name,
        g.current_user.username,
    )
    return success(
        {**result, "release": release.to_dict()},
        "Rollback completed",
    )


@bp.get("/<int:app_id>/status")
def application_status(project_id, app_id):
    app = get_application(project_id, app_id)
    environment = request.args.get("environment", "dev")
    environment_config = ApplicationEnvironment.query.filter_by(
        application_id=app.id, environment_name=environment
    ).first()
    namespace = environment_config.namespace if environment_config else app.namespace
    data = KubernetesService().get_application_status(app.name, namespace)
    if environment_config:
        environment_config.status = data["status"]
        db.session.commit()
    data["environment"] = environment
    data["namespace"] = namespace
    return success(data)


@bp.get("/<int:app_id>/runtime/pods/<pod_name>/logs")
def pod_logs(project_id, app_id, pod_name):
    app = get_application(project_id, app_id)
    environment = request.args.get("environment", "dev")
    env = ApplicationEnvironment.query.filter_by(
        application_id=app.id, environment_name=environment
    ).first()
    namespace = env.namespace if env else app.namespace
    logs = KubernetesService().get_pod_logs(
        pod_name, namespace, request.args.get("container"), request.args.get("tail", 500, type=int)
    )
    return success({"pod": pod_name, "namespace": namespace, "logs": logs})


@bp.get("/<int:app_id>/runtime/pods/<pod_name>/yaml")
def pod_yaml(project_id, app_id, pod_name):
    app = get_application(project_id, app_id)
    environment = request.args.get("environment", "dev")
    env = ApplicationEnvironment.query.filter_by(
        application_id=app.id, environment_name=environment
    ).first()
    namespace = env.namespace if env else app.namespace
    return success(KubernetesService().get_pod_manifest(pod_name, namespace))
