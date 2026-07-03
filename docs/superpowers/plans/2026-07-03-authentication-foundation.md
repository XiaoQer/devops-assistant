# Authentication Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add pre-provisioned administrator login, revocable database sessions, CSRF protection, trusted current-user propagation, and authenticated Vue navigation.

**Architecture:** Flask owns authentication through `AuthService`, persists password hashes and session-token digests in MySQL, and identifies requests with an HttpOnly cookie. A global request guard protects every API except login and health, while Vue restores identity through `/auth/me`, keeps only user/CSRF state in Pinia, and redirects unauthenticated navigation to a login page.

**Tech Stack:** Flask 3.1, Flask-SQLAlchemy, Alembic, Werkzeug password hashing, Python `secrets`/`hashlib`, Vue 3, Pinia, Vue Router, Axios, Element Plus, pytest

---

## File map

### Backend files

- Create `backend/app/models/user.py`: user identity, password hash, active state, safe serialization.
- Create `backend/app/models/user_session.py`: revocable session record containing only token and CSRF digests.
- Modify `backend/app/models/__init__.py`: register both models for SQLAlchemy and migrations.
- Create `backend/migrations/versions/a7c8d9e0f1a2_add_authentication_foundation.py`: create `users` and `user_sessions`.
- Create `backend/app/services/auth_service.py`: password verification, session lifecycle, cookie-token lookup, CSRF verification.
- Create `backend/app/routes/auth.py`: login, current-user, and logout transport behavior.
- Modify `backend/app/routes/__init__.py`: export the auth Blueprint.
- Modify `backend/app/__init__.py`: configure CORS, register auth, install trace/auth/CSRF hooks, expose `create-admin`.
- Modify `backend/app/config.py`: cookie names, lifetime, secure flag, and allowed frontend origins.
- Modify `backend/app/routes/applications.py`, `approvals.py`, and `environments.py`: use `g.current_user.username` instead of `X-User`.
- Create `backend/tests/auth_helpers.py`: reusable user creation, login, and CSRF-aware request helper.
- Create `backend/tests/test_auth_service.py`: model and session service tests.
- Create `backend/tests/test_auth_routes.py`: login/me/logout/global-guard/CSRF tests.
- Modify `backend/tests/test_project_routes.py` and `backend/tests/test_validation_routes.py`: authenticate existing route tests.

### Frontend files

- Modify `frontend/src/types.ts`: add `AuthenticatedUser` and `AuthResponse`.
- Create `frontend/src/api/auth.ts`: typed login, current-user, and logout calls.
- Modify `frontend/src/api/client.ts`: credentials, CSRF header, and centralized 401 notification.
- Create `frontend/src/stores/auth.ts`: current user, CSRF state, initialization, login, logout.
- Create `frontend/src/views/Login.vue`: username/password form and safe return navigation.
- Modify `frontend/src/router/index.ts`: public login route and global authentication guard.
- Modify `frontend/src/main.ts`: create Pinia once and initialize the router guard with it.
- Create `frontend/src/components/common/CurrentUserMenu.vue`: shared current-user display and logout action.
- Modify `frontend/src/layouts/PortalLayout.vue`, `ProjectCenterLayout.vue`, `DevCenterLayout.vue`, and `MainLayout.vue`: replace hard-coded identity with `CurrentUserMenu`.

### Product memory

- Modify `docs/current-state.md`: record the verified authentication capability and its explicit security gaps.
- Modify `specs/active/authentication-foundation.md`: add verification evidence and move it to `specs/completed/` only after acceptance.

## Task 1: Persist users and revocable sessions

**Files:**
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/user_session.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/migrations/versions/a7c8d9e0f1a2_add_authentication_foundation.py`
- Test: `backend/tests/test_auth_service.py`

- [ ] **Step 1: Write failing model tests**

Create `backend/tests/test_auth_service.py` with a small in-memory app and these tests:

```python
from datetime import timedelta
import unittest

from werkzeug.security import check_password_hash

from app import create_app
from app.extensions import db
from app.models import User, UserSession
from app.models.project import utcnow


