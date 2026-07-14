from app.extensions import db
from .project import utcnow


class ApprovalRecord(db.Model):
    __tablename__ = "approval_records"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(
        db.Integer, db.ForeignKey("applications.id"), nullable=False, index=True
    )
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    environment = db.Column(db.String(30), nullable=False, index=True)
    namespace = db.Column(db.String(120), nullable=False)
    kubernetes_cluster_id = db.Column(
        db.Integer, db.ForeignKey("kubernetes_clusters.id"), nullable=True
    )
    image_name = db.Column(db.String(300), nullable=False)
    image_tag = db.Column(db.String(120), nullable=False)
    git_branch = db.Column(db.String(120))
    git_commit = db.Column(db.String(64))
    applicant = db.Column(db.String(120), nullable=False)
    approver = db.Column(db.String(120))
    status = db.Column(db.String(30), default="Pending", nullable=False, index=True)
    comment = db.Column(db.Text)
    pipeline_run_name = db.Column(db.String(253))
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    approved_at = db.Column(db.DateTime(timezone=True))
    rejected_at = db.Column(db.DateTime(timezone=True))
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    application = db.relationship("Application", back_populates="approvals")

    def to_dict(self):
        return {
            "id": self.id,
            "application_id": self.application_id,
            "application_name": self.application.name if self.application else None,
            "project_id": self.project_id,
            "environment": self.environment,
            "namespace": self.namespace,
            "kubernetes_cluster_id": self.kubernetes_cluster_id,
            "image_name": self.image_name,
            "image_tag": self.image_tag,
            "image": f"{self.image_name}:{self.image_tag}",
            "git_branch": self.git_branch,
            "git_commit": self.git_commit,
            "applicant": self.applicant,
            "approver": self.approver,
            "status": self.status,
            "comment": self.comment,
            "pipeline_run_name": self.pipeline_run_name,
            "created_at": self.created_at.isoformat(),
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejected_at": self.rejected_at.isoformat() if self.rejected_at else None,
            "updated_at": self.updated_at.isoformat(),
        }
