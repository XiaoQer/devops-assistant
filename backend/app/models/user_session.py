from app.extensions import db
from .project import utcnow


class UserSession(db.Model):
    __tablename__ = "user_sessions"
    __table_args__ = (
        db.UniqueConstraint("token_digest", name="uq_user_sessions_token_digest"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.id",
            name="fk_user_sessions_user_id_users",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    token_digest = db.Column(db.String(64), nullable=False, index=True)
    csrf_digest = db.Column(db.String(64), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    revoked_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    user = db.relationship("User", back_populates="sessions")
