from flask import Blueprint, g, request

from app.models import ApprovalRecord, Application
from app.services.approval_service import ApprovalService
from app.utils.errors import ApiError
from app.utils.response import success
from app.utils.validation import json_object, require_positive_int, require_string

bp = Blueprint("approvals", __name__, url_prefix="/api/approvals")


def get_approval(approval_id):
    item = ApprovalRecord.query.get(approval_id)
    if not item:
        raise ApiError("审批记录不存在", 404, "APPROVAL_NOT_FOUND")
    return item


@bp.get("")
def list_approvals():
    page = max(request.args.get("page", 1, type=int), 1)
    page_size = min(max(request.args.get("pageSize", 20, type=int), 1), 100)
    query = ApprovalRecord.query
    if request.args.get("status"):
        query = query.filter_by(status=request.args["status"])
    if request.args.get("environment"):
        query = query.filter_by(environment=request.args["environment"])
    pagination = query.order_by(ApprovalRecord.created_at.desc()).paginate(
        page=page, per_page=page_size, error_out=False
    )
    return success({
        "items": [item.to_dict() for item in pagination.items],
        "page": page,
        "pageSize": page_size,
        "total": pagination.total,
    })


@bp.post("")
def submit_approval():
    payload = json_object(request.get_json(silent=True), required=True)
    application_id = require_positive_int(payload, "application_id")
    app = Application.query.get(application_id)
    if not app:
        raise ApiError("应用不存在", 404, "APPLICATION_NOT_FOUND")
    item = ApprovalService().submit(
        app, payload, g.current_user.username
    )
    return success(item.to_dict(), "发布审批已提交", 201)


@bp.post("/<int:approval_id>/approve")
def approve(approval_id):
    payload = json_object(request.get_json(silent=True))
    item = ApprovalService().approve(
        get_approval(approval_id),
        g.current_user.username,
        payload.get("comment"),
    )
    return success(item.to_dict(), "审批通过，PipelineRun 已创建")


@bp.post("/<int:approval_id>/reject")
def reject(approval_id):
    payload = json_object(request.get_json(silent=True), required=True)
    comment = require_string(payload, "comment")
    item = ApprovalService().reject(
        get_approval(approval_id),
        g.current_user.username,
        comment,
    )
    return success(item.to_dict(), "审批已拒绝")
