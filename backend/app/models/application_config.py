import uuid

from app.extensions import db
from .project import utcnow


class ApplicationConfig(db.Model):
    __tablename__ = "application_configs"

    id = db.Column(db.Integer, primary_key=True)
    config_group_id = db.Column(
        db.String(36), default=lambda: str(uuid.uuid4()), nullable=False, index=True
    )
    application_id = db.Column(
        db.Integer, db.ForeignKey("applications.id"), nullable=False, index=True
    )
    environment_id = db.Column(
        db.Integer, db.ForeignKey("application_environments.id"), nullable=False, index=True
    )
    config_type = db.Column(db.String(30), nullable=False, index=True)
    config_key = db.Column(db.String(253), nullable=False)
    encrypted_value = db.Column(db.Text)
    value_format = db.Column(db.String(20), default="text")
    version = db.Column(db.Integer, default=1, nullable=False)
    is_secret = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    changed_by = db.Column(db.String(120), default="local-user", nullable=False)
    change_message = db.Column(db.String(500))
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    application = db.relationship("Application", back_populates="configs")
    environment = db.relationship("ApplicationEnvironment", back_populates="configs")

    def to_dict(self, value=None):
        return {
            "id": self.id,
            "config_group_id": self.config_group_id,
            "application_id": self.application_id,
            "environment_id": self.environment_id,
            "config_type": self.config_type,
            "config_key": self.config_key,
            "value": "••••••••" if self.is_secret and value is None else value,
            "value_format": self.value_format,
            "version": self.version,
            "is_secret": self.is_secret,
            "is_active": self.is_active,
            "changed_by": self.changed_by,
            "change_message": self.change_message,
            "created_at": self.created_at.isoformat(),
        }