class TestConfig:
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    AUTO_CREATE_SCHEMA = True
    SECRET_KEY = "auth-service-test-secret"
    AUTH_SESSION_HOURS = 8
    AUTH_COOKIE_NAME = "aegis_session"
    AUTH_CSRF_COOKIE_NAME = "aegis_csrf"
    AUTH_COOKIE_SECURE = False
    CORS_ORIGINS = ["http://localhost:5173"]
    TESTING = True


class AuthModelTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.context = self.app.app_context()
        self.context.push()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    def test_user_hashes_password_and_serializes_only_public_fields(self):
        user = User(username="admin", display_name="Aegis Admin")
        user.set_password("correct-horse-battery-staple")
        db.session.add(user)
        db.session.commit()

        self.assertTrue(check_password_hash(user.password_hash, "correct-horse-battery-staple"))
        self.assertNotIn("password_hash", user.to_dict())
        self.assertEqual(user.to_dict()["username"], "admin")

    def test_session_relationship_is_deleted_with_user(self):
        user = User(username="admin", display_name="Aegis Admin", password_hash="hash")
        session = UserSession(
            user=user,
            token_digest="a" * 64,
            csrf_digest="b" * 64,
            expires_at=utcnow() + timedelta(hours=8),
        )
        db.session.add_all([user, session])
        db.session.commit()
        db.session.delete(user)
        db.session.commit()

        self.assertEqual(UserSession.query.count(), 0)
```

- [ ] **Step 2: Run the tests and verify the missing models fail**

Run:

```bash
cd backend
.venv/bin/python -m pytest tests/test_auth_service.py -q
```

Expected: collection fails because `User` and `UserSession` are not exported.

- [ ] **Step 3: Implement the user model**

Create `backend/app/models/user.py`:

```python
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from .project import utcnow


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), nullable=False, unique=True, index=True)
    display_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )
    sessions = db.relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name,
            "is_active": self.is_active,
        }
```

- [ ] **Step 4: Implement the session model and exports**

Create `backend/app/models/user_session.py`:

```python
from app.extensions import db
from .project import utcnow


class UserSession(db.Model):
    __tablename__ = "user_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    token_digest = db.Column(db.String(64), nullable=False, unique=True, index=True)
    csrf_digest = db.Column(db.String(64), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    revoked_at = db.Column(db.DateTime(timezone=True), index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    user = db.relationship("User", back_populates="sessions")
```

Add to `backend/app/models/__init__.py`:

```python
from .user import User
from .user_session import UserSession
```

and add `"User", "UserSession"` to `__all__`.

- [ ] **Step 5: Add the Alembic migration**

Create `backend/migrations/versions/a7c8d9e0f1a2_add_authentication_foundation.py` with
`revision = "a7c8d9e0f1a2"` and `down_revision = "f1a2b3c4d5e6"`. Its `upgrade()` must
create `users` first and `user_sessions` second:

```python
def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username", name="uq_users_username"),
    )
    with op.batch_alter_table("users") as batch_op:
        batch_op.create_index("ix_users_username", ["username"], unique=True)
        batch_op.create_index("ix_users_is_active", ["is_active"], unique=False)

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_digest", sa.String(length=64), nullable=False),
        sa.Column("csrf_digest", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_user_sessions_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "token_digest", name="uq_user_sessions_token_digest"
        ),
    )
    with op.batch_alter_table("user_sessions") as batch_op:
        batch_op.create_index(
            "ix_user_sessions_user_id", ["user_id"], unique=False
        )
        batch_op.create_index(
            "ix_user_sessions_token_digest", ["token_digest"], unique=True
        )
        batch_op.create_index(
            "ix_user_sessions_expires_at", ["expires_at"], unique=False
        )
        batch_op.create_index(
            "ix_user_sessions_revoked_at", ["revoked_at"], unique=False
        )


def downgrade():
    op.drop_table("user_sessions")
    op.drop_table("users")
```

- [ ] **Step 6: Run the focused tests**

Run:

```bash
cd backend
.venv/bin/python -m pytest tests/test_auth_service.py -q
```

Expected: `2 passed`.

- [ ] **Step 7: Commit the persistence slice**

```bash
git add backend/app/models backend/migrations/versions/a7c8d9e0f1a2_add_authentication_foundation.py backend/tests/test_auth_service.py
git commit -m "feat(auth): persist users and sessions"
```

## Task 2: Implement session lifecycle and CSRF verification

**Files:**
- Create: `backend/app/services/auth_service.py`
- Modify: `backend/app/config.py`
- Test: `backend/tests/test_auth_service.py`

- [ ] **Step 1: Add failing service tests**

Append tests that create an active user and assert:

```python
from app.services.auth_service import AuthService

