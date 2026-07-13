from app.extensions import db
from .project import utcnow


class ContainerRegistry(db.Model):
    __tablename__ = "container_registries"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=True, index=True)
    name = db.Column(db.String(120), nullable=False)
    provider = db.Column(db.String(30), default="generic", nullable=False)
    server = db.Column(db.String(300), nullable=False)
    namespace = db.Column(db.String(200))
    username = db.Column(db.String(300))
    encrypted_password = db.Column(db.Text)
    email = db.Column(db.String(300))
    pull_secret_name = db.Column(
        db.String(253), default="aegis-registry-credentials", nullable=False
    )
    skip_tls_verify = db.Column(db.Boolean, default=False, nullable=False)
    connection_status = db.Column(
        db.String(20), default="untested", nullable=False
    )
    last_checked_at = db.Column(db.DateTime(timezone=True))
    last_connection_message = db.Column(db.String(300))
    is_default = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    project = db.relationship("Project", back_populates="registries")

    @property
    def image_prefix(self):
        parts = [self.server.rstrip("/")]
        if self.namespace:
            parts.append(self.namespace.strip("/"))
        return "/".join(parts)

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "project_name": self.project.name if self.project else None,
            "name": self.name,
            "provider": self.provider,
            "server": self.server,
            "namespace": self.namespace or "",
            "image_prefix": self.image_prefix,
            "username": self.username or "",
            "has_credentials": bool(self.encrypted_password),
            "email": self.email or "",
            "pull_secret_name": self.pull_secret_name,
            "skip_tls_verify": self.skip_tls_verify,
            "connection_status": self.connection_status,
            "last_checked_at": (
                self.last_checked_at.isoformat() if self.last_checked_at else None
            ),
            "last_connection_message": self.last_connection_message,
            "is_default": self.is_default,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
