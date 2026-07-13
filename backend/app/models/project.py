from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), nullable=False, unique=True, index=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(30), default="active", nullable=False, index=True)
    business_owner = db.Column(db.String(120))
    billing_owner = db.Column(db.String(120))
    github_group = db.Column(db.String(255))
    github_default_visibility = db.Column(db.String(30), default="private", nullable=False)
    aliyun_account_id = db.Column(db.String(64))
    aliyun_resource_group_id = db.Column(db.String(120))
    aliyun_region = db.Column(db.String(64))
    aliyun_vpc_id = db.Column(db.String(120))
    aliyun_binding_status = db.Column(
        db.String(30), default="unbound", nullable=False, index=True
    )
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    applications = db.relationship("Application", back_populates="project")
    members = db.relationship(
        "ProjectMember",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProjectMember.id",
    )
    kubernetes_clusters = db.relationship(
        "KubernetesCluster",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="KubernetesCluster.id",
    )
    registries = db.relationship(
        "ContainerRegistry",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ContainerRegistry.name",
    )

    def to_dict(self, include_stats=False):
        data = {
            "id": self.id,
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "business_owner": self.business_owner,
            "billing_owner": self.billing_owner,
            "github_group": self.github_group,
            "github_default_visibility": self.github_default_visibility,
            "aliyun_account_id": self.aliyun_account_id,
            "aliyun_resource_group_id": self.aliyun_resource_group_id,
            "aliyun_region": self.aliyun_region,
            "aliyun_vpc_id": self.aliyun_vpc_id,
            "aliyun_binding_status": self.aliyun_binding_status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if include_stats:
            data.update({
                "applications_count": len(self.applications),
                "members_count": len(self.members),
                "clusters_count": len(self.kubernetes_clusters),
                "registries_count": len(self.registries),
            })
        return data
