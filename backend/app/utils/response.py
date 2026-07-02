from datetime import datetime, timezone
from flask import jsonify, g


def envelope(successful, message):
    return {
        "success": successful,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trace_id": getattr(g, "trace_id", None),
    }


def success(data=None, message="ok", status=200):
    return jsonify({**envelope(True, message), "data": data}), status


def failure(message, code="INTERNAL_ERROR", status=500, details=None):
    body = {**envelope(False, message), "error": {"code": code}}
    if details is not None:
        body["error"]["details"] = details
    return jsonify(body), status
