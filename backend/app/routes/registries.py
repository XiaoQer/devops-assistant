from flask import Blueprint, request

from app.models import ContainerRegistry
from app.services.registry_service import RegistryService
from app.utils.errors import ApiError
from app.utils.response import success

bp = Blueprint("registries", __name__, url_prefix="/api/registries")


def get_registry(registry_id):
    item = ContainerRegistry.query.get(registry_id)
    if not item:
        raise ApiError("镜像仓库不存在", 404, "REGISTRY_NOT_FOUND")
    return item


@bp.get("")
def list_registries():
    return success([item.to_dict() for item in RegistryService().list()])


@bp.post("")
def create_registry():
    item = RegistryService().create(request.get_json(silent=True) or {})
    return success(item.to_dict(), "镜像仓库已创建", 201)


@bp.patch("/<int:registry_id>")
def update_registry(registry_id):
    item = RegistryService().update(
        get_registry(registry_id), request.get_json(silent=True) or {}
    )
    return success(item.to_dict(), "镜像仓库已更新")


@bp.delete("/<int:registry_id>")
def delete_registry(registry_id):
    RegistryService().delete(get_registry(registry_id))
    return success(None, "镜像仓库已删除")


@bp.post("/<int:registry_id>/default")
def set_default_registry(registry_id):
    item = RegistryService().set_default(get_registry(registry_id))
    return success(item.to_dict(), "默认镜像仓库已更新")
