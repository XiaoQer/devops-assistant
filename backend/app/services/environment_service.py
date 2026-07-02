from copy import deepcopy

from app.extensions import db
from app.models import ApplicationEnvironment
from app.utils.errors import ApiError


class EnvironmentService:
    ALLOWED_FIELDS = {
        "display_name", "cluster_name", "kube_context", "namespace", "replicas",
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
        definitions = [
            ("dev", "Development", app.namespace, 1, False),
            ("test", "Test", f"{app.name}-test", 1, False),
            ("staging", "Staging", f"{app.name}-staging", 2, False),
            ("prod", "Production", f"{app.name}-prod", 3, True),
        ]
        for name, display, namespace, replicas, approval in definitions:
            db.session.add(ApplicationEnvironment(
                application_id=app.id,
                environment_name=name,
                display_name=display,
                namespace=namespace,
                replicas=replicas,
                approval_required=approval,
            ))
        db.session.commit()

    def _assign(self, environment, payload):
        for key in self.ALLOWED_FIELDS:
            if key in payload:
                setattr(environment, key, payload[key])
