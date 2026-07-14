from app.extensions import db
from .project import utcnow


class ApplicationReleaseTarget(db.Model):
    __tablename__ = "application_release_targets"
    __table_args__ = (db.UniqueConstraint("batch_id", "environment_id", name="uq_release_target_environment"),)

    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey("application_release_batches.id", ondelete="CASCADE"), nullable=False, index=True)
    environment_id = db.Column(db.Integer, db.ForeignKey("application_environments.id", ondelete="CASCADE"), nullable=False, index=True)
    build_version_id = db.Column(db.Integer, db.ForeignKey("application_build_versions.id"), nullable=True, index=True)
    pipeline_run_name = db.Column(db.String(253), index=True)
    status = db.Column(db.String(30), default="Pending", nullable=False, index=True)
    approval_id = db.Column(db.Integer, db.ForeignKey("approval_records.id"), nullable=True, index=True)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    batch = db.relationship("ApplicationReleaseBatch", back_populates="targets")
    environment = db.relationship("ApplicationEnvironment")

    def to_dict(self):
        env = self.environment
        return {
            "id": self.id, "batch_id": self.batch_id, "environment_id": self.environment_id,
            "environment": env.environment_name if env else None,
            "display_name": env.display_name if env else None,
            "namespace": env.namespace if env else None,
            "build_version_id": self.build_version_id,
            "pipeline_run_name": self.pipeline_run_name, "status": self.status,
            "approval_id": self.approval_id, "error_message": self.error_message,
            "created_at": self.created_at.isoformat(), "updated_at": self.updated_at.isoformat(),
        }
