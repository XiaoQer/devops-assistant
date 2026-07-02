import os


class Config:
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
