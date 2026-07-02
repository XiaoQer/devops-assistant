from flask import Flask
from flask import g, request
from flask_cors import CORS
from kubernetes.client.exceptions import ApiException
from kubernetes.config.config_exception import ConfigException
import uuid

from .config import Config
from .extensions import db, migrate
from .routes import (
    applications_bp, health_bp, pipelines_bp, environments_bp, releases_bp,
    approvals_bp, registries_bp, ai_bp,
)
from .utils.errors import ApiError
from .utils.response import failure
from .services.release_service import ReleaseService


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    CORS(app)
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
    app.register_blueprint(registries_bp)
    app.register_blueprint(ai_bp)

    @app.before_request
    def attach_trace_id():
        g.trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())

    @app.after_request
    def return_trace_id(response):
        response.headers["X-Trace-ID"] = getattr(g, "trace_id", "")
        return response

    @app.cli.command("sync-deliveries")
    def sync_deliveries():
        """Synchronize pending Tekton runs into delivery records."""
        count = ReleaseService().sync_all()
        print(f"Synced {count} pending delivery records")

    @app.errorhandler(ApiError)
    def handle_api_error(exc):
        return failure(exc.message, exc.code, exc.status_code, exc.details)

    @app.errorhandler(404)
    def handle_not_found(_exc):
        return failure("接口不存在", "NOT_FOUND", 404)

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
