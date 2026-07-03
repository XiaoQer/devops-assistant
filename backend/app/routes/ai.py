from flask import Blueprint, request

from app.services.ai_assistant_service import AiAssistantService
from app.utils.response import success
from app.utils.validation import json_object, require_string

bp = Blueprint("ai", __name__, url_prefix="/api/ai")


@bp.post("/intent/resolve")
def resolve_intent():
    payload = json_object(request.get_json(silent=True), required=True)
    text = require_string(payload, "text")
    result = AiAssistantService().analyze_user_intent(text)
    return success(result, "意图解析完成")

