from app.extensions import db
from .project import utcnow


class RuntimeOperationAudit(db.Model):
    __tablename__ = "runtime_operation_audits"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True
    )
    application_id = db.Column(
        db.Integer, db.ForeignKey("applications.id"), nullable=False, index=True
    )
    environment = db.Column(db.String(30), nullable=False)
    cluster_id = db.Column(
        db.Integer, db.ForeignKey("kubernetes_clusters.id"), nullable=False
    )
    namespace = db.Column(db.String(253), nullable=False)
    resource_kind = db.Column(db.String(30), nullable=False)
    resource_name = db.Column(db.String(253), nullable=False)
    container = db.Column(db.String(253))
    action = db.Column(db.String(40), nullable=False)
    reason = db.Column(db.String(500))
    status = db.Column(db.String(30), nullable=False, default="Running", index=True)
    error_message = db.Column(db.String(500))
    started_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    finished_at = db.Column(db.DateTime(timezone=True))

    @classmethod
    def start(cls, **values):
        return cls(status="Running", started_at=utcnow(), **values)

    def finish(self, status, error_message=None):
        self.status = status
        self.error_message = error_message
        self.finished_at = utcnow()
        return self

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "application_id": self.application_id,
            "environment": self.environment,
            "cluster_id": self.cluster_id,
            "namespace": self.namespace,
            "resource_kind": self.resource_kind,
            "resource_name": self.resource_name,
            "container": self.container,
            "action": self.action,
            "reason": self.reason,
            "status": self.status,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }
