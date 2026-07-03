from app.extensions import db
from .project import utcnow


class PipelineExecution(db.Model):
    __tablename__ = "pipeline_executions"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(
        db.Integer, db.ForeignKey("applications.id"), nullable=False, index=True
    )
    pipeline_run_name = db.Column(db.String(253), nullable=False, unique=True)
    status = db.Column(db.String(30), default="Pending")
    started_at = db.Column(db.DateTime(timezone=True))
    finished_at = db.Column(db.DateTime(timezone=True))
    image_url = db.Column(db.String(500))
    error_message = db.Column(db.Text)
    logs = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    application = db.relationship("Application", back_populates="executions")

    def to_dict(self):
        return {
            "id": self.id,
            "application_id": self.application_id,
            "pipeline_run_name": self.pipeline_run_name,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "image_url": self.image_url,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

