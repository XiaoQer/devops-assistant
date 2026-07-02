from flask import Blueprint, request

from app.services.ai_assistant_service import AiAssistantService
from app.utils.response import success

bp = Blueprint("ai", __name__, url_prefix="/api/ai")


@bp.post("/intent/resolve")
def resolve_intent():
    payload = request.get_json(silent=True) or {}
    text = payload.get("text", "")
    result = AiAssistantService().analyze_user_intent(text)
    return success(result, "意图解析完成")

