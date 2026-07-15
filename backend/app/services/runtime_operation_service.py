from app.extensions import db
from app.models import RuntimeOperationAudit
from app.utils.errors import ApiError

from .kubernetes_cluster_service import KubernetesClusterService


class RuntimeOperationService:
    def _client(self, context):
        return KubernetesClusterService().client(context.cluster)

    @staticmethod
    def _require_confirmation(confirmed):
        if confirmed is not True:
            raise ApiError(
                "该运行态操作需要显式确认",
                409,
                "CONFIRMATION_REQUIRED",
            )

    @staticmethod
    def _audit(context, actor, kind, name, action, reason=None, container=None):
        audit = RuntimeOperationAudit.start(
            user_id=actor.id,
            project_id=context.project.id,
            application_id=context.application.id,
            environment=context.environment.environment_name,
            cluster_id=context.cluster.id,
            namespace=context.namespace,
            resource_kind=kind,
            resource_name=name,
            container=container,
            action=action,
            reason=reason,
        )
        db.session.add(audit)
        db.session.commit()
        return audit

    @staticmethod
    def _finish(audit, status, message=None):
        audit.finish(status, message) if message else audit.finish(status)
        db.session.commit()

    def deployment_manifest(self, context, deployment_name):
        return self._client(context).get_application_deployment_manifest(
            deployment_name, context.namespace, context.application.name
        )

    def restart_deployment(
        self, context, deployment_name, actor, confirmed, reason=None
    ):
        self._require_confirmation(confirmed)
        audit = self._audit(
            context, actor, "Deployment", deployment_name, "restart", reason
        )
        try:
            result = self._client(context).restart_deployment(
                deployment_name, context.namespace, context.application.name
            )
        except Exception as exc:
            message = exc.message if isinstance(exc, ApiError) else "Kubernetes 操作失败"
            self._finish(audit, "Failed", message)
            raise
        self._finish(audit, "Succeeded")
        return result

    def delete_pod(self, context, pod_name, actor, confirmed, reason=None):
        self._require_confirmation(confirmed)
        audit = self._audit(context, actor, "Pod", pod_name, "delete", reason)
        try:
            result = self._client(context).delete_application_pod(
                pod_name, context.namespace, context.application.name
            )
        except Exception as exc:
            message = exc.message if isinstance(exc, ApiError) else "Kubernetes 操作失败"
            self._finish(audit, "Failed", message)
            raise
        self._finish(audit, "Succeeded")
        return result
