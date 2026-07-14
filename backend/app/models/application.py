from app.extensions import db
from .project import utcnow


class Application(db.Model):
    __tablename__ = "applications"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    repo_url = db.Column(db.String(500), nullable=False)
    branch = db.Column(db.String(120), default="main", nullable=False)
    language = db.Column(db.String(30), default="unknown")
    framework = db.Column(db.String(50), default="unknown")
    build_type = db.Column(db.String(30), default="unknown")
    deploy_type = db.Column(db.String(30), default="kubernetes")
    image_name = db.Column(db.String(300))
    image_tag = db.Column(db.String(100), default="latest")
    namespace = db.Column(db.String(120), default="default")
    port = db.Column(db.Integer, default=8080)
    status = db.Column(db.String(30), default="draft")
    application_spec = db.Column(db.JSON)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    project = db.relationship("Project", back_populates="applications")
    executions = db.relationship(
        "PipelineExecution",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="PipelineExecution.created_at.desc()",
    )
    build_versions = db.relationship(
        "ApplicationBuildVersion",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationBuildVersion.created_at.desc()",
    )
    releases = db.relationship(
        "ReleaseRecord",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ReleaseRecord.created_at.desc()",
        foreign_keys="ReleaseRecord.application_id",
    )
    environments = db.relationship(
        "ApplicationEnvironment",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationEnvironment.environment_name",
    )
    configs = db.relationship(
        "ApplicationConfig",
        back_populates="application",
        cascade="all, delete-orphan",
    )
    approvals = db.relationship(
        "ApprovalRecord",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApprovalRecord.created_at.desc()",
    )
    release_batches = db.relationship(
        "ApplicationReleaseBatch", back_populates="application",
        cascade="all, delete-orphan", order_by="ApplicationReleaseBatch.created_at.desc()",
    )

    def to_dict(self, include_spec=True):
        latest_execution = next(
            (
                execution
                for execution in self.executions
                if execution.project_id == self.project_id
            ),
            None,
        )
        data = {
            "id": self.id,
            "project_id": self.project_id,
            "project_name": self.project.name if self.project else None,
            "name": self.name,
            "repo_url": self.repo_url,
            "branch": self.branch,
            "language": self.language,
            "framework": self.framework,
            "build_type": self.build_type,
            "deploy_type": self.deploy_type,
            "image_name": self.image_name,
            "image_tag": self.image_tag,
            "namespace": self.namespace,
            "port": self.port,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "latest_execution": (
                latest_execution.to_dict() if latest_execution else None
            ),
            "latest_build_version": (
                self.build_versions[0].to_dict() if self.build_versions else None
            ),
        }
        if include_spec:
            data["application_spec"] = self.application_spec
        return data
