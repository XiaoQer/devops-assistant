from flask import Blueprint, g, request

from app.models import Application, ApplicationEnvironment, ApplicationConfig
from app.services.environment_service import EnvironmentService
from app.services.configuration_service import ConfigurationService
from app.utils.errors import ApiError
from app.utils.response import success
from app.utils.validation import (
    json_object,
    require_positive_int,
    require_query_positive_int,
    require_string,
)

bp = Blueprint(
    "environments",
    __name__,
    url_prefix="/api/projects/<int:project_id>/applications",
)


def get_app(project_id, app_id):
    app = Application.query.filter_by(id=app_id, project_id=project_id).first()
    if not app:
        raise ApiError("应用不存在", 404, "APPLICATION_NOT_FOUND")
    return app


def get_env(project_id, app_id, env_id):
    environment = (
        ApplicationEnvironment.query.join(Application)
        .filter(
            ApplicationEnvironment.id == env_id,
            ApplicationEnvironment.application_id == app_id,
            Application.project_id == project_id,
        )
        .first()
    )
    if not environment:
        raise ApiError("环境不存在", 404, "ENVIRONMENT_NOT_FOUND")
    return environment


@bp.get("/<int:app_id>/environments")
def list_environments(project_id, app_id):
    items = EnvironmentService().list(get_app(project_id, app_id))
    return success([item.to_dict() for item in items])


@bp.post("/<int:app_id>/environments")
def create_environment(project_id, app_id):
    payload = json_object(request.get_json(silent=True), required=True)
    require_string(payload, "environment_name")
    item = EnvironmentService().create(get_app(project_id, app_id), payload)
    return success(item.to_dict(), "环境已创建", 201)


@bp.patch("/<int:app_id>/environments/<int:env_id>")
def update_environment(project_id, app_id, env_id):
    item = EnvironmentService().update(
        get_env(project_id, app_id, env_id),
        json_object(request.get_json(silent=True), required=True),
    )
    return success(item.to_dict(), "环境配置已更新")


@bp.delete("/<int:app_id>/environments/<int:env_id>")
def delete_environment(project_id, app_id, env_id):
    EnvironmentService().delete(get_env(project_id, app_id, env_id))
    return success(None, "环境已删除")


@bp.post("/<int:app_id>/environments/<int:env_id>/clone")
def clone_environment(project_id, app_id, env_id):
    payload = json_object(request.get_json(silent=True), required=True)
    environment_name = require_string(payload, "environment_name")
    item = EnvironmentService().clone(
        get_env(project_id, app_id, env_id),
        environment_name,
        payload.get("namespace"),
    )
    return success(item.to_dict(), "环境已克隆", 201)


@bp.get("/<int:app_id>/environments/<int:env_id>/export")
def export_environment(project_id, app_id, env_id):
    return success(get_env(project_id, app_id, env_id).to_dict())


@bp.get("/<int:app_id>/environments/compare")
def compare_environments(project_id, app_id):
    get_app(project_id, app_id)
    left = get_env(
        project_id, app_id, require_query_positive_int(request.args, "left")
    )
    right = get_env(
        project_id, app_id, require_query_positive_int(request.args, "right")
    )
    return success(EnvironmentService.compare(left, right))


@bp.get("/<int:app_id>/configs")
def list_configs(project_id, app_id):
    get_app(project_id, app_id)
    environment_id = request.args.get("environmentId", type=int)
    if not environment_id:
        raise ApiError("environmentId 为必填参数")
    get_env(project_id, app_id, environment_id)
    service = ConfigurationService()
    items = service.list(app_id, environment_id, request.args.get("type"))
    return success([service.serialize(item) for item in items])


@bp.post("/<int:app_id>/configs")
def create_config(project_id, app_id):
    get_app(project_id, app_id)
    payload = json_object(request.get_json(silent=True), required=True)
    environment_id = require_positive_int(payload, "environment_id")
    get_env(project_id, app_id, environment_id)
    service = ConfigurationService()
    item = service.create(
        app_id, environment_id, payload, g.current_user.username
    )
    return success(service.serialize(item), "配置已保存", 201)


@bp.patch("/<int:app_id>/configs/<int:config_id>")
def update_config(project_id, app_id, config_id):
    get_app(project_id, app_id)
    item = (
        ApplicationConfig.query.join(Application)
        .filter(
            ApplicationConfig.id == config_id,
            ApplicationConfig.application_id == app_id,
            Application.project_id == project_id,
        )
        .first()
    )
    if not item:
        raise ApiError("配置不存在", 404, "CONFIG_NOT_FOUND")
    service = ConfigurationService()
    updated = service.update(
        item, json_object(request.get_json(silent=True), required=True),
        g.current_user.username,
    )
    return success(service.serialize(updated), "配置已更新")


@bp.delete("/<int:app_id>/configs/<int:config_id>")
def delete_config(project_id, app_id, config_id):
    get_app(project_id, app_id)
    item = (
        ApplicationConfig.query.join(Application)
        .filter(
            ApplicationConfig.id == config_id,
            ApplicationConfig.application_id == app_id,
            Application.project_id == project_id,
        )
        .first()
    )
    if not item:
        raise ApiError("配置不存在", 404, "CONFIG_NOT_FOUND")
    ConfigurationService().delete(item)
    return success(None, "配置已删除")


@bp.get("/<int:app_id>/configs/<config_group_id>/history")
def config_history(project_id, app_id, config_group_id):
    get_app(project_id, app_id)
    service = ConfigurationService()
    items = [
        item
        for item in service.history(config_group_id)
        if item.application_id == app_id
    ]
    if not items:
        raise ApiError("配置不存在", 404, "CONFIG_NOT_FOUND")
    return success([service.serialize(item) for item in items])