def test_login_creates_only_digests(self):
    result = AuthService().login("admin", "correct-horse-battery-staple")
    self.assertNotEqual(result.session.token_digest, result.session_token)
    self.assertNotEqual(result.session.csrf_digest, result.csrf_token)
    self.assertEqual(len(result.session.token_digest), 64)

def test_invalid_or_disabled_user_has_same_error(self):
    with self.assertRaisesRegex(Exception, "用户名或密码错误"):
        AuthService().login("missing", "anything")
    self.user.is_active = False
    db.session.commit()
    with self.assertRaisesRegex(Exception, "用户名或密码错误"):
        AuthService().login("admin", "correct-horse-battery-staple")

def test_resolve_rejects_expired_and_revoked_sessions(self):
    result = AuthService().login("admin", "correct-horse-battery-staple")
    result.session.revoked_at = utcnow()
    db.session.commit()
    self.assertIsNone(AuthService().resolve(result.session_token))
```

In `setUp`, save the created user as `self.user`.

- [ ] **Step 2: Verify the service tests fail**

Run:

```bash
cd backend
.venv/bin/python -m pytest tests/test_auth_service.py -q
```

Expected: import fails because `AuthService` does not exist.

- [ ] **Step 3: Add authentication configuration**

Add to `backend/app/config.py`:

```python
AUTH_SESSION_HOURS = int(os.getenv("AUTH_SESSION_HOURS", "8"))
AUTH_COOKIE_NAME = os.getenv("AUTH_COOKIE_NAME", "aegis_session")
AUTH_CSRF_COOKIE_NAME = os.getenv("AUTH_CSRF_COOKIE_NAME", "aegis_csrf")
AUTH_COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true"
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
```

- [ ] **Step 4: Implement `AuthService`**

Create `backend/app/services/auth_service.py` with:

```python
from dataclasses import dataclass
from datetime import timedelta
import hashlib
import secrets

from flask import current_app

from app.extensions import db
from app.models import User, UserSession
from app.models.project import utcnow
from app.utils.errors import ApiError


@dataclass
class LoginResult:
    user: User
    session: UserSession
    session_token: str
    csrf_token: str


class AuthService:
    INVALID_CREDENTIALS = "用户名或密码错误"

    @staticmethod
    def digest(value):
        return hashlib.sha256(value.encode()).hexdigest()

    def login(self, username, password):
        user = User.query.filter_by(username=username).first()
        if not user or not user.is_active or not user.check_password(password):
            raise ApiError(self.INVALID_CREDENTIALS, 401, "INVALID_CREDENTIALS")
        session_token = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        session = UserSession(
            user=user,
            token_digest=self.digest(session_token),
            csrf_digest=self.digest(csrf_token),
            expires_at=utcnow() + timedelta(
                hours=current_app.config["AUTH_SESSION_HOURS"]
            ),
        )
        db.session.add(session)
        db.session.commit()
        return LoginResult(user, session, session_token, csrf_token)

    def resolve(self, session_token):
        if not session_token:
            return None
        return (
            UserSession.query.join(User)
            .filter(
                UserSession.token_digest == self.digest(session_token),
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > utcnow(),
                User.is_active.is_(True),
            )
            .first()
        )

    def verify_csrf(self, session, csrf_token):
        return bool(
            csrf_token
            and secrets.compare_digest(session.csrf_digest, self.digest(csrf_token))
        )

    def revoke(self, session):
        session.revoked_at = utcnow()
        db.session.commit()
```

- [ ] **Step 5: Run focused tests**

Run:

```bash
cd backend
.venv/bin/python -m pytest tests/test_auth_service.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit the service slice**

```bash
git add backend/app/config.py backend/app/services/auth_service.py backend/tests/test_auth_service.py
git commit -m "feat(auth): manage secure database sessions"
```

## Task 3: Expose auth endpoints and protect the API globally

