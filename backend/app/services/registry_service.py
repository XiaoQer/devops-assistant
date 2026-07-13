import base64
import hashlib
from datetime import datetime, timezone
from urllib.parse import urlparse

from cryptography.fernet import Fernet
from flask import current_app

from app.extensions import db
from app.models import ContainerRegistry
from app.utils.errors import ApiError
from .oci_registry_client import OCIRegistryClient


class RegistryService:
    PROVIDERS = {"acr", "harbor", "dockerhub", "ecr", "gcr", "generic", "ghcr"}

    def __init__(self, connectivity_client=None):
        self.connectivity_client = connectivity_client or OCIRegistryClient()

    def list(self, project):
        return ContainerRegistry.query.filter_by(project_id=project.id).order_by(
            ContainerRegistry.is_default.desc(), ContainerRegistry.name
        ).all()

    def get(self, project, registry_id):
        item = ContainerRegistry.query.filter_by(
            project_id=project.id,
            id=registry_id,
        ).first()
        if not item:
            raise ApiError(
                "镜像仓库不存在",
                404,
                "REGISTRY_NOT_FOUND",
            )
        return item

    def get_default(self, project_id=None):
        if project_id is not None:
            scoped = self._get_scoped_default(project_id)
            if scoped:
                return scoped
        return ContainerRegistry.query.filter_by(
            project_id=None, is_default=True, is_active=True
        ).first()

    def create(self, project, payload):
        values = self._validated(payload, require_credentials=True)
        if ContainerRegistry.query.filter_by(
            project_id=project.id, name=values["name"]
        ).first():
            raise ApiError("镜像仓库名称已存在", 409, "REGISTRY_EXISTS")
        password = str(payload.get("password") or "")
        item = ContainerRegistry(project_id=project.id, **values)
        item.encrypted_password = self._encrypt(password)
        db.session.add(item)
        if item.is_default:
            self._clear_default(project.id)
        elif not self._get_scoped_default(project.id):
            item.is_default = True
        db.session.commit()
        return item

    def update(self, item, payload):
        if payload.get("clear_credentials"):
            raise ApiError(
                "Registry 必须保留用户名和 Token",
                400,
                "REGISTRY_CREDENTIALS_REQUIRED",
            )
        values = self._validated(payload, item, require_credentials=True)
        duplicate = ContainerRegistry.query.filter_by(
            project_id=item.project_id,
            name=values["name"],
        ).filter(ContainerRegistry.id != item.id).first()
        if duplicate:
            raise ApiError("镜像仓库名称已存在", 409, "REGISTRY_EXISTS")

        password = str(payload.get("password") or "")
        connection_changed = (
            values["server"] != item.server
            or values["username"] != item.username
            or values["skip_tls_verify"] != item.skip_tls_verify
            or bool(password)
        )
        for key, value in values.items():
            setattr(item, key, value)
        if password:
            item.encrypted_password = self._encrypt(password)
        if not item.encrypted_password:
            raise ApiError(
                "Registry Token 为必填字段",
                400,
                "REGISTRY_CREDENTIALS_REQUIRED",
            )
        if connection_changed:
            self._reset_connection_state(item)
        if item.is_default:
            self._clear_default(item.project_id, item.id)
        db.session.commit()
        return item

    def delete(self, item):
        was_default = item.is_default
        project_id = item.project_id
        db.session.delete(item)
        db.session.flush()
        if was_default:
            replacement = ContainerRegistry.query.filter_by(
                project_id=project_id, is_active=True
            ).first()
            if replacement:
                replacement.is_default = True
        db.session.commit()

    def set_default(self, item):
        if not item.is_active:
            raise ApiError("停用的镜像仓库不能设为默认")
        self._clear_default(item.project_id, item.id)
        item.is_default = True
        db.session.commit()
        return item

    def test_connection(self, payload, current=None):
        server = self._normalize_server(payload.get(
            "server", current.server if current else ""
        ))
        username = str(payload.get(
            "username", current.username if current else ""
        ) or "").strip()
        password = str(payload.get("password") or "")
        if not password and current and current.encrypted_password:
            password = self._decrypt(current.encrypted_password)
        if not server or not username or not password:
            raise ApiError(
                "server、username 和 Token 为必填字段",
                400,
                "REGISTRY_CREDENTIALS_REQUIRED",
            )
        skip_tls_verify = bool(payload.get(
            "skip_tls_verify",
            current.skip_tls_verify if current else False,
        ))
        return self.connectivity_client.test(
            server,
            username,
            password,
            skip_tls_verify,
        )

    def test_saved_connection(self, item):
        result = self.test_connection({}, current=item)
        item.connection_status = "connected" if result["connected"] else "failed"
        item.last_checked_at = datetime.now(timezone.utc)
        item.last_connection_message = str(result["message"])[:300]
        db.session.commit()
        return result

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

    def _validated(self, payload, current=None, require_credentials=False):
        name = str(payload.get("name", current.name if current else "")).strip()
        server = self._normalize_server(payload.get(
            "server", current.server if current else ""
        ))
        provider = str(
            payload.get("provider", current.provider if current else "generic")
        ).lower()
        username = str(payload.get(
            "username", current.username if current else ""
        ) or "").strip()
        has_password = bool(str(payload.get("password") or "")) or bool(
            current and current.encrypted_password
        )
        if not name or not server:
            raise ApiError("name 和 server 为必填字段")
        if require_credentials and (not username or not has_password):
            raise ApiError(
                "Registry 用户名和 Token 为必填字段",
                400,
                "REGISTRY_CREDENTIALS_REQUIRED",
            )
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
            "username": username,
            "email": payload.get("email", current.email if current else None) or None,
            "pull_secret_name": payload.get(
                "pull_secret_name",
                current.pull_secret_name if current else "aegis-registry-credentials",
            ) or "aegis-registry-credentials",
            "skip_tls_verify": bool(payload.get(
                "skip_tls_verify",
                current.skip_tls_verify if current else False,
            )),
            "is_default": bool(payload.get(
                "is_default", current.is_default if current else False
            )),
            "is_active": bool(payload.get(
                "is_active", current.is_active if current else True
            )),
        }

    @staticmethod
    def _normalize_server(value):
        server = str(value or "").strip()
        return server.removeprefix("https://").removeprefix("http://").rstrip("/")

    @staticmethod
    def _reset_connection_state(item):
        item.connection_status = "untested"
        item.last_checked_at = None
        item.last_connection_message = None

    @staticmethod
    def _get_scoped_default(project_id):
        return ContainerRegistry.query.filter_by(
            project_id=project_id,
            is_default=True,
            is_active=True,
        ).first()

    @staticmethod
    def _clear_default(project_id=None, exclude_id=None):
        query = ContainerRegistry.query.filter_by(
            project_id=project_id,
            is_default=True,
        )
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
