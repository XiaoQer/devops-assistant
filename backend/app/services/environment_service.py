from copy import deepcopy

from app.extensions import db
from app.models import ApplicationEnvironment, KubernetesCluster
from app.utils.errors import ApiError


class EnvironmentService:
    ALLOWED_FIELDS = {
        "display_name", "cluster_name", "kube_context", "namespace", "replicas",
        "kubernetes_cluster_id",
        "ingress_domain", "cpu_request", "cpu_limit",
        "memory_request", "memory_limit", "storage_size", "config_maps",
        "secret_refs", "helm_values", "deploy_strategy", "max_unavailable",
        "max_surge", "approval_required",
    }

    def list(self, app, ensure_defaults=True):
        if ensure_defaults and not app.environments:
            self._create_defaults(app)
        return ApplicationEnvironment.query.filter_by(
            application_id=app.id
        ).order_by(ApplicationEnvironment.id).all()

    def create(self, app, payload):
        name = payload.get("environment_name", "").strip().lower()
        if not name:
            raise ApiError("environment_name 为必填字段")
        if ApplicationEnvironment.query.filter_by(
            application_id=app.id, environment_name=name
        ).first():
            raise ApiError("环境名称已存在", 409, "ENVIRONMENT_EXISTS")
        environment = ApplicationEnvironment(
            application_id=app.id,
            environment_name=name,
            namespace=payload.get("namespace") or f"{app.name}-{name}",
        )
        self._assign(environment, payload)
        db.session.add(environment)
        db.session.commit()
        return environment

    def update(self, environment, payload):
        self._assign(environment, payload)
        db.session.commit()
        return environment

    def delete(self, environment):
        if environment.environment_name == "prod":
            raise ApiError("Production 环境不可直接删除", 409, "PROTECTED_ENVIRONMENT")
        db.session.delete(environment)
        db.session.commit()

    def clone(self, environment, target_name, namespace=None):
        payload = environment.to_dict()
        for key in ("id", "created_at", "updated_at", "status", "application_id"):
            payload.pop(key, None)
        payload["environment_name"] = target_name
        payload["namespace"] = namespace or f"{environment.application.name}-{target_name}"
        return self.create(environment.application, deepcopy(payload))

    @staticmethod
    def compare(left, right):
        ignored = {"id", "environment_name", "display_name", "created_at", "updated_at"}
        left_data, right_data = left.to_dict(), right.to_dict()
        return [{
            "field": key,
            "left": left_data.get(key),
            "right": right_data.get(key),
            "changed": left_data.get(key) != right_data.get(key),
        } for key in sorted(set(left_data) | set(right_data)) if key not in ignored]

    def _create_defaults(self, app):
        default_cluster = KubernetesCluster.query.filter_by(
            project_id=app.project_id,
            is_default=True,
            is_active=True,
        ).first()
        namespace_prefix = (
            (default_cluster.namespace_prefix or "").strip("-")
            if default_cluster else ""
        )
        cluster_name = default_cluster.name if default_cluster else "default"
        kube_context = default_cluster.kube_context if default_cluster else None
        def namespaced(value):
            return f"{namespace_prefix}-{value}" if namespace_prefix else value
        definitions = [
            ("dev", "Development", namespaced(app.namespace), 1, False),
        ]
        for name, display, namespace, replicas, approval in definitions:
            db.session.add(ApplicationEnvironment(
                application_id=app.id,
                kubernetes_cluster_id=default_cluster.id if default_cluster else None,
                environment_name=name,
                display_name=display,
                cluster_name=cluster_name,
                kube_context=kube_context,
                namespace=namespace,
                replicas=replicas,
                approval_required=approval,
            ))
        db.session.commit()

    def _assign(self, environment, payload):
        if "kubernetes_cluster_id" in payload:
            cluster_id = payload.get("kubernetes_cluster_id")
            if cluster_id in (None, ""):
                environment.kubernetes_cluster_id = None
                environment.cluster_name = "default"
                environment.kube_context = None
            else:
                cluster = KubernetesCluster.query.get(int(cluster_id))
                project_id = environment.application.project_id if environment.application else None
                if not cluster or cluster.project_id != project_id:
                    raise ApiError("Kubernetes 集群不存在", 404, "CLUSTER_NOT_FOUND")
                environment.kubernetes_cluster_id = cluster.id
                environment.cluster_name = cluster.name
                environment.kube_context = cluster.kube_context
        for key in self.ALLOWED_FIELDS:
            if key in payload and key != "kubernetes_cluster_id":
                setattr(environment, key, payload[key])
