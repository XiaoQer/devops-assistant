from flask import Blueprint

from app.services.kubernetes_service import KubernetesService
from app.utils.response import failure, success

bp = Blueprint("health", __name__, url_prefix="/api/health")


@bp.get("")
def health():
    return success({"status": "ok"})


@bp.get("/kubernetes")
def kubernetes_health():
    try:
        return success(KubernetesService().health())
    except Exception as exc:
        return failure(
            "无法连接 Kubernetes",
            "KUBERNETES_UNAVAILABLE",
            503,
            {"connected": False, "reason": str(exc)},
        )