**Files:**
- Create: `backend/app/routes/auth.py`
- Modify: `backend/app/routes/__init__.py`
- Modify: `backend/app/__init__.py`
- Create: `backend/tests/auth_helpers.py`
- Create: `backend/tests/test_auth_routes.py`

- [ ] **Step 1: Write failing route and guard tests**

Create `backend/tests/auth_helpers.py`:

```python
from app.extensions import db
from app.models import User


PASSWORD = "test-only-strong-password"


def create_user(username="admin", display_name="Aegis Admin", active=True):
    user = User(username=username, display_name=display_name, is_active=active)
    user.set_password(PASSWORD)
    db.session.add(user)
    db.session.commit()
    return user


def login(client, username="admin", password=PASSWORD):
    response = client.post("/api/auth/login", json={
        "username": username,
        "password": password,
    })
    return response, response.get_json().get("data", {})


def csrf_post(client, path, csrf_token, **kwargs):
    headers = {**kwargs.pop("headers", {}), "X-CSRF-Token": csrf_token}
    return client.post(path, headers=headers, **kwargs)
```

Create `backend/tests/test_auth_routes.py` and cover:

```python
def test_health_and_login_are_public(self):
    self.assertEqual(self.client.get("/api/health").status_code, 200)
    self.assertNotEqual(
        self.client.get("/api/health/kubernetes").status_code, 401
    )
    self.assertNotEqual(
        self.client.post("/api/auth/login", json={}).status_code, 401
    )

def test_business_api_requires_authentication(self):
    response = self.client.get("/api/projects")
    self.assertEqual(response.status_code, 401)
    self.assertEqual(
        response.get_json()["error"]["code"], "AUTHENTICATION_REQUIRED"
    )

def test_login_me_logout_lifecycle(self):
    response, data = login(self.client)
    self.assertEqual(response.status_code, 200)
    self.assertEqual(data["user"]["username"], "admin")
    self.assertNotIn("password_hash", data["user"])
    self.assertTrue(data["csrf_token"])
    self.assertEqual(self.client.get("/api/auth/me").status_code, 200)
    logout = self.client.post(
        "/api/auth/logout", headers={"X-CSRF-Token": data["csrf_token"]}
    )
    self.assertEqual(logout.status_code, 200)
    self.assertEqual(self.client.get("/api/auth/me").status_code, 401)

def test_write_request_requires_matching_csrf(self):
    _response, data = login(self.client)
    missing = self.client.post("/api/projects", json={"key": "x", "name": "X"})
    wrong = self.client.post(
        "/api/projects",
        json={"key": "x", "name": "X"},
        headers={"X-CSRF-Token": "wrong"},
    )
    self.assertEqual(missing.status_code, 403)
    self.assertEqual(wrong.status_code, 403)
    self.assertEqual(
        missing.get_json()["error"]["code"], "CSRF_VALIDATION_FAILED"
    )
```

- [ ] **Step 2: Run route tests and verify failure**

Run:

```bash
cd backend
.venv/bin/python -m pytest tests/test_auth_routes.py -q
```

Expected: login route is 404 and business API is still public.

- [ ] **Step 3: Implement auth routes**

Create `backend/app/routes/auth.py`. Validate the body with existing validation helpers,
call `AuthService`, wrap the standard response tuple with `make_response`, and use these
cookie settings:

```python
response = make_response(success(
    {"user": result.user.to_dict(), "csrf_token": result.csrf_token},
    "登录成功",
))
response.set_cookie(
    current_app.config["AUTH_COOKIE_NAME"],
    result.session_token,
    httponly=True,
    secure=current_app.config["AUTH_COOKIE_SECURE"],
    samesite="Lax",
    max_age=current_app.config["AUTH_SESSION_HOURS"] * 3600,
    path="/",
)
response.set_cookie(
    current_app.config["AUTH_CSRF_COOKIE_NAME"],
    result.csrf_token,
    httponly=False,
    secure=current_app.config["AUTH_COOKIE_SECURE"],
    samesite="Lax",
    max_age=current_app.config["AUTH_SESSION_HOURS"] * 3600,
    path="/",
)
```

The three route responses must be:

```python
success({"user": result.user.to_dict(), "csrf_token": result.csrf_token}, "登录成功")
success({"user": g.current_user.to_dict(), "csrf_token": request.cookies.get(
    current_app.config["AUTH_CSRF_COOKIE_NAME"]
)})
success(None, "已退出登录")
```

