from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models import RuntimeOperationAudit
from app.utils.errors import ApiError

from .kubernetes_cluster_service import KubernetesClusterService


class RuntimeExecService:
    EXEC_PERMISSION_ROLES = {"owner", "admin"}

    def __init__(self, registry):
        self.registry = registry

    def create(self, context, pod_name, container, actor, reason):
        reason = str(reason or "").strip()
        approval_required = bool(getattr(context.environment, "approval_required", False))
        if approval_required and not self.has_permission(context.project, actor):
            raise ApiError("该审批环境没有终端操作权限", 403, "EXEC_PERMISSION_REQUIRED")
        if approval_required and not reason:
            raise ApiError("进入终端前必须填写操作原因", 400, "EXEC_REASON_REQUIRED")
        if not reason:
            reason = "免审批环境终端操作"
        containers = KubernetesClusterService().client(
            context.cluster
        ).list_application_pod_containers(
            pod_name, context.namespace, context.application.name
        )
        if container not in containers:
            raise ApiError("Container 不存在", 404, "CONTAINER_NOT_FOUND")

        audit = RuntimeOperationAudit.start(
            user_id=actor.id,
            project_id=context.project.id,
            application_id=context.application.id,
            environment=context.environment.environment_name,
            cluster_id=context.cluster.id,
            namespace=context.namespace,
            resource_kind="Pod",
            resource_name=pod_name,
            container=container,
            action="exec",
            reason=reason,
        )
        db.session.add(audit)
        db.session.commit()
        target = (
            context.project.id,
            context.application.id,
            context.environment.environment_name,
            pod_name,
            container,
        )
        ticket = self.registry.issue(
            actor.id,
            target,
            {
                "context_ref": {
                    "project_id": context.project.id,
                    "application_id": context.application.id,
                    "environment": context.environment.environment_name,
                },
                "pod": pod_name,
                "container": container,
                "audit_id": audit.id,
            },
        )
        return {
            "ticket": ticket,
            "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat(),
            "websocket_url": f"/api/runtime/exec/{ticket}",
        }

    @classmethod
    def has_permission(cls, project, actor):
        username = str(getattr(actor, "username", "") or "").strip().lower()
        for member in getattr(project, "members", []) or []:
            email = str(getattr(member, "email", "") or "").strip().lower()
            if email == username and getattr(member, "status", "active") == "active":
                return getattr(member, "role", "") in cls.EXEC_PERMISSION_ROLES
        return False
