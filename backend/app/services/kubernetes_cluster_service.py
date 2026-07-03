from app.extensions import db
from app.models import KubernetesCluster
from app.utils.errors import ApiError


class KubernetesClusterService:
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
        if KubernetesCluster.query.filter_by(project_id=project.id, name=values["name"]).first():
            raise ApiError("集群名称已存在", 409, "CLUSTER_EXISTS")
        cluster = KubernetesCluster(project_id=project.id, **values)
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
        duplicate = KubernetesCluster.query.filter_by(
            project_id=cluster.project_id, name=values["name"]
        ).filter(KubernetesCluster.id != cluster.id).first()
        if duplicate:
            raise ApiError("集群名称已存在", 409, "CLUSTER_EXISTS")
        for key, value in values.items():
            setattr(cluster, key, value)
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

    @staticmethod
    def _validated(payload, current=None):
        name = str(payload.get("name", current.name if current else "")).strip()
        kube_context = str(payload.get(
            "kube_context", current.kube_context if current else ""
        )).strip()
        if not name or not kube_context:
            raise ApiError("name 和 kube_context 为必填字段")
        return {
            "name": name,
            "description": payload.get("description", current.description if current else None),
            "kube_context": kube_context,
            "namespace_prefix": str(payload.get(
                "namespace_prefix", current.namespace_prefix if current else ""
            ) or "").strip() or None,
            "api_server": str(payload.get(
                "api_server", current.api_server if current else ""
            ) or "").strip() or None,
            "is_default": bool(payload.get("is_default", current.is_default if current else False)),
            "is_active": bool(payload.get("is_active", current.is_active if current else True)),
        }

    @staticmethod
    def _clear_default(project_id, exclude_id=None):
        query = KubernetesCluster.query.filter_by(project_id=project_id, is_default=True)
        if exclude_id:
            query = query.filter(KubernetesCluster.id != exclude_id)
        query.update({"is_default": False}, synchronize_session=False)
