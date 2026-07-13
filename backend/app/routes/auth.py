from flask import Blueprint, current_app, g, make_response, request

from app.services.auth_service import AuthService
from app.utils.errors import ApiError
from app.utils.response import success


bp = Blueprint("auth", __name__, url_prefix="/api/auth")
auth_service = AuthService()


def _cookie_options(http_only):
    return {
        "max_age": current_app.config["AUTH_SESSION_HOURS"] * 3600,
        "secure": current_app.config["AUTH_COOKIE_SECURE"],
        "httponly": http_only,
        "samesite": "Lax",
        "path": "/",
    }


def _login_payload():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ApiError("请求体必须是 JSON 对象", 400, "VALIDATION_ERROR")
    for field in ("username", "password"):
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ApiError(f"{field} 必须是非空字符串", 400, "VALIDATION_ERROR")
    if len(payload["username"]) > 120:
        raise ApiError("username 长度不能超过 120", 400, "VALIDATION_ERROR")
    if len(payload["password"]) > 4096:
        raise ApiError("password 长度不能超过 4096", 400, "VALIDATION_ERROR")
    return payload


@bp.post("/login")
def login():
    payload = _login_payload()
    result = auth_service.login(payload["username"].strip(), payload["password"])
    response = make_response(
        success(
            {
                "user": result.user.to_dict(),
                "csrf_token": result.csrf_token,
            },
            "登录成功",
        )
    )
    response.set_cookie(
        current_app.config["AUTH_COOKIE_NAME"],
        result.session_token,
        **_cookie_options(http_only=True),
    )
    response.set_cookie(
        current_app.config["AUTH_CSRF_COOKIE_NAME"],
        result.csrf_token,
        **_cookie_options(http_only=False),
    )
    return response


@bp.get("/me")
def me():
    csrf_token = request.cookies.get(
        current_app.config["AUTH_CSRF_COOKIE_NAME"]
    )
    rotated = not auth_service.verify_csrf(g.current_session, csrf_token)
    if rotated:
        csrf_token = auth_service.rotate_csrf(g.current_session)
    response = make_response(
        success(
            {
                "user": g.current_user.to_dict(),
                "csrf_token": csrf_token,
            }
        )
    )
    if rotated:
        response.set_cookie(
            current_app.config["AUTH_CSRF_COOKIE_NAME"],
            csrf_token,
            **_cookie_options(http_only=False),
        )
    return response


@bp.post("/logout")
def logout():
    auth_service.revoke(g.current_session)
    response = make_response(success(None, "已退出登录"))
    response.delete_cookie(
        current_app.config["AUTH_COOKIE_NAME"],
        path="/",
        secure=current_app.config["AUTH_COOKIE_SECURE"],
        httponly=True,
        samesite="Lax",
    )
    response.delete_cookie(
        current_app.config["AUTH_CSRF_COOKIE_NAME"],
        path="/",
        secure=current_app.config["AUTH_COOKIE_SECURE"],
        httponly=False,
        samesite="Lax",
    )
    return response
