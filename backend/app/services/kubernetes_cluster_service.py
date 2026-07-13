import base64
import hashlib
import ssl
from datetime import datetime, timezone
from urllib.parse import urlparse

import yaml
from cryptography.fernet import Fernet
from flask import current_app
from kubernetes.client.exceptions import ApiException
from kubernetes.config.config_exception import ConfigException
from urllib3.exceptions import (
    ConnectTimeoutError,
    MaxRetryError,
    ReadTimeoutError,
    SSLError as Urllib3SSLError,
)

from app.extensions import db
from app.models import KubernetesCluster
from app.utils.errors import ApiError
from .kubernetes_service import KubernetesService


class KubernetesClusterService:
    MAX_KUBECONFIG_BYTES = 1024 * 1024
    FORBIDDEN_USER_KEYS = {
        "exec", "client-certificate", "client-key", "tokenFile"
    }

    def list(self, project):
        return KubernetesCluster.query.filter_by(project_id=project.id).order_by(
            KubernetesCluster.is_default.desc(), KubernetesCluster.name
        ).all()

    def get(self, project, cluster_id):
        cluster = KubernetesCluster.query.filter_by(
            project_id=project.id, id=cluster_id
        ).first()
        if not cluster:
            raise ApiError("Kubernetes 集群不存在", 404, "CLUSTER_NOT_FOUND")
        return cluster

    def create(self, project, payload):
        values = self._validated(payload)
        kubeconfig = self._required_kubeconfig(payload.get("kubeconfig"))
        self.inspect_kubeconfig(kubeconfig, values["kube_context"])
        if KubernetesCluster.query.filter_by(project_id=project.id, name=values["name"]).first():
            raise ApiError("集群名称已存在", 409, "CLUSTER_EXISTS")
        cluster = KubernetesCluster(project_id=project.id, **values)
        cluster.encrypted_kubeconfig = self._encrypt(kubeconfig)
        db.session.add(cluster)
        db.session.flush()
        if cluster.is_default:
            self._clear_default(project.id, exclude_id=cluster.id)
        elif not self.get_default(project.id):
            cluster.is_default = True
        db.session.commit()
        return cluster

    def update(self, cluster, payload):
        values = self._validated(payload, cluster)
        incoming_kubeconfig = payload.get("kubeconfig")
        if incoming_kubeconfig is not None and not isinstance(incoming_kubeconfig, str):
            raise ApiError(
                "kubeconfig 必须是字符串", 400, "CLUSTER_KUBECONFIG_INVALID"
            )
        replacing_kubeconfig = bool(
            isinstance(incoming_kubeconfig, str) and incoming_kubeconfig.strip()
        )
        if replacing_kubeconfig:
            kubeconfig = incoming_kubeconfig
        elif cluster.encrypted_kubeconfig:
            kubeconfig = self._decrypt(cluster.encrypted_kubeconfig)
        else:
            raise ApiError(
                "请提供 kubeconfig", 400, "CLUSTER_KUBECONFIG_REQUIRED"
            )
        self.inspect_kubeconfig(kubeconfig, values["kube_context"])
        duplicate = KubernetesCluster.query.filter_by(
            project_id=cluster.project_id, name=values["name"]
        ).filter(KubernetesCluster.id != cluster.id).first()
        if duplicate:
            raise ApiError("集群名称已存在", 409, "CLUSTER_EXISTS")
        context_changed = values["kube_context"] != cluster.kube_context
        for key, value in values.items():
            setattr(cluster, key, value)
        if replacing_kubeconfig:
            cluster.encrypted_kubeconfig = self._encrypt(kubeconfig)
        if replacing_kubeconfig or context_changed:
            cluster.connection_status = "untested"
            cluster.last_checked_at = None
            cluster.kubernetes_version = None
            cluster.api_server = None
        if cluster.is_default:
            self._clear_default(cluster.project_id, exclude_id=cluster.id)
        db.session.commit()
        return cluster

    def delete(self, cluster):
        was_default = cluster.is_default
        project_id = cluster.project_id
        db.session.delete(cluster)
        db.session.flush()
        if was_default:
            replacement = KubernetesCluster.query.filter_by(
                project_id=project_id, is_active=True
            ).first()
            if replacement:
                replacement.is_default = True
        db.session.commit()

    def set_default(self, cluster):
        if not cluster.is_active:
            raise ApiError("停用的集群不能设为默认")
        self._clear_default(cluster.project_id, exclude_id=cluster.id)
        cluster.is_default = True
        db.session.commit()
        return cluster

    def get_default(self, project_id):
        return KubernetesCluster.query.filter_by(
            project_id=project_id,
            is_default=True,
            is_active=True,
        ).first()

    def credentials(self, cluster):
        if not cluster.encrypted_kubeconfig:
            raise ApiError(
                "集群尚未配置 kubeconfig",
                400,
                "CLUSTER_KUBECONFIG_REQUIRED",
            )
        return self._decrypt(cluster.encrypted_kubeconfig), cluster.kube_context

    def inspect_kubeconfig(self, value, context):
        if not isinstance(value, str) or not value.strip():
            raise ApiError(
                "kubeconfig 不能为空", 400, "CLUSTER_KUBECONFIG_INVALID"
            )
        if len(value.encode()) > self.MAX_KUBECONFIG_BYTES:
            raise ApiError(
                "kubeconfig 不能超过 1 MiB",
                400,
                "CLUSTER_KUBECONFIG_INVALID",
            )
        try:
            document = yaml.safe_load(value)
        except yaml.YAMLError as exc:
            raise ApiError(
                "无法解析 kubeconfig", 400, "CLUSTER_KUBECONFIG_INVALID"
            ) from exc
        if not isinstance(document, dict):
            raise ApiError(
                "kubeconfig 必须是对象", 400, "CLUSTER_KUBECONFIG_INVALID"
            )
        selected_context = str(context or "").strip()
        contexts = self._named_entries(document.get("contexts"), "context")
        selected = contexts.get(selected_context)
        if not selected:
            raise ApiError(
                "所选 kube context 不存在", 400, "CLUSTER_CONTEXT_NOT_FOUND"
            )
        clusters = self._named_entries(document.get("clusters"), "cluster")
        users = self._named_entries(document.get("users"), "user")
        cluster_config = clusters.get(selected.get("cluster"))
        user_config = users.get(selected.get("user"))
        if not isinstance(cluster_config, dict) or not isinstance(user_config, dict):
            raise ApiError(
                "kube context 引用无效", 400, "CLUSTER_KUBECONFIG_INVALID"
            )
        server = str(cluster_config.get("server", "")).strip()
        parsed_server = urlparse(server)
        if parsed_server.scheme != "https" or not parsed_server.hostname:
            raise ApiError(
                "Kubernetes API Server 必须使用 HTTPS",
                400,
                "CLUSTER_SERVER_INVALID",
            )
        if "certificate-authority" in cluster_config:
            raise ApiError(
                "kubeconfig 不能引用本地 CA 文件",
                400,
                "CLUSTER_KUBECONFIG_UNSAFE",
            )
        if self.FORBIDDEN_USER_KEYS.intersection(user_config):
            raise ApiError(
                "kubeconfig 不能执行命令或引用本地凭据文件",
                400,
                "CLUSTER_KUBECONFIG_UNSAFE",
            )
        return document

    def test_connection(self, kubeconfig, context):
        document = self.inspect_kubeconfig(kubeconfig, context)
        try:
            version = KubernetesService.from_kubeconfig(
                document, str(context).strip()
            ).version()
        except ConfigException as exc:
            raise ApiError(
                "kubeconfig 无法加载", 400, "CLUSTER_KUBECONFIG_INVALID"
            ) from exc
        except Exception as exc:
            return {
                "connected": False,
                "message": self._connection_failure_message(exc),
            }
        return {
            "connected": True,
            "message": "Kubernetes API 连接成功",
            "api_server": version["server"],
            "kubernetes_version": version["version"],
        }

    def test_saved_connection(self, cluster):
        kubeconfig, context = self.credentials(cluster)
        result = self.test_connection(kubeconfig, context)
        cluster.connection_status = (
            "connected" if result["connected"] else "failed"
        )
        cluster.last_checked_at = datetime.now(timezone.utc)
        cluster.kubernetes_version = result.get("kubernetes_version")
        if result["connected"]:
            cluster.api_server = result["api_server"]
        db.session.commit()
        return result

    @staticmethod
    def _validated(payload, current=None):
        name = str(payload.get("name", current.name if current else "")).strip()
        kube_context = str(payload.get(
            "kube_context", current.kube_context if current else ""
        )).strip()
        if not name or not kube_context:
            raise ApiError("name 和 kube_context 为必填字段")
        environment_label = payload.get(
            "environment_label", current.environment_label if current else None
        )
        if not isinstance(environment_label, str) or not environment_label.strip():
            raise ApiError(
                "环境标签为必填字段",
                400,
                "CLUSTER_ENVIRONMENT_LABEL_REQUIRED",
            )
        environment_label = environment_label.strip()
        if len(environment_label) > 80:
            raise ApiError(
                "环境标签不能超过 80 个字符",
                400,
                "CLUSTER_ENVIRONMENT_LABEL_INVALID",
            )
        return {
            "name": name,
            "description": payload.get("description", current.description if current else None),
            "kube_context": kube_context,
            "environment_label": environment_label,
            "namespace_prefix": str(payload.get(
                "namespace_prefix", current.namespace_prefix if current else ""
            ) or "").strip() or None,
            "api_server": current.api_server if current else None,
            "is_default": bool(payload.get("is_default", current.is_default if current else False)),
            "is_active": bool(payload.get("is_active", current.is_active if current else True)),
        }

    @staticmethod
    def _named_entries(value, config_key):
        if not isinstance(value, list):
            return {}
        result = {}
        for item in value:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            config_value = item.get(config_key)
            if isinstance(name, str) and isinstance(config_value, dict):
                result[name] = config_value
        return result

    @staticmethod
    def _required_kubeconfig(value):
        if not isinstance(value, str) or not value.strip():
            raise ApiError(
                "请提供 kubeconfig", 400, "CLUSTER_KUBECONFIG_REQUIRED"
            )
        return value

    @staticmethod
    def _connection_failure_message(exc):
        if isinstance(exc, ApiException) and exc.status in {401, 403}:
            return "Kubernetes 认证失败"
        if isinstance(exc, (ssl.SSLError, Urllib3SSLError)):
            return "Kubernetes 证书校验失败"
        if isinstance(exc, (TimeoutError, ConnectTimeoutError, ReadTimeoutError)):
            return "Kubernetes 连接超时"
        if isinstance(exc, MaxRetryError):
            reason = getattr(exc, "reason", None)
            if isinstance(reason, (ssl.SSLError, Urllib3SSLError)):
                return "Kubernetes 证书校验失败"
            if isinstance(reason, (TimeoutError, ConnectTimeoutError, ReadTimeoutError)):
                return "Kubernetes 连接超时"
            return "Kubernetes 网络不可达"
        if isinstance(exc, OSError):
            return "Kubernetes 网络不可达"
        if isinstance(exc, ApiException):
            return "Kubernetes API 请求失败"
        return "Kubernetes 连接失败"

    def _fernet(self):
        digest = hashlib.sha256(current_app.config["SECRET_KEY"].encode()).digest()
        return Fernet(base64.urlsafe_b64encode(digest))

    def _encrypt(self, value):
        return self._fernet().encrypt(value.encode()).decode()

    def _decrypt(self, value):
        try:
            return self._fernet().decrypt(value.encode()).decode()
        except Exception as exc:
            raise ApiError(
                "集群 kubeconfig 解密失败",
                500,
                "CLUSTER_KUBECONFIG_DECRYPTION_FAILED",
            ) from exc

    @staticmethod
    def _clear_default(project_id, exclude_id=None):
        query = KubernetesCluster.query.filter_by(project_id=project_id, is_default=True)
        if exclude_id:
            query = query.filter(KubernetesCluster.id != exclude_id)
        query.update({"is_default": False}, synchronize_session=False)