Logout must call `AuthService().revoke(g.current_session)` and delete both cookies.

- [ ] **Step 4: Export and register the Blueprint**

Export `auth_bp` from `backend/app/routes/__init__.py`, import it in
`backend/app/__init__.py`, and register it before business Blueprints.

- [ ] **Step 5: Add global authentication and CSRF hooks**

Keep `attach_trace_id` first. Add a second `before_request` hook:

```python
@app.before_request
def authenticate_request():
    if (
        not request.path.startswith("/api/")
        or request.blueprint == "health"
        or request.endpoint == "auth.login"
        or request.method == "OPTIONS"
    ):
        return None
    token = request.cookies.get(app.config["AUTH_COOKIE_NAME"])
    session = AuthService().resolve(token)
    if not session:
        raise ApiError(
            "请先登录", 401, "AUTHENTICATION_REQUIRED"
        )
    g.current_session = session
    g.current_user = session.user
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        csrf_token = request.headers.get("X-CSRF-Token")
        if not AuthService().verify_csrf(session, csrf_token):
            raise ApiError(
                "CSRF 校验失败", 403, "CSRF_VALIDATION_FAILED"
            )
```

Do not exempt logout from authentication or CSRF.

- [ ] **Step 6: Restrict credentialed CORS**

Replace `CORS(app)` with:

```python
CORS(
    app,
    resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
    supports_credentials=True,
)
```

- [ ] **Step 7: Run focused route tests**

Run:

```bash
cd backend
.venv/bin/python -m pytest tests/test_auth_routes.py -q
```

Expected: all tests pass.

- [ ] **Step 8: Commit the HTTP boundary**

```bash
git add backend/app/__init__.py backend/app/routes backend/tests/auth_helpers.py backend/tests/test_auth_routes.py
git commit -m "feat(auth): protect API with cookie sessions"
```

## Task 4: Provision the first administrator safely

**Files:**
- Modify: `backend/app/__init__.py`
- Test: `backend/tests/test_auth_routes.py`

- [ ] **Step 1: Write a failing CLI test**

Add a test using `self.app.test_cli_runner()`:

```python
def test_create_admin_reads_environment_without_echoing_password(self):
    result = self.runner.invoke(
        args=["create-admin"],
        env={
            "AEGIS_ADMIN_USERNAME": "admin",
            "AEGIS_ADMIN_DISPLAY_NAME": "Aegis Admin",
            "AEGIS_ADMIN_PASSWORD": "cli-only-strong-password",
        },
    )
    self.assertEqual(result.exit_code, 0)
    self.assertIn("admin created", result.output)
    self.assertNotIn("cli-only-strong-password", result.output)
    self.assertTrue(User.query.filter_by(username="admin").one().check_password(
        "cli-only-strong-password"
    ))
```

Also test a missing variable exits non-zero and an existing username exits non-zero without
changing its password.

- [ ] **Step 2: Verify the CLI test fails**

Run:

```bash
cd backend
.venv/bin/python -m pytest tests/test_auth_routes.py -k create_admin -q
```

Expected: Flask reports that `create-admin` does not exist.

- [ ] **Step 3: Implement the non-interactive command**

Add `create-admin` in `create_app`:

```python
@app.cli.command("create-admin")
def create_admin():
    username = os.getenv("AEGIS_ADMIN_USERNAME", "").strip()
    display_name = os.getenv("AEGIS_ADMIN_DISPLAY_NAME", "").strip()
    password = os.getenv("AEGIS_ADMIN_PASSWORD", "")
    if not username or not display_name or not password:
        raise click.ClickException(
            "AEGIS_ADMIN_USERNAME, AEGIS_ADMIN_DISPLAY_NAME and "
            "AEGIS_ADMIN_PASSWORD are required"
        )
    if len(password) < 12:
        raise click.ClickException("AEGIS_ADMIN_PASSWORD must be at least 12 characters")
    if User.query.filter_by(username=username).first():
        raise click.ClickException("admin already exists")
    user = User(username=username, display_name=display_name)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo("admin created")
```

Import `click`, `os`, and `User`; never print environment values.

