from datetime import datetime, timedelta, timezone

from flask import current_app

from app.extensions import db
from app.models import Application, ApplicationReleaseBatch, ApplicationReleaseTarget
from app.services.approval_service import ApprovalService
from app.services.application_service import ApplicationService
from app.services.tekton_service import TektonService
from app.utils.errors import ApiError


class DeliveryReconciler:
    def reconcile_batch(self, batch_id):
        batch = db.session.get(ApplicationReleaseBatch, batch_id)
        if not batch:
            return {"status": "NotFound"}
        version = batch.build_version
        if not version:
            return batch.to_dict()
        namespace = current_app.config["TEKTON_NAMESPACE"]
        if version.pipeline_run_name and version.status in {"Pending", "Running"}:
            try:
                status = TektonService().get_pipeline_run_status(version.pipeline_run_name, namespace)
                version.status = status.get("status", version.status)
                version.error_message = status.get("message") if version.status == "Failed" else None
                if status.get("finished_at") and not version.finished_at:
                    version.finished_at = datetime.fromisoformat(status["finished_at"].replace("Z", "+00:00"))
            except Exception:
                pass
        if version.status == "Succeeded":
            batch.status = "Deploying"
            for target in batch.targets:
                if target.status not in {"Pending", "Starting"}:
                    continue
                claim_token = self.claim_target(target.id)
                if not claim_token:
                    continue
                claim = {"token": claim_token}

                def renew_claim():
                    claim["token"] = self.renew_target_claim(
                        target.id,
                        claim["token"],
                    )
                    return claim["token"]

                target = db.session.get(ApplicationReleaseTarget, target.id)
                env = target.environment
                if env.approval_required:
                    try:
                        renew_claim()
                    except ApiError as exc:
                        if exc.code != "RELEASE_TARGET_CLAIM_LOST":
                            raise
                        db.session.rollback()
                        db.session.expire_all()
                        continue
                    approval = ApprovalService().submit(batch.application, {
                        "environment": env.environment_name,
                        "build_version_id": version.id,
                        "git_branch": batch.branch,
                        "git_commit": batch.git_commit,
                    }, batch.created_by, release_target_id=target.id)
                    target.approval_id = approval.id
                    target.status = "WaitingApproval"
                    continue
                try:
                    existing_run = TektonService().find_pipeline_run_by_label(
                        namespace,
                        "aegis.dev/release-target-id",
                        str(target.id),
                    )
                    execution, _release = ApplicationService().deploy(batch.application, {
                        "environment": env.environment_name,
                        "build_version_id": version.id,
                        "git_branch": batch.branch,
                        "git_commit": batch.git_commit,
                    }, batch.created_by, recovery={
                        "release_target_id": target.id,
                        "existing_pipeline_run_name": existing_run,
                        "renew_claim": renew_claim,
                    })
                    target.pipeline_run_name = execution.pipeline_run_name
                    target.build_version_id = version.id
                    target.status = "Running"
                except Exception as exc:
                    try:
                        renew_claim()
                    except ApiError as claim_error:
                        if claim_error.code != "RELEASE_TARGET_CLAIM_LOST":
                            raise
                        db.session.rollback()
                        db.session.expire_all()
                        continue
                    target = db.session.get(ApplicationReleaseTarget, target.id)
                    target.status = "Failed"
                    target.error_message = str(exc)[:500]
        elif version.status == "Failed":
            batch.status = "BuildFailed"
        for target in batch.targets:
            if target.status != "Running" or not target.pipeline_run_name:
                continue
            try:
                state = TektonService().get_pipeline_run_status(target.pipeline_run_name, namespace)
                target.status = {"Succeeded": "Succeeded", "Failed": "Failed"}.get(state.get("status"), "Running")
                if target.status == "Failed":
                    target.error_message = state.get("message")
            except Exception:
                pass
        statuses = {target.status for target in batch.targets}
        if version.status == "Succeeded":
            if not statuses or statuses == {"Succeeded"}:
                batch.status = "Succeeded"
            elif statuses == {"Failed"}:
                batch.status = "Failed"
            elif statuses == {"Rejected"}:
                batch.status = "Rejected"
            elif statuses <= {"Succeeded", "Failed", "Rejected"}:
                batch.status = "PartialFailed"
            else:
                batch.status = "Deploying"
        db.session.commit()
        return batch.to_dict()

    def claim_target(self, target_id):
        now = datetime.now(timezone.utc)
        claimed = ApplicationReleaseTarget.query.filter(
            ApplicationReleaseTarget.id == target_id,
            ApplicationReleaseTarget.status == "Pending",
        ).update(
            {
                ApplicationReleaseTarget.status: "Starting",
                ApplicationReleaseTarget.updated_at: now,
            },
            synchronize_session=False,
        )
        if claimed == 0:
            claimed = ApplicationReleaseTarget.query.filter(
                ApplicationReleaseTarget.id == target_id,
                ApplicationReleaseTarget.status == "Starting",
                ApplicationReleaseTarget.updated_at < now - timedelta(minutes=5),
            ).update(
                {ApplicationReleaseTarget.updated_at: now},
                synchronize_session=False,
            )
        db.session.commit()
        return now if claimed == 1 else None

    def renew_target_claim(self, target_id, claim_token):
        now = datetime.now(timezone.utc)
        renewed = ApplicationReleaseTarget.query.filter(
            ApplicationReleaseTarget.id == target_id,
            ApplicationReleaseTarget.status == "Starting",
            ApplicationReleaseTarget.updated_at == claim_token,
        ).update(
            {ApplicationReleaseTarget.updated_at: now},
            synchronize_session=False,
        )
        db.session.commit()
        if renewed != 1:
            raise ApiError(
                "发布目标认领已失效，请等待当前协调任务完成",
                409,
                "RELEASE_TARGET_CLAIM_LOST",
            )
        return now

    def reconcile_pending(self):
        batches = ApplicationReleaseBatch.query.filter(
            ApplicationReleaseBatch.status.in_(["Building", "Deploying"])
        ).all()
        for batch in batches:
            self.reconcile_batch(batch.id)
        return len(batches)

    def reconcile_project(self, project_id):
        batches = (
            ApplicationReleaseBatch.query.join(Application)
            .filter(
                ApplicationReleaseBatch.project_id == project_id,
                Application.project_id == project_id,
                ApplicationReleaseBatch.status.in_([
                    "Building",
                    "Deploying",
                ]),
            )
            .all()
        )
        for batch in batches:
            self.reconcile_batch(batch.id)
        return len(batches)
