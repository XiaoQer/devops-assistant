import base64
import hashlib

from cryptography.fernet import Fernet
from flask import current_app

from app.extensions import db
from app.models import ApplicationConfig, ApplicationEnvironment
from app.utils.errors import ApiError
from .registry_service import RegistryService


class ConfigurationService:
    TYPES = {"env", "configmap", "secret", "registry_secret", "resource", "ingress"}
    RESOURCE_KEYS = {
        "replicas", "cpu_request", "cpu_limit", "memory_request", "memory_limit",
        "storage_size", "deploy_strategy", "max_unavailable", "max_surge",
    }
    INGRESS_KEYS = {"host", "path", "service_port"}

    def list(self, app_id, environment_id, config_type=None):
        query = ApplicationConfig.query.filter_by(
            application_id=app_id, environment_id=environment_id, is_active=True
        )
        if config_type:
            query = query.filter_by(config_type=config_type)
        return query.order_by(ApplicationConfig.config_type, ApplicationConfig.config_key).all()

    def create(self, app_id, environment_id, payload, user):
        config_type = payload.get("config_type", "env")
        if config_type not in self.TYPES:
            raise ApiError("不支持的配置类型")
        key = payload.get("config_key", "").strip()
        if not key:
            raise ApiError("config_key 为必填字段")
        if config_type == "resource" and key not in self.RESOURCE_KEYS:
            raise ApiError("不支持的资源参数")
        if config_type == "ingress" and key not in self.INGRESS_KEYS:
            raise ApiError("不支持的 Ingress 参数")
        existing = ApplicationConfig.query.filter_by(
            application_id=app_id,
            environment_id=environment_id,
            config_type=config_type,
            config_key=key,
            is_active=True,
        ).first()
        if existing:
            raise ApiError(
                f"配置 {key} 已存在，请直接编辑已有配置",
                409,
                "CONFIG_EXISTS",
            )
        item = ApplicationConfig(
            application_id=app_id,
            environment_id=environment_id,
            config_type=config_type,
            config_key=key,
            encrypted_value=self._encrypt(str(payload.get("value", ""))),
            value_format=payload.get("value_format", "text"),
            is_secret=config_type in {"secret", "registry_secret"} or payload.get("is_secret", False),
            changed_by=user,
            change_message=payload.get("change_message"),
        )
        db.session.add(item)
        db.session.commit()
        return item

    def update(self, current, payload, user):
        next_key = payload.get("config_key", current.config_key).strip()
        if not next_key:
            raise ApiError("config_key 为必填字段")
        if next_key != current.config_key:
            duplicate = ApplicationConfig.query.filter_by(
                application_id=current.application_id,
                environment_id=current.environment_id,
                config_type=current.config_type,
                config_key=next_key,
                is_active=True,
            ).filter(ApplicationConfig.id != current.id).first()
            if duplicate:
                raise ApiError(
                    f"配置 {next_key} 已存在，请直接编辑已有配置",
                    409,
                    "CONFIG_EXISTS",
                )
        current.is_active = False
        item = ApplicationConfig(
            config_group_id=current.config_group_id,
            application_id=current.application_id,
            environment_id=current.environment_id,
            config_type=current.config_type,
            config_key=next_key,
            encrypted_value=(
                self._encrypt(str(payload["value"]))
                if "value" in payload else current.encrypted_value
            ),
            value_format=payload.get("value_format", current.value_format),
            version=current.version + 1,
            is_secret=current.is_secret,
            changed_by=user,
            change_message=payload.get("change_message"),
        )
        db.session.add(item)
        db.session.commit()
        return item

    def history(self, app_id, config_group_id):
        return (
            ApplicationConfig.query.join(
                ApplicationEnvironment,
                ApplicationConfig.environment_id == ApplicationEnvironment.id,
            )
            .filter(
                ApplicationConfig.application_id == app_id,
                ApplicationEnvironment.application_id == app_id,
                ApplicationConfig.config_group_id == config_group_id,
            )
            .order_by(ApplicationConfig.version.desc())
            .all()
        )

    def delete(self, item):
        item.is_active = False
        db.session.commit()

    def serialize(self, item, reveal=False):
        value = self._decrypt(item.encrypted_value) if reveal or not item.is_secret else None
        return item.to_dict(value=value)

    def materialize(self, app, environment, kubernetes_service, registry=None):
        """Render active database configuration into Kubernetes resources."""
        items = self.list(app.id, environment.id)
        grouped = {}
        for item in items:
            grouped.setdefault(item.config_type, {})[item.config_key] = self._decrypt(
                item.encrypted_value
            )
        kubernetes_service.ensure_namespace(environment.namespace)
        config_map_name = f"{app.name}-config"
        env_config_map_name = f"{app.name}-env"
        secret_name = f"{app.name}-secret"
        kubernetes_service.apply_config_map(config_map_name, environment.namespace, grouped.get("configmap", {}))
        kubernetes_service.apply_config_map(env_config_map_name, environment.namespace, grouped.get("env", {}))
        kubernetes_service.apply_secret(
            secret_name, environment.namespace, grouped.get("secret", {})
        )
        resource_overrides = {
            key: value
            for key, value in grouped.get("resource", {}).items()
            if key in self.RESOURCE_KEYS
        }
        ingress = grouped.get("ingress", {})
        if ingress.get("host"):
            resource_overrides["ingress_host"] = ingress["host"]
        if ingress.get("path"):
            resource_overrides["ingress_path"] = ingress["path"]
        if ingress.get("service_port"):
            resource_overrides["ingress_service_port"] = ingress["service_port"]
        registry_secret_name = None
        global_credentials = None
        if registry:
            global_credentials = RegistryService().credentials(registry)
        legacy_registry = grouped.get("registry_secret", {})
        required = {"REGISTRY_SERVER", "REGISTRY_USERNAME", "REGISTRY_PASSWORD"}
        if global_credentials or required.issubset(legacy_registry):
            credentials = global_credentials or {
                "server": legacy_registry["REGISTRY_SERVER"],
                "username": legacy_registry["REGISTRY_USERNAME"],
                "password": legacy_registry["REGISTRY_PASSWORD"],
                "email": legacy_registry.get("REGISTRY_EMAIL", ""),
                "secret_name": f"{app.name}-registry",
            }
            registry_secret_name = credentials["secret_name"]
            kubernetes_service.apply_registry_secret(
                registry_secret_name,
                environment.namespace,
                credentials["server"],
                credentials["username"],
                credentials["password"],
                credentials.get("email", ""),
            )
        return {
            "config_map_name": config_map_name,
            "env_config_map_name": env_config_map_name,
            "secret_name": secret_name,
            "registry_secret_name": registry_secret_name,
            "resource_overrides": resource_overrides,
        }

    def materialize_build_registry(
        self, registry, central_kubernetes, tekton_namespace
    ):
        credentials = RegistryService().credentials(registry)
        if not credentials:
            raise ApiError(
                "Registry 凭据不可用",
                409,
                "REGISTRY_CREDENTIALS_REQUIRED",
            )
        central_kubernetes.ensure_namespace(tekton_namespace)
        central_kubernetes.apply_registry_secret(
            credentials["secret_name"],
            tekton_namespace,
            credentials["server"],
            credentials["username"],
            credentials["password"],
            credentials.get("email", ""),
        )
        return credentials["secret_name"]

    def _fernet(self):
        digest = hashlib.sha256(current_app.config["SECRET_KEY"].encode()).digest()
        return Fernet(base64.urlsafe_b64encode(digest))

    def _encrypt(self, value):
        return self._fernet().encrypt(value.encode()).decode()

    def _decrypt(self, value):
        if not value:
            return ""
        try:
            return self._fernet().decrypt(value.encode()).decode()
        except Exception as exc:
            raise ApiError("配置解密失败", 500, "CONFIG_DECRYPTION_FAILED") from exc