- [ ] **Step 4: Run the CLI tests**

Run:

```bash
cd backend
.venv/bin/python -m pytest tests/test_auth_routes.py -k create_admin -q
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit the provisioning command**

```bash
git add backend/app/__init__.py backend/tests/test_auth_routes.py
git commit -m "feat(auth): provision administrators safely"
```

## Task 5: Propagate trusted identity and repair existing route tests

**Files:**
- Modify: `backend/app/routes/applications.py`
- Modify: `backend/app/routes/approvals.py`
- Modify: `backend/app/routes/environments.py`
- Modify: `backend/tests/test_project_routes.py`
- Modify: `backend/tests/test_validation_routes.py`
- Test: `backend/tests/test_auth_routes.py`

- [ ] **Step 1: Add a failing spoofed-header test**

Create an application fixture, login as `admin`, send a config creation request with
`X-User: attacker`, and assert:

```python
self.assertEqual(response.status_code, 201)
self.assertEqual(response.get_json()["data"]["changed_by"], "admin")
```

- [ ] **Step 2: Verify the spoofing test fails**

Run:

```bash
cd backend
.venv/bin/python -m pytest tests/test_auth_routes.py -k ignores_spoofed_user -q
```

Expected: `changed_by` is `attacker`.

- [ ] **Step 3: Replace every `X-User` read**

In the three Route modules, import `g` from Flask and replace:

```python
request.headers.get("X-User", "local-user")
```

and:

```python
request.headers.get("X-User", "project-owner")
```

with:

```python
g.current_user.username
```

Run `rg -n "X-User" backend/app` and expect no matches.

- [ ] **Step 4: Authenticate existing route tests**

In both route-test classes:

```python
from tests.auth_helpers import create_user, login

self.user = create_user()
_response, self.auth = login(self.client)
```

For every POST/PATCH/DELETE in those files, add:

```python
headers={"X-CSRF-Token": self.auth["csrf_token"]}
```

GET requests need no CSRF header.

- [ ] **Step 5: Run all backend tests**

Run:

```bash
cd backend
.venv/bin/python -m pytest tests -q
```

Expected: all backend tests pass; no route assertion fails with 401 or 403.

- [ ] **Step 6: Commit trusted identity propagation**

```bash
git add backend/app/routes backend/tests
git commit -m "refactor(auth): use verified current user"
```

## Task 6: Build the frontend authentication state and API boundary

**Files:**
- Modify: `frontend/src/types.ts`
- Create: `frontend/src/api/auth.ts`
- Modify: `frontend/src/api/client.ts`
- Create: `frontend/src/stores/auth.ts`

- [ ] **Step 1: Add authentication types**

Append to `frontend/src/types.ts`:

```typescript
export interface AuthenticatedUser {
  id: number
  username: string
  display_name: string
  is_active: boolean
}

export interface AuthResponse {
  user: AuthenticatedUser
  csrf_token: string
}
```

- [ ] **Step 2: Create the typed auth API**

Create `frontend/src/api/auth.ts`:

```typescript
import { client } from './client'
import type { AuthResponse } from '../types'

export const authApi = {
  login: (username: string, password: string) =>
    client.post<never, AuthResponse>('/auth/login', { username, password }),
  me: () => client.get<never, AuthResponse>('/auth/me'),
  logout: () => client.post('/auth/logout'),
}
```

- [ ] **Step 3: Make Axios session-aware without importing the Store**

Modify `frontend/src/api/client.ts`:

```typescript
import axios from 'axios'

export const client = axios.create({
  baseURL: '/api',
  timeout: 120000,
  withCredentials: true,
})

let csrfToken = ''
let authenticationRequired: (() => void) | undefined

export function setCsrfToken(value = '') {
  csrfToken = value
}

export function onAuthenticationRequired(callback: () => void) {
  authenticationRequired = callback
}

client.interceptors.request.use(config => {
  const method = config.method?.toUpperCase()
  if (method && !['GET', 'HEAD', 'OPTIONS'].includes(method) && csrfToken) {
    config.headers.set('X-CSRF-Token', csrfToken)
  }
  return config
})

