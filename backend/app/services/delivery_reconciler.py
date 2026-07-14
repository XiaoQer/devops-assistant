from datetime import datetime

from flask import current_app

from app.extensions import db
from app.models import Application, ApplicationReleaseBatch
from app.services.approval_service import ApprovalService
from app.services.application_service import ApplicationService
from app.services.tekton_service import TektonService


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
                if target.status != "Pending":
                    continue
                env = target.environment
                if env.approval_required:
                    approval = ApprovalService().submit(batch.application, {
                        "environment": env.environment_name,
                        "build_version_id": version.id,
                        "git_branch": batch.branch,
                        "git_commit": batch.git_commit,
                    }, batch.created_by)
                    target.approval_id = approval.id
                    target.status = "WaitingApproval"
                    continue
                try:
                    execution, _release = ApplicationService().deploy(batch.application, {
                        "environment": env.environment_name,
                        "build_version_id": version.id,
                        "git_branch": batch.branch,
                        "git_commit": batch.git_commit,
                    }, batch.created_by)
                    target.pipeline_run_name = execution.pipeline_run_name
                    target.build_version_id = version.id
                    target.status = "Running"
                except Exception as exc:
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
        if statuses and statuses <= {"Succeeded"}:
            batch.status = "Succeeded"
        elif "Failed" in statuses or "BuildFailed" in statuses:
            batch.status = "PartialFailed" if "Succeeded" in statuses else batch.status
        db.session.commit()
        return batch.to_dict()

    def reconcile_pending(self):
        batches = ApplicationReleaseBatch.query.filter(
            ApplicationReleaseBatch.status.in_(["Building", "Deploying", "PartialFailed"])
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
                    "PartialFailed",
                ]),
            )
            .all()
        )
        for batch in batches:
            self.reconcile_batch(batch.id)
        return len(batches)
