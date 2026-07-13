import os
import secrets
import uuid

import click
from flask import Flask
from flask import g, request
from flask_cors import CORS
from kubernetes.client.exceptions import ApiException
from kubernetes.config.config_exception import ConfigException
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.exceptions import RequestEntityTooLarge

from .config import Config
from .extensions import db, migrate
from .models import User
from .routes import (
    applications_bp, health_bp, pipelines_bp, environments_bp, releases_bp,
    approvals_bp, ai_bp, projects_bp, auth_bp,
)
from .utils.errors import ApiError
from .utils.response import failure
from .services.release_service import ReleaseService
from .services.auth_service import AuthService


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    CORS(
        app,
        origins=app.config.get("CORS_ORIGINS", Config.CORS_ORIGINS),
        supports_credentials=True,
    )
    db.init_app(app)
    migrate.init_app(app, db)

    # 仅供 Docker Compose 本地测试；生产环境应始终使用 Alembic migration。
    if app.config["AUTO_CREATE_SCHEMA"]:
        with app.app_context():
            db.create_all()

    app.register_blueprint(applications_bp)
    app.register_blueprint(pipelines_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(environments_bp)
    app.register_blueprint(releases_bp)
    app.register_blueprint(approvals_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(auth_bp)

    @app.before_request
    def attach_trace_id():
        g.trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())

    @app.before_request
    def authenticate_api_request():
        if (
            not request.path.startswith("/api")
            or request.method == "OPTIONS"
            or request.blueprint == "health"
            or request.endpoint == "auth.login"
        ):
            return None

        auth_service = AuthService()
        session = auth_service.resolve(
            request.cookies.get(app.config["AUTH_COOKIE_NAME"])
        )
        g.current_session = session
        g.current_user = session.user

        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            csrf_header = request.headers.get("X-CSRF-Token")
            csrf_cookie = request.cookies.get(app.config["AUTH_CSRF_COOKIE_NAME"])
            csrf_tokens_match = bool(
                csrf_header and csrf_cookie
            ) and secrets.compare_digest(csrf_header, csrf_cookie)
            if not csrf_tokens_match or not auth_service.verify_csrf(
                session, csrf_header
            ):
                raise ApiError(
                    "CSRF 校验失败",
                    403,
                    "CSRF_VALIDATION_FAILED",
                )
        return None

    @app.after_request
    def return_trace_id(response):
        response.headers["X-Trace-ID"] = getattr(g, "trace_id", "")
        if request.blueprint == "auth":
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.cli.command("sync-deliveries")
    def sync_deliveries():
        """Synchronize pending Tekton runs into delivery records."""
        count = ReleaseService().sync_all()
        print(f"Synced {count} pending delivery records")

    @app.cli.command("create-admin")
    def create_admin():
        """Create the initial administrator from environment variables."""
        username = os.environ.get("AEGIS_ADMIN_USERNAME", "").strip()
        display_name = os.environ.get("AEGIS_ADMIN_DISPLAY_NAME", "").strip()
        password = os.environ.get("AEGIS_ADMIN_PASSWORD", "")

        if not username or not display_name or not password:
            raise click.ClickException(
                "Administrator credentials are required"
            )
        if len(username) > 120 or len(display_name) > 120:
            raise click.ClickException("Administrator profile is invalid")
        if not password.strip() or not 12 <= len(password) <= 4096:
            raise click.ClickException("Administrator password is invalid")

        try:
            if User.query.filter_by(username=username).first() is not None:
                raise click.ClickException("admin already exists")

            user = User(username=username, display_name=display_name)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise click.ClickException("admin already exists") from None
        except SQLAlchemyError:
            db.session.rollback()
            raise click.ClickException("failed to create admin") from None
        click.echo(f"Administrator '{username}' created successfully")

    @app.cli.command("sync-project-schema")
    def sync_project_schema():
        """Repair local schema drift for the project-centric model."""
        from .models import (
            ApplicationEnvironment,
            KubernetesCluster,
            Project,
            ProjectMember,
        )

        engine = db.engine
        ProjectMember.__table__.create(engine, checkfirst=True)
        KubernetesCluster.__table__.create(engine, checkfirst=True)

        def has_column(table_name, column_name):
            return column_name in {item["name"] for item in inspect(engine).get_columns(table_name)}

        def has_unique_key(table_name, key_name):
            rows = db.session.execute(text(f"SHOW INDEX FROM {table_name} WHERE Key_name = :key"), {"key": key_name}).fetchall()
            return any(row[1] == 0 for row in rows)

        if not has_column("projects", "key"):
            db.session.execute(text("ALTER TABLE projects ADD COLUMN `key` VARCHAR(64) NULL"))
            db.session.commit()
        db.session.execute(text("UPDATE projects SET `key` = CONCAT('project-', id) WHERE `key` IS NULL OR `key` = ''"))
        db.session.commit()
        db.session.execute(text("ALTER TABLE projects MODIFY COLUMN `key` VARCHAR(64) NOT NULL"))
        db.session.commit()
        if not db.session.execute(text("SHOW INDEX FROM projects WHERE Key_name = 'ix_projects_key'" )).fetchall():
            db.session.execute(text("CREATE UNIQUE INDEX ix_projects_key ON projects (`key`)"))
            db.session.commit()

        default_project_id = db.session.execute(text("SELECT id FROM projects WHERE `key` = 'default' LIMIT 1")).scalar()
        if default_project_id is None:
            db.session.execute(text(
                "INSERT INTO projects (`key`, name, description, created_at, updated_at) "
                "VALUES ('default', 'Default Project', '系统默认项目', UTC_TIMESTAMP(), UTC_TIMESTAMP())"
            ))
            db.session.commit()
            default_project_id = db.session.execute(text("SELECT id FROM projects WHERE `key` = 'default' LIMIT 1")).scalar()

        db.session.execute(
            text("UPDATE applications SET project_id = :project_id WHERE project_id IS NULL"),
            {"project_id": default_project_id},
        )
        db.session.commit()

        if has_unique_key("applications", "name"):
            db.session.execute(text("ALTER TABLE applications DROP INDEX name"))
            db.session.commit()

        if not has_column("container_registries", "project_id"):
            db.session.execute(text("ALTER TABLE container_registries ADD COLUMN project_id INT NULL"))
            db.session.commit()
            db.session.execute(text(
                "ALTER TABLE container_registries "
                "ADD CONSTRAINT fk_container_registries_project_id_projects "
                "FOREIGN KEY (project_id) REFERENCES projects (id)"
            ))
            db.session.commit()
            db.session.execute(text("CREATE INDEX ix_container_registries_project_id ON container_registries (project_id)"))
            db.session.commit()
        db.session.execute(
            text("UPDATE container_registries SET project_id = :project_id WHERE project_id IS NULL"),
            {"project_id": default_project_id},
        )
        db.session.commit()
        if has_unique_key("container_registries", "name"):
            db.session.execute(text("ALTER TABLE container_registries DROP INDEX name"))
            db.session.commit()

        if not has_column("application_environments", "kubernetes_cluster_id"):
            db.session.execute(text("ALTER TABLE application_environments ADD COLUMN kubernetes_cluster_id INT NULL"))
            db.session.commit()
            db.session.execute(text(
                "ALTER TABLE application_environments "
                "ADD CONSTRAINT fk_app_env_cluster "
                "FOREIGN KEY (kubernetes_cluster_id) REFERENCES kubernetes_clusters (id)"
            ))
            db.session.commit()
            db.session.execute(text(
                "CREATE INDEX ix_application_environments_kubernetes_cluster_id "
                "ON application_environments (kubernetes_cluster_id)"
            ))
            db.session.commit()

        current_version = db.session.execute(text("SELECT version_num FROM alembic_version")).scalar()
        if current_version != "f1a2b3c4d5e6":
            db.session.execute(text("UPDATE alembic_version SET version_num = 'f1a2b3c4d5e6'"))
            db.session.commit()

        print("Project-centric schema synced successfully")

    @app.errorhandler(ApiError)
    def handle_api_error(exc):
        return failure(exc.message, exc.code, exc.status_code, exc.details)

    @app.errorhandler(404)
    def handle_not_found(_exc):
        return failure("接口不存在", "NOT_FOUND", 404)

    @app.errorhandler(RequestEntityTooLarge)
    def handle_request_too_large(_exc):
        return failure("请求体过大", "REQUEST_TOO_LARGE", 413)

    @app.errorhandler(ConfigException)
    def handle_kubernetes_config_error(exc):
        return failure(
            "无法读取 Kubernetes 配置，请检查 ~/.kube/config",
            "KUBERNETES_CONFIG_ERROR",
            503,
            str(exc),
        )

    @app.errorhandler(ApiException)
    def handle_kubernetes_api_error(exc):
        return failure(
            f"Kubernetes API 请求失败: {exc.reason}",
            "KUBERNETES_API_ERROR",
            502,
            {"status": exc.status, "body": exc.body},
        )

    @app.errorhandler(Exception)
    def handle_unexpected(exc):
        app.logger.exception("Unhandled error")
        return failure(str(exc) if app.debug else "服务内部错误")

    return app
