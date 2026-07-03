from app.extensions import db
from .project import utcnow


class ProjectMember(db.Model):
    __tablename__ = "project_members"
    __table_args__ = (
        db.UniqueConstraint("project_id", "email", name="uq_project_member_email"),
    )

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True
    )
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), default="developer", nullable=False)
    title = db.Column(db.String(120))
    status = db.Column(db.String(30), default="active", nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    project = db.relationship("Project", back_populates="members")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "title": self.title,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
