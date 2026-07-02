from flask import Blueprint, request

from app.models import Application, ApplicationEnvironment, ReleaseRecord
from app.services.application_service import ApplicationService
from app.services.kubernetes_service import KubernetesService
from app.services.release_service import ReleaseService
from app.services.approval_service import ApprovalService
from app.utils.errors import ApiError
from app.utils.response import success
from app.extensions import db

bp = Blueprint("applications", __name__, url_prefix="/api/applications")


def get_application(app_id):
    app = Application.query.get(app_id)
    if not app:
        raise ApiError("应用不存在", 404, "APPLICATION_NOT_FOUND")
    return app


@bp.get("")
def list_applications():
    apps = Application.query.order_by(Application.created_at.desc()).all()
    return success([app.to_dict(include_spec=False) for app in apps])


@bp.post("")
def create_application():
    app = ApplicationService().create(request.get_json(silent=True) or {})
    return success(app.to_dict(), "应用分析完成", 201)


@bp.get("/<int:app_id>")
def application_detail(app_id):
    return success(get_application(app_id).to_dict())


@bp.post("/<int:app_id>/deploy")
def deploy_application(app_id):
    payload = request.get_json(silent=True) or {}
    app = get_application(app_id)
    environment_name = payload.get("environment", "dev")
    environment = ApplicationEnvironment.query.filter_by(
        application_id=app.id, environment_name=environment_name
    ).first()
    if environment and environment.approval_required:
        approval = ApprovalService().submit(
            app, payload, request.headers.get("X-User", "local-user")
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
        request.headers.get("X-User", "local-user"),
    )
    data = execution.to_dict()
    data["release"] = release.to_dict()
    return success(data, "PipelineRun 已创建", 201)


@bp.get("/<int:app_id>/executions")
def list_executions(app_id):
    app = get_application(app_id)
    return success([execution.to_dict() for execution in app.executions])


@bp.get("/<int:app_id>/releases")
def list_releases(app_id):
    releases = ReleaseService().list_releases(
        get_application(app_id), request.args.get("environment")
    )
    return success([release.to_dict() for release in releases])


@bp.post("/<int:app_id>/rollback")
def rollback_application(app_id):
    payload = request.get_json(silent=True) or {}
    if not payload.get("release_id"):
        raise ApiError("release_id 为必填字段")
    result, release = ReleaseService().rollback(
        get_application(app_id),
        payload["release_id"],
        payload.get("environment", "dev"),
        request.headers.get("X-User", "local-user"),
    )
    return success(
        {**result, "release": release.to_dict()},
        "Rollback completed",
    )


@bp.get("/<int:app_id>/status")
def application_status(app_id):
    app = get_application(app_id)
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
def pod_logs(app_id, pod_name):
    app = get_application(app_id)
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
def pod_yaml(app_id, pod_name):
    app = get_application(app_id)
    environment = request.args.get("environment", "dev")
    env = ApplicationEnvironment.query.filter_by(
        application_id=app.id, environment_name=environment
    ).first()
    namespace = env.namespace if env else app.namespace
    return success(KubernetesService().get_pod_manifest(pod_name, namespace))
