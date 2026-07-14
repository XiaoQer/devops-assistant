from datetime import datetime, timezone

from app.extensions import db
from app.models import ApprovalRecord, ApplicationEnvironment, ApplicationReleaseTarget
from app.utils.errors import ApiError
from .application_service import ApplicationService
from .build_version_service import BuildVersionService


class ApprovalService:
    def submit(self, app, payload, applicant):
        environment_name = payload.get("environment", "prod")
        environment = ApplicationEnvironment.query.filter_by(
            application_id=app.id, environment_name=environment_name
        ).first()
        if not environment:
            raise ApiError("目标环境不存在", 404, "ENVIRONMENT_NOT_FOUND")
        build_version = None
        if payload.get("build_version_id"):
            build_version = BuildVersionService().require_publishable(app, int(payload["build_version_id"]))
        image_tag = build_version.image_tag if build_version else payload.get("image_tag", app.image_tag)
        image_name = build_version.image_name if build_version else app.image_name
        duplicate = ApprovalRecord.query.filter_by(
            application_id=app.id,
            project_id=app.project_id,
            environment=environment_name,
            image_tag=image_tag,
            status="Pending",
        ).first()
        if duplicate:
            return duplicate
        approval = ApprovalRecord(
            application_id=app.id,
            project_id=app.project_id,
            environment=environment_name,
            namespace=environment.namespace,
            build_version_id=build_version.id if build_version else None,
            image_name=image_name,
            image_tag=image_tag,
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
                "build_version_id": approval.build_version_id,
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
        target = ApplicationReleaseTarget.query.filter_by(approval_id=approval.id).first()
        if target:
            target.pipeline_run_name = execution.pipeline_run_name
            target.build_version_id = approval.build_version_id
            target.status = "Running"
            target.error_message = None
        db.session.commit()
        return approval

    def reject(self, approval, approver, comment):
        if approval.status != "Pending":
            raise ApiError("审批单已处理", 409, "APPROVAL_ALREADY_PROCESSED")
        approval.status = "Rejected"
        approval.approver = approver
        approval.comment = comment
        approval.rejected_at = datetime.now(timezone.utc)
        target = ApplicationReleaseTarget.query.filter_by(approval_id=approval.id).first()
        if target:
            target.status = "Rejected"
            target.error_message = comment
        db.session.commit()
        return approval
