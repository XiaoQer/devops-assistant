from app.utils.errors import ApiError


def json_object(payload, *, required=False):
    if payload is None:
        if required:
            raise ApiError("请求体必须为 JSON 对象", 400, "INVALID_REQUEST_BODY")
        return {}
    if not isinstance(payload, dict):
        raise ApiError("请求体必须为 JSON 对象", 400, "INVALID_REQUEST_BODY")
    return payload


def require_fields(payload, *fields):
    missing = [
        field for field in fields
        if payload.get(field) is None
        or (isinstance(payload.get(field), str) and not payload.get(field).strip())
    ]
    if missing:
        raise ApiError(
            f"缺少必填字段: {', '.join(missing)}",
            400,
            "VALIDATION_ERROR",
            {"fields": missing},
        )
    return payload


def require_string(payload, field, *, allow_blank=False):
    value = payload.get(field)
    if value is None:
        raise ApiError(
            f"{field} 为必填字段", 400, "VALIDATION_ERROR", {"field": field}
        )
    if not isinstance(value, str):
        raise ApiError(
            f"{field} 必须为字符串",
            400,
            "VALIDATION_ERROR",
            {"field": field},
        )
    value = value.strip()
    if not value and not allow_blank:
        raise ApiError(
            f"{field} 不能为空", 400, "VALIDATION_ERROR", {"field": field}
        )
    return value


def require_positive_int(payload, field):
    value = payload.get(field)
    if value is None or value == "":
        raise ApiError(
            f"{field} 为必填字段", 400, "VALIDATION_ERROR", {"field": field}
        )
    try:
        value = int(value)
    except (TypeError, ValueError) as exc:
        raise ApiError(
            f"{field} 必须为正整数",
            400,
            "VALIDATION_ERROR",
            {"field": field},
        ) from exc
    if value <= 0:
        raise ApiError(
            f"{field} 必须为正整数",
            400,
            "VALIDATION_ERROR",
            {"field": field},
        )
    return value


def require_query_positive_int(args, field):
    value = args.get(field)
    if value is None or value == "":
        raise ApiError(
            f"{field} 为必填参数", 400, "VALIDATION_ERROR", {"field": field}
        )
    try:
        value = int(value)
    except (TypeError, ValueError) as exc:
        raise ApiError(
            f"{field} 必须为正整数",
            400,
            "VALIDATION_ERROR",
            {"field": field},
        ) from exc
    if value <= 0:
        raise ApiError(
            f"{field} 必须为正整数",
            400,
            "VALIDATION_ERROR",
            {"field": field},
        )
    return value
