import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta

from flask import current_app

from app.extensions import db
from app.models import User, UserSession
from app.models.project import utcnow
from app.utils.errors import ApiError
from werkzeug.security import check_password_hash, generate_password_hash


_DUMMY_PASSWORD_HASH = generate_password_hash(secrets.token_urlsafe(32))


@dataclass(frozen=True)
class LoginResult:
    user: User
    session: UserSession
    session_token: str
    csrf_token: str


class AuthService:
    @staticmethod
    def digest(token):
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def login(self, username, password):
        user = User.query.filter_by(username=username).first()
        password_hash = user.password_hash if user is not None else _DUMMY_PASSWORD_HASH
        password_matches = check_password_hash(password_hash, password)
        if user is None or not user.is_active or not password_matches:
            raise ApiError(
                "用户名或密码错误",
                401,
                "INVALID_CREDENTIALS",
            )

        session_token = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        session = UserSession(
            user=user,
            token_digest=self.digest(session_token),
            csrf_digest=self.digest(csrf_token),
            expires_at=utcnow()
            + timedelta(hours=current_app.config["AUTH_SESSION_HOURS"]),
        )
        db.session.add(session)
        db.session.commit()
        return LoginResult(user, session, session_token, csrf_token)

    def resolve(self, session_token):
        session = None
        if session_token:
            session = (
                UserSession.query.join(User)
                .filter(
                    UserSession.token_digest == self.digest(session_token),
                    UserSession.revoked_at.is_(None),
                    UserSession.expires_at > utcnow(),
                    User.is_active.is_(True),
                )
                .first()
            )
        if session is None:
            raise ApiError(
                "需要登录后访问",
                401,
                "AUTHENTICATION_REQUIRED",
            )
        return session

    def verify_csrf(self, session, csrf_token):
        if not csrf_token:
            return False
        return secrets.compare_digest(
            session.csrf_digest,
            self.digest(csrf_token),
        )

    def rotate_csrf(self, session):
        csrf_token = secrets.token_urlsafe(32)
        session.csrf_digest = self.digest(csrf_token)
        db.session.commit()
        return csrf_token

    def revoke(self, session):
        session.revoked_at = utcnow()
        db.session.commit()
