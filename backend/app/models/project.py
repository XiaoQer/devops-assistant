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

