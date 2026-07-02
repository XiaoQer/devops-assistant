import base64
import hashlib
from urllib.parse import urlparse

from cryptography.fernet import Fernet
from flask import current_app

from app.extensions import db
from app.models import ContainerRegistry
from app.utils.errors import ApiError


class RegistryService:
    PROVIDERS = {"acr", "harbor", "dockerhub", "ecr", "gcr", "generic"}

    def list(self):
        return ContainerRegistry.query.order_by(
            ContainerRegistry.is_default.desc(), ContainerRegistry.name
        ).all()

    def get_default(self):
        return ContainerRegistry.query.filter_by(
            is_default=True, is_active=True
        ).first()

    def create(self, payload):
        values = self._validated(payload)
        if ContainerRegistry.query.filter_by(name=values["name"]).first():
            raise ApiError("镜像仓库名称已存在", 409, "REGISTRY_EXISTS")
        item = ContainerRegistry(**values)
        if payload.get("password"):
            item.encrypted_password = self._encrypt(payload["password"])
        db.session.add(item)
        if item.is_default:
            self._clear_default()
        elif not self.get_default():
            item.is_default = True
        db.session.commit()
        return item

    def update(self, item, payload):
        values = self._validated(payload, item)
        for key, value in values.items():
            setattr(item, key, value)
        if payload.get("password"):
            item.encrypted_password = self._encrypt(payload["password"])
        if payload.get("clear_credentials"):
            item.encrypted_password = None
            item.username = None
        if item.is_default:
            self._clear_default(item.id)
        db.session.commit()
        return item

    def delete(self, item):
        was_default = item.is_default
        db.session.delete(item)
        db.session.flush()
        if was_default:
            replacement = ContainerRegistry.query.filter_by(is_active=True).first()
            if replacement:
                replacement.is_default = True
        db.session.commit()

    def set_default(self, item):
        if not item.is_active:
            raise ApiError("停用的镜像仓库不能设为默认")
        self._clear_default(item.id)
        item.is_default = True
        db.session.commit()
        return item

    def credentials(self, item):
        if not item or not item.encrypted_password:
            return None
        return {
            "server": self.auth_server(item),
            "username": item.username or "",
            "password": self._decrypt(item.encrypted_password),
            "email": item.email or "",
            "secret_name": item.pull_secret_name,
        }

    @staticmethod
    def auth_server(item):
        if item.provider == "dockerhub" and item.server in {
            "docker.io", "index.docker.io"
        }:
            return "https://index.docker.io/v1/"
        return item.server

    def _validated(self, payload, current=None):
        name = str(payload.get("name", current.name if current else "")).strip()
        server = str(payload.get("server", current.server if current else "")).strip()
        server = server.removeprefix("https://").removeprefix("http://").rstrip("/")
        provider = str(
            payload.get("provider", current.provider if current else "generic")
        ).lower()
        if not name or not server:
            raise ApiError("name 和 server 为必填字段")
        if provider not in self.PROVIDERS:
            raise ApiError("不支持的镜像仓库类型")
        if "/" in server or not urlparse(f"//{server}").hostname:
            raise ApiError("server 只能填写仓库域名，例如 company.azurecr.io")
        return {
            "name": name,
            "provider": provider,
            "server": server,
            "namespace": str(payload.get(
                "namespace", current.namespace if current else ""
            ) or "").strip("/"),
            "username": payload.get(
                "username", current.username if current else None
            ) or None,
            "email": payload.get("email", current.email if current else None) or None,
            "pull_secret_name": payload.get(
                "pull_secret_name",
                current.pull_secret_name if current else "aegis-registry-credentials",
            ) or "aegis-registry-credentials",
            "is_default": bool(payload.get(
                "is_default", current.is_default if current else False
            )),
            "is_active": bool(payload.get(
                "is_active", current.is_active if current else True
            )),
        }

    def _clear_default(self, exclude_id=None):
        query = ContainerRegistry.query.filter_by(is_default=True)
        if exclude_id:
            query = query.filter(ContainerRegistry.id != exclude_id)
        query.update({"is_default": False}, synchronize_session=False)

    def _fernet(self):
        digest = hashlib.sha256(current_app.config["SECRET_KEY"].encode()).digest()
        return Fernet(base64.urlsafe_b64encode(digest))

    def _encrypt(self, value):
        return self._fernet().encrypt(str(value).encode()).decode()

    def _decrypt(self, value):
        try:
            return self._fernet().decrypt(value.encode()).decode()
        except Exception as exc:
            raise ApiError(
                "镜像仓库凭证解密失败", 500, "REGISTRY_DECRYPTION_FAILED"
            ) from exc