client.interceptors.response.use(
  response => response.data.data,
  error => {
    if (error.response?.status === 401) authenticationRequired?.()
    return Promise.reject(new Error(error.response?.data?.message || error.message))
  },
)
```

This avoids a circular dependency between the Axios singleton and Pinia.

- [ ] **Step 4: Create the authentication Store**

Create `frontend/src/stores/auth.ts`:

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '../api/auth'
import { setCsrfToken } from '../api/client'
import type { AuthenticatedUser } from '../types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthenticatedUser>()
  const initialized = ref(false)

  function apply(data?: { user: AuthenticatedUser; csrf_token: string }) {
    user.value = data?.user
    setCsrfToken(data?.csrf_token || '')
  }

  async function initialize() {
    if (initialized.value) return
    try {
      apply(await authApi.me())
    } catch {
      apply()
    } finally {
      initialized.value = true
    }
  }

  async function login(username: string, password: string) {
    apply(await authApi.login(username, password))
  }

  async function logout() {
    try {
      await authApi.logout()
    } finally {
      apply()
    }
  }

  function clear() {
    apply()
  }

  return { user, initialized, initialize, login, logout, clear }
})
```

- [ ] **Step 5: Run the frontend type/build check**

Run:

```bash
npm --prefix frontend run build
```

Expected: type checking and Vite production build pass.

- [ ] **Step 6: Commit the frontend API slice**

```bash
git add frontend/src/types.ts frontend/src/api frontend/src/stores/auth.ts
git commit -m "feat(auth): add frontend session state"
```

## Task 7: Add login navigation and real current-user UI

**Files:**
- Create: `frontend/src/views/Login.vue`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/main.ts`
- Create: `frontend/src/components/common/CurrentUserMenu.vue`
- Modify: `frontend/src/layouts/PortalLayout.vue`
- Modify: `frontend/src/layouts/ProjectCenterLayout.vue`
- Modify: `frontend/src/layouts/DevCenterLayout.vue`
- Modify: `frontend/src/layouts/MainLayout.vue`

- [ ] **Step 1: Add a standalone login page**

Create `frontend/src/views/Login.vue` with a centered Element Plus form. Its submit logic must be:

```typescript
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const username = ref('')
const password = ref('')
const submitting = ref(false)

async function submit() {
  if (!username.value || !password.value) {
    return ElMessage.warning('请输入用户名和密码')
  }
  submitting.value = true
  try {
    await auth.login(username.value, password.value)
    const redirect = typeof route.query.redirect === 'string'
      && route.query.redirect.startsWith('/')
      && !route.query.redirect.startsWith('//')
      ? route.query.redirect
      : '/portal'
    await router.replace(redirect)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '登录失败')
  } finally {
    submitting.value = false
  }
}
```

The password input must use `type="password"` and `show-password`; the form must not save
the password outside component state.

- [ ] **Step 2: Add the public route and global guard**

Refactor `frontend/src/router/index.ts` to export both the router and an installer:

```typescript
import type { Pinia } from 'pinia'
import { useAuthStore } from '../stores/auth'

const router = createRouter({ /* retain every existing route */ })

router.addRoute({
  path: '/login',
  name: 'login',
  component: () => import('../views/Login.vue'),
  meta: { public: true, title: 'Sign in' },
})

export function installAuthGuard(pinia: Pinia) {
  router.beforeEach(async to => {
    const auth = useAuthStore(pinia)
    await auth.initialize()
    if (to.meta.public) {
      return to.path === '/login' && auth.user ? '/portal' : true
    }
    if (!auth.user) {
      return { path: '/login', query: { redirect: to.fullPath } }
    }
    return true
  })
}

export default router
```

Mark only `/login` public. `/portal` is authenticated because it calls protected APIs and displays
the current user.

- [ ] **Step 3: Install Pinia and the guard in the correct order**

Modify `frontend/src/main.ts`:

```typescript
const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
installAuthGuard(pinia)
app.use(router)
app.use(ElementPlus)
app.mount('#app')
```

- [ ] **Step 4: Connect centralized 401 handling**

After creating the Store in `installAuthGuard`, register once:

```typescript
onAuthenticationRequired(() => {
  auth.clear()
  if (router.currentRoute.value.path !== '/login') {
    router.replace({
      path: '/login',
      query: { redirect: router.currentRoute.value.fullPath },
    })
  }
})
```

Guard duplicate registration with a module-level boolean.

- [ ] **Step 5: Create a shared current-user menu**

Create `frontend/src/components/common/CurrentUserMenu.vue`:

```vue
<template>
  <el-dropdown @command="handle">
    <button class="current-user">
      <span>{{ initials }}</span>
      <b>{{ auth.user?.display_name }}</b>
    </button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item disabled>{{ auth.user?.username }}</el-dropdown-item>
        <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const initials = computed(() =>
  (auth.user?.display_name || auth.user?.username || '?')
    .split(/\s+/).map(part => part[0]).join('').slice(0, 2).toUpperCase()
)

