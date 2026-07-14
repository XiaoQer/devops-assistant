from sqlalchemy.orm import selectinload

from app.models import (
    Application,
    ApplicationReleaseBatch,
)


class CicdWorkbenchService:
    def list_applications(self, project_id, query=None, status=None):
        applications = (
            Application.query.options(
                selectinload(Application.project),
                selectinload(Application.environments),
                selectinload(Application.build_versions),
                selectinload(Application.executions),
                selectinload(Application.release_batches).selectinload(
                    ApplicationReleaseBatch.targets
                ),
            )
            .filter(Application.project_id == project_id)
            .all()
        )
        normalized_query = (query or "").strip().lower()
        normalized_status = (status or "").strip().lower()
        items = []
        for application in applications:
            if normalized_query and normalized_query not in (
                f"{application.name} {application.repo_url}".lower()
            ):
                continue
            item = self._summary(application)
            if (
                normalized_status
                and item["activity_status"].lower() != normalized_status
            ):
                continue
            items.append(item)
        items.sort(
            key=lambda item: item["last_activity_at"] or "",
            reverse=True,
        )
        return items

    def _summary(self, application):
        builds = [
            build
            for build in application.build_versions
            if build.project_id == application.project_id
        ]
        batches = [
            batch
            for batch in application.release_batches
            if batch.project_id == application.project_id
        ]
        executions = [
            execution
            for execution in application.executions
            if execution.project_id == application.project_id
        ]
        latest_build = builds[0] if builds else None
        latest_batch = batches[0] if batches else None
        latest_execution = executions[0] if executions else None
        candidates = []
        if latest_build:
            candidates.append((latest_build.created_at, 1, latest_build.status))
        if latest_batch:
            candidates.append((latest_batch.created_at, 2, latest_batch.status))
        if latest_execution:
            candidates.append((
                latest_execution.updated_at or latest_execution.created_at,
                3,
                latest_execution.status,
            ))
        if not candidates:
            candidates.append((
                application.updated_at or application.created_at,
                0,
                application.status or "Unknown",
            ))
        activity_at, _priority, activity_status = max(
            candidates,
            key=lambda candidate: (candidate[0], candidate[1]),
        )
        return {
            "application": application.to_dict(include_spec=False),
            "latest_build": latest_build.to_dict() if latest_build else None,
            "latest_batch": latest_batch.to_dict() if latest_batch else None,
            "latest_execution": (
                latest_execution.to_dict() if latest_execution else None
            ),
            "available_environments": [
                environment.to_dict() for environment in application.environments
            ],
            "activity_status": activity_status or "Unknown",
            "last_activity_at": activity_at.isoformat() if activity_at else None,
        }
