from flask import Blueprint, request

from app.models import Project
from app.services.kubernetes_cluster_service import KubernetesClusterService
from app.services.project_service import ProjectService
from app.utils.response import success
from app.utils.validation import json_object, require_fields

bp = Blueprint("projects", __name__, url_prefix="/api/projects")

project_service = ProjectService()
cluster_service = KubernetesClusterService()


def get_project(project_id):
    return project_service.get(project_id)


@bp.get("")
def list_projects():
    return success([project.to_dict(include_stats=True) for project in project_service.list()])


@bp.post("")
def create_project():
    payload = json_object(request.get_json(silent=True), required=True)
    require_fields(payload, "key", "name")
    project = project_service.create(payload)
    return success(project.to_dict(include_stats=True), "项目已创建", 201)


@bp.get("/<int:project_id>")
def project_detail(project_id):
    project = get_project(project_id)
    return success(project.to_dict(include_stats=True))


@bp.patch("/<int:project_id>")
def update_project(project_id):
    project = project_service.update(
        get_project(project_id),
        json_object(request.get_json(silent=True), required=True),
    )
    return success(project.to_dict(include_stats=True), "项目已更新")


@bp.get("/<int:project_id>/members")
def list_members(project_id):
    project = get_project(project_id)
    return success([item.to_dict() for item in project_service.list_members(project)])


@bp.post("/<int:project_id>/members")
def create_member(project_id):
    project = get_project(project_id)
    payload = json_object(request.get_json(silent=True), required=True)
    require_fields(payload, "name", "email")
    item = project_service.add_member(project, payload)
    return success(item.to_dict(), "项目成员已添加", 201)


@bp.patch("/<int:project_id>/members/<int:member_id>")
def update_member(project_id, member_id):
    project = get_project(project_id)
    member = project_service.get_member(project, member_id)
    item = project_service.update_member(
        member,
        json_object(request.get_json(silent=True), required=True),
    )
    return success(item.to_dict(), "项目成员已更新")


@bp.delete("/<int:project_id>/members/<int:member_id>")
def delete_member(project_id, member_id):
    project = get_project(project_id)
    project_service.delete_member(project_service.get_member(project, member_id))
    return success(None, "项目成员已移除")


@bp.get("/<int:project_id>/clusters")
def list_clusters(project_id):
    project = get_project(project_id)
    return success([item.to_dict() for item in cluster_service.list(project)])


@bp.post("/<int:project_id>/clusters")
def create_cluster(project_id):
    project = get_project(project_id)
    payload = json_object(request.get_json(silent=True), required=True)
    require_fields(payload, "name", "kube_context")
    item = cluster_service.create(project, payload)
    return success(item.to_dict(), "Kubernetes 集群已添加", 201)


@bp.patch("/<int:project_id>/clusters/<int:cluster_id>")
def update_cluster(project_id, cluster_id):
    project = get_project(project_id)
    item = cluster_service.update(
        cluster_service.get(project, cluster_id),
        json_object(request.get_json(silent=True), required=True),
    )
    return success(item.to_dict(), "Kubernetes 集群已更新")


@bp.delete("/<int:project_id>/clusters/<int:cluster_id>")
def delete_cluster(project_id, cluster_id):
    project = get_project(project_id)
    cluster_service.delete(cluster_service.get(project, cluster_id))
    return success(None, "Kubernetes 集群已删除")


@bp.post("/<int:project_id>/clusters/<int:cluster_id>/default")
def set_default_cluster(project_id, cluster_id):
    project = get_project(project_id)
    item = cluster_service.set_default(cluster_service.get(project, cluster_id))
    return success(item.to_dict(), "默认 Kubernetes 集群已更新")

