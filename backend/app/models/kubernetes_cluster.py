from app.extensions import db
from .project import utcnow


class KubernetesCluster(db.Model):
    __tablename__ = "kubernetes_clusters"
    __table_args__ = (
        db.UniqueConstraint("project_id", "name", name="uq_project_cluster_name"),
    )

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True
    )
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    kube_context = db.Column(db.String(200), nullable=False)
    environment_label = db.Column(db.String(80))
    encrypted_kubeconfig = db.Column(db.Text)
    namespace_prefix = db.Column(db.String(120))
    api_server = db.Column(db.String(300))
    connection_status = db.Column(
        db.String(20), default="untested", nullable=False
    )
    last_checked_at = db.Column(db.DateTime(timezone=True))
    kubernetes_version = db.Column(db.String(80))
    is_default = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    project = db.relationship("Project", back_populates="kubernetes_clusters")
    environments = db.relationship("ApplicationEnvironment", back_populates="kubernetes_cluster")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "kube_context": self.kube_context,
            "environment_label": self.environment_label,
            "has_kubeconfig": bool(self.encrypted_kubeconfig),
            "namespace_prefix": self.namespace_prefix,
            "api_server": self.api_server,
            "connection_status": self.connection_status,
            "last_checked_at": (
                self.last_checked_at.isoformat() if self.last_checked_at else None
            ),
            "kubernetes_version": self.kubernetes_version,
            "is_default": self.is_default,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
