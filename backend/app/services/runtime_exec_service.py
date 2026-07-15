from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models import RuntimeOperationAudit
from app.utils.errors import ApiError

from .kubernetes_cluster_service import KubernetesClusterService


class RuntimeExecService:
    def __init__(self, registry):
        self.registry = registry

    def create(self, context, pod_name, container, actor, reason):
        reason = str(reason or "").strip()
        if not reason:
            raise ApiError("进入终端前必须填写操作原因", 400, "EXEC_REASON_REQUIRED")
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
                "context": context,
                "pod": pod_name,
                "container": container,
                "audit": audit,
            },
        )
        return {
            "ticket": ticket,
            "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat(),
            "websocket_url": f"/api/runtime/exec/{ticket}",
        }
