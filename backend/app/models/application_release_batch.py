from app.extensions import db
from .project import utcnow


class ApplicationReleaseBatch(db.Model):
    __tablename__ = "application_release_batches"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    build_version_id = db.Column(db.Integer, db.ForeignKey("application_build_versions.id"), nullable=True, index=True)
    branch = db.Column(db.String(120), nullable=False)
    git_commit = db.Column(db.String(64), nullable=False)
    commit_message = db.Column(db.String(500))
    commit_author = db.Column(db.String(255))
    status = db.Column(db.String(30), default="Building", nullable=False, index=True)
    created_by = db.Column(db.String(120), default="local-user", nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    application = db.relationship("Application", back_populates="release_batches")
    targets = db.relationship("ApplicationReleaseTarget", back_populates="batch", cascade="all, delete-orphan")
    build_version = db.relationship("ApplicationBuildVersion", back_populates="release_batch")

    def to_dict(self):
        return {
            "id": self.id, "application_id": self.application_id, "project_id": self.project_id,
            "build_version_id": self.build_version_id, "branch": self.branch,
            "git_commit": self.git_commit, "commit_message": self.commit_message,
            "commit_author": self.commit_author, "status": self.status,
            "created_by": self.created_by, "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "targets": [target.to_dict() for target in self.targets],
        }
