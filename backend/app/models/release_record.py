from app.extensions import db
from .project import utcnow


class ReleaseRecord(db.Model):
    __tablename__ = "release_records"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(
        db.Integer, db.ForeignKey("applications.id"), nullable=False, index=True
    )
    build_version_id = db.Column(
        db.Integer, db.ForeignKey("application_build_versions.id"), nullable=True, index=True
    )
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    release_type = db.Column(db.String(20), default="deploy", nullable=False)
    environment = db.Column(db.String(30), default="dev", nullable=False, index=True)
    git_repo = db.Column(db.String(500), nullable=False)
    git_branch = db.Column(db.String(120), nullable=False)
    git_commit = db.Column(db.String(64))
    image_name = db.Column(db.String(300), nullable=False)
    image_tag = db.Column(db.String(120), nullable=False)
    pipeline_run_name = db.Column(db.String(253), index=True)
    deploy_namespace = db.Column(db.String(120), nullable=False)
    kubernetes_cluster_id = db.Column(
        db.Integer, db.ForeignKey("kubernetes_clusters.id"), nullable=True
    )
    deploy_status = db.Column(db.String(30), default="Pending", nullable=False)
    deploy_user = db.Column(db.String(120), default="local-user", nullable=False)
    source_release_id = db.Column(db.Integer, db.ForeignKey("release_records.id"))
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    finished_at = db.Column(db.DateTime(timezone=True))
    error_message = db.Column(db.Text)

    application = db.relationship("Application", back_populates="releases")
    source_release = db.relationship("ReleaseRecord", remote_side=[id])

    @property
    def image(self):
        return f"{self.image_name}:{self.image_tag}"

    def to_dict(self):
        return {
            "id": self.id,
            "application_id": self.application_id,
            "build_version_id": self.build_version_id,
            "project_id": self.project_id,
            "release_type": self.release_type,
            "environment": self.environment,
            "git_repo": self.git_repo,
            "git_branch": self.git_branch,
            "git_commit": self.git_commit,
            "image_name": self.image_name,
            "image_tag": self.image_tag,
            "image": self.image,
            "pipeline_run_name": self.pipeline_run_name,
            "deploy_namespace": self.deploy_namespace,
            "kubernetes_cluster_id": self.kubernetes_cluster_id,
            "deploy_status": self.deploy_status,
            "deploy_user": self.deploy_user,
            "source_release_id": self.source_release_id,
            "created_at": self.created_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "error_message": self.error_message,
        }
