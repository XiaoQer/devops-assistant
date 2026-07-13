import os


def _comma_separated_env(name, default):
    return [
        value.strip()
        for value in os.getenv(name, default).split(",")
        if value.strip()
    ]


class Config:
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", "16384"))
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://devops:devops@127.0.0.1:3307/devops_platform"
        "?charset=utf8mb4",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
    TEKTON_NAMESPACE = os.getenv("TEKTON_NAMESPACE", "devops-platform")
    DEFAULT_IMAGE_REGISTRY = os.getenv("DEFAULT_IMAGE_REGISTRY", "registry.local")
    AUTO_CREATE_SCHEMA = os.getenv("AUTO_CREATE_SCHEMA", "false").lower() == "true"
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    AUTH_SESSION_HOURS = int(os.getenv("AUTH_SESSION_HOURS", "8"))
    AUTH_COOKIE_NAME = os.getenv("AUTH_COOKIE_NAME", "aegis_session")
    AUTH_CSRF_COOKIE_NAME = os.getenv("AUTH_CSRF_COOKIE_NAME", "aegis_csrf")
    AUTH_COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true"
    CORS_ORIGINS = _comma_separated_env(
        "CORS_ORIGINS",
        "http://localhost:5173",
    )
