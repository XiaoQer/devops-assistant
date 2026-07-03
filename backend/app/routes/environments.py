from flask import Blueprint, request

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

bp = Blueprint("environments", __name__, url_prefix="/api")


def get_app(app_id):
    app = Application.query.get(app_id)
    if not app:
        raise ApiError("应用不存在", 404, "APPLICATION_NOT_FOUND")
    return app


def get_env(app_id, env_id):
    environment = ApplicationEnvironment.query.filter_by(
        id=env_id, application_id=app_id
    ).first()
    if not environment:
        raise ApiError("环境不存在", 404, "ENVIRONMENT_NOT_FOUND")
    return environment


@bp.get("/applications/<int:app_id>/environments")
def list_environments(app_id):
    items = EnvironmentService().list(get_app(app_id))
    return success([item.to_dict() for item in items])


@bp.post("/applications/<int:app_id>/environments")
def create_environment(app_id):
    payload = json_object(request.get_json(silent=True), required=True)
    require_string(payload, "environment_name")
    item = EnvironmentService().create(get_app(app_id), payload)
    return success(item.to_dict(), "环境已创建", 201)


@bp.patch("/applications/<int:app_id>/environments/<int:env_id>")
def update_environment(app_id, env_id):
    item = EnvironmentService().update(
        get_env(app_id, env_id), json_object(request.get_json(silent=True), required=True)
    )
    return success(item.to_dict(), "环境配置已更新")


@bp.delete("/applications/<int:app_id>/environments/<int:env_id>")
def delete_environment(app_id, env_id):
    EnvironmentService().delete(get_env(app_id, env_id))
    return success(None, "环境已删除")


@bp.post("/applications/<int:app_id>/environments/<int:env_id>/clone")
def clone_environment(app_id, env_id):
    payload = json_object(request.get_json(silent=True), required=True)
    environment_name = require_string(payload, "environment_name")
    item = EnvironmentService().clone(
        get_env(app_id, env_id), environment_name, payload.get("namespace")
    )
    return success(item.to_dict(), "环境已克隆", 201)


@bp.get("/applications/<int:app_id>/environments/<int:env_id>/export")
def export_environment(app_id, env_id):
    return success(get_env(app_id, env_id).to_dict())


@bp.get("/applications/<int:app_id>/environments/compare")
def compare_environments(app_id):
    left = get_env(app_id, require_query_positive_int(request.args, "left"))
    right = get_env(app_id, require_query_positive_int(request.args, "right"))
    return success(EnvironmentService.compare(left, right))


@bp.get("/applications/<int:app_id>/configs")
def list_configs(app_id):
    environment_id = request.args.get("environmentId", type=int)
    if not environment_id:
        raise ApiError("environmentId 为必填参数")
    service = ConfigurationService()
    items = service.list(app_id, environment_id, request.args.get("type"))
    return success([service.serialize(item) for item in items])


@bp.post("/applications/<int:app_id>/configs")
def create_config(app_id):
    payload = json_object(request.get_json(silent=True), required=True)
    environment_id = require_positive_int(payload, "environment_id")
    get_env(app_id, environment_id)
    service = ConfigurationService()
    item = service.create(
        app_id, environment_id, payload, request.headers.get("X-User", "local-user")
    )
    return success(service.serialize(item), "配置已保存", 201)


@bp.patch("/configs/<int:config_id>")
def update_config(config_id):
    item = ApplicationConfig.query.get(config_id)
    if not item:
        raise ApiError("配置不存在", 404, "CONFIG_NOT_FOUND")
    service = ConfigurationService()
    updated = service.update(
        item, json_object(request.get_json(silent=True), required=True),
        request.headers.get("X-User", "local-user"),
    )
    return success(service.serialize(updated), "配置已更新")


@bp.delete("/configs/<int:config_id>")
def delete_config(config_id):
    item = ApplicationConfig.query.get(config_id)
    if not item:
        raise ApiError("配置不存在", 404, "CONFIG_NOT_FOUND")
    ConfigurationService().delete(item)
    return success(None, "配置已删除")


@bp.get("/configs/<config_group_id>/history")
def config_history(config_group_id):
    service = ConfigurationService()
    return success([service.serialize(item) for item in service.history(config_group_id)])
