from .applications import bp as applications_bp
from .health import bp as health_bp
from .pipelines import bp as pipelines_bp
from .environments import bp as environments_bp
from .releases import bp as releases_bp
from .approvals import bp as approvals_bp
from .ai import bp as ai_bp
from .projects import bp as projects_bp
from .auth import bp as auth_bp

__all__ = [
    "applications_bp", "health_bp", "pipelines_bp", "environments_bp",
    "releases_bp", "approvals_bp", "ai_bp", "projects_bp",
    "auth_bp",
]