async function handle(command: string) {
  if (command !== 'logout') return
  await auth.logout()
  await router.replace('/login')
}
</script>
```

Add scoped styling that matches existing `--surface-*`, `--text`, and `--muted` tokens.

- [ ] **Step 6: Replace every hard-coded identity**

Import and render `CurrentUserMenu` in the header/footer identity areas of all four Layouts.
Remove `Shaoqian Li`, `SL`, and `Platform user` literals where they represent the signed-in user.
Do not change unrelated navigation or layout styling.

Run:

```bash
rg -n "Shaoqian Li|Platform user|Builder mode" frontend/src/layouts
```

Expected: no matches.

- [ ] **Step 7: Run the production frontend build**

Run:

```bash
npm --prefix frontend run build
```

Expected: `vue-tsc` and Vite complete successfully; only the already documented bundle-size warning
may remain.

- [ ] **Step 8: Commit the authenticated UI**

```bash
git add frontend/src
git commit -m "feat(auth): add authenticated navigation"
```

## Task 8: Verify the whole behavior and update repository memory

**Files:**
- Modify: `docs/current-state.md`
- Modify then move: `specs/active/authentication-foundation.md` to `specs/completed/authentication-foundation.md`

- [ ] **Step 1: Run migration upgrade and downgrade checks against a disposable database**

Use the existing local test database configuration or a disposable MySQL schema:

```bash
cd backend
flask db upgrade
flask db downgrade f1a2b3c4d5e6
flask db upgrade
```

Expected: both tables are created, removed in dependency order, and recreated without errors.
Do not run downgrade against a database containing user-owned data.

- [ ] **Step 2: Run the repository verification harness**

Run:

```bash
./scripts/verify.sh
```

Expected: all backend tests pass and the frontend production build succeeds.

- [ ] **Step 3: Perform browser acceptance checks**

Run the local backend and frontend, then verify:

1. An unauthenticated deep link redirects to `/login?redirect=...`.
2. Wrong credentials show the generic message.
3. Valid credentials return to the original deep link.
4. Refresh restores the user through `/auth/me`.
5. A write request without CSRF returns 403.
6. Sending `X-User: attacker` does not change the recorded actor.
7. Logout returns to login and the old session cannot call `/api/projects`.
8. No password, raw session token, token digest, or registry/application secret appears in API
   responses, browser logs, backend logs, fixtures, or documentation.

- [ ] **Step 4: Update `docs/current-state.md` with verified facts**

Add authentication to “仓库中已经实现” only after Step 2 passes. Add these remaining gaps:

```markdown
- 身份认证目前仅支持预置管理员和数据库会话；尚无注册、密码恢复、SSO、MFA、
  项目级 RBAC 和分布式登录限流，因此仍不构成生产级身份系统。
```

Update the audit date and verification counts from the actual command output.

- [ ] **Step 5: Complete the active specification**

In the spec:

- change status from `草稿` to `已验收`;
- check only acceptance boxes backed by evidence;
- add the exact test/build/migration/browser evidence;
- record the acceptance date;
- move the file to `specs/completed/authentication-foundation.md`.

- [ ] **Step 6: Run final consistency checks**

Run:

```bash
rg -n "X-User" backend/app
rg -n "Shaoqian Li|local-user" frontend/src/layouts
git diff --check
./scripts/verify.sh
```

Expected: the first two searches have no matches, `git diff --check` is silent, and verification
passes.

- [ ] **Step 7: Commit verified documentation and completed spec**

```bash
git add docs/current-state.md specs/active specs/completed
git commit -m "docs(auth): record verified authentication capability"
```
