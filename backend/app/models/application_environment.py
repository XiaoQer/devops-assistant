from app.extensions import db
from .project import utcnow


class ApplicationEnvironment(db.Model):
    __tablename__ = "application_environments"
    __table_args__ = (
        db.UniqueConstraint(
            "application_id", "environment_name", name="uq_application_environment"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(
        db.Integer, db.ForeignKey("applications.id"), nullable=False, index=True
    )
    environment_name = db.Column(db.String(30), nullable=False, index=True)
    display_name = db.Column(db.String(80))
    cluster_name = db.Column(db.String(120), default="default")
    kube_context = db.Column(db.String(200))
    namespace = db.Column(db.String(120), nullable=False)
    replicas = db.Column(db.Integer, default=1, nullable=False)
    image_registry = db.Column(db.String(300))
    ingress_domain = db.Column(db.String(300))
    cpu_request = db.Column(db.String(30), default="100m")
    cpu_limit = db.Column(db.String(30), default="500m")
    memory_request = db.Column(db.String(30), default="128Mi")
    memory_limit = db.Column(db.String(30), default="512Mi")
    storage_size = db.Column(db.String(30))
    config_maps = db.Column(db.JSON, default=dict)
    secret_refs = db.Column(db.JSON, default=list)
    helm_values = db.Column(db.JSON, default=dict)
    deploy_strategy = db.Column(db.String(30), default="RollingUpdate")
    max_unavailable = db.Column(db.String(20), default="25%")
    max_surge = db.Column(db.String(20), default="25%")
    approval_required = db.Column(db.Boolean, default=False, nullable=False)
    status = db.Column(db.String(30), default="Unknown", nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    application = db.relationship("Application", back_populates="environments")
    configs = db.relationship(
        "ApplicationConfig",
        back_populates="environment",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
            if column.name not in {"created_at", "updated_at"}
        } | {
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

