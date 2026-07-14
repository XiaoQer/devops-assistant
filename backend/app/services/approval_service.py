from datetime import datetime, timezone

from app.extensions import db
from app.models import ApprovalRecord, ApplicationEnvironment
from app.utils.errors import ApiError
from .application_service import ApplicationService


class ApprovalService:
    def submit(self, app, payload, applicant):
        environment_name = payload.get("environment", "prod")
        environment = ApplicationEnvironment.query.filter_by(
            application_id=app.id, environment_name=environment_name
        ).first()
        if not environment:
            raise ApiError("目标环境不存在", 404, "ENVIRONMENT_NOT_FOUND")
        duplicate = ApprovalRecord.query.filter_by(
            application_id=app.id,
            project_id=app.project_id,
            environment=environment_name,
            image_tag=payload.get("image_tag", app.image_tag),
            status="Pending",
        ).first()
        if duplicate:
            return duplicate
        approval = ApprovalRecord(
            application_id=app.id,
            project_id=app.project_id,
            environment=environment_name,
            namespace=environment.namespace,
            image_name=app.image_name,
            image_tag=payload.get("image_tag", app.image_tag),
            git_branch=payload.get("git_branch", app.branch),
            git_commit=payload.get("git_commit"),
            applicant=applicant,
            comment=payload.get("comment"),
        )
        db.session.add(approval)
        db.session.commit()
        return approval

    def approve(self, approval, approver, comment=None):
        if approval.status != "Pending":
            raise ApiError("审批单已处理", 409, "APPROVAL_ALREADY_PROCESSED")
        execution, _release = ApplicationService().deploy(
            approval.application,
            {
                "environment": approval.environment,
                "namespace": approval.namespace,
                "image_tag": approval.image_tag,
                "git_branch": approval.git_branch,
                "git_commit": approval.git_commit,
            },
            approval.applicant,
        )
        approval.status = "Approved"
        approval.approver = approver
        approval.comment = comment or approval.comment
        approval.pipeline_run_name = execution.pipeline_run_name
        approval.approved_at = datetime.now(timezone.utc)
        db.session.commit()
        return approval

    def reject(self, approval, approver, comment):
        if approval.status != "Pending":
            raise ApiError("审批单已处理", 409, "APPROVAL_ALREADY_PROCESSED")
        approval.status = "Rejected"
        approval.approver = approver
        approval.comment = comment
        approval.rejected_at = datetime.now(timezone.utc)
        db.session.commit()
        return approval
