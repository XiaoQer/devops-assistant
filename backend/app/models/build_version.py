from app.extensions import db
from .project import utcnow


class ApplicationBuildVersion(db.Model):
    __tablename__ = "application_build_versions"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    version = db.Column(db.String(120), nullable=False)
    git_repo = db.Column(db.String(500), nullable=False)
    git_branch = db.Column(db.String(120), nullable=False)
    git_commit = db.Column(db.String(64))
    image_name = db.Column(db.String(300), nullable=False)
    image_tag = db.Column(db.String(120), nullable=False)
    image_digest = db.Column(db.String(255))
    pipeline_run_name = db.Column(db.String(253), index=True)
    status = db.Column(db.String(30), default="Pending", nullable=False, index=True)
    created_by = db.Column(db.String(120), default="local-user", nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    finished_at = db.Column(db.DateTime(timezone=True))
    error_message = db.Column(db.Text)

    application = db.relationship("Application", back_populates="build_versions")

    @property
    def image(self):
        return f"{self.image_name}:{self.image_tag}"

    def to_dict(self):
        return {
            "id": self.id,
            "application_id": self.application_id,
            "project_id": self.project_id,
            "version": self.version,
            "git_repo": self.git_repo,
            "git_branch": self.git_branch,
            "git_commit": self.git_commit,
            "image_name": self.image_name,
            "image_tag": self.image_tag,
            "image_digest": self.image_digest,
            "image": self.image,
            "pipeline_run_name": self.pipeline_run_name,
            "status": self.status,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "error_message": self.error_message,
        }
