from datetime import datetime, timezone

from .application_runtime_service import ApplicationRuntimeService
from .delivery_context_service import DeliveryContextService


class ProjectRuntimeService:
    ERROR_MESSAGE = "暂时无法读取该环境的 Kubernetes 运行状态"

    def overview(self, project):
        groups = {}
        summary = {
            "environments": 0,
            "deployments": 0,
            "healthy_pods": 0,
            "unhealthy_pods": 0,
            "restart_count": 0,
        }
        runtime = ApplicationRuntimeService()
        resolver = DeliveryContextService()

        applications = sorted(project.applications, key=lambda item: (item.name, item.id))
        for application in applications:
            environments = sorted(
                application.environments,
                key=lambda item: item.environment_name,
            )
            for environment in environments:
                group = groups.setdefault(
                    environment.environment_name,
                    {
                        "name": environment.environment_name,
                        "display_name": environment.display_name or environment.environment_name,
                        "applications": [],
                    },
                )
                item = {
                    "application_id": application.id,
                    "application_name": application.name,
                    "namespace": environment.namespace,
                }
                try:
                    context = resolver.resolve(
                        project, application, environment.environment_name
                    )
                    data = runtime.status(context)
                    group["cluster_name"] = getattr(
                        context.cluster, "name", environment.cluster_name
                    )
                    item.update({
                        "status": data.get("status", "Unknown"),
                        "deployment": data.get("deployment"),
                        "pods": data.get("pods", []),
                    })
                    if data.get("deployment"):
                        summary["deployments"] += 1
                    for pod in item["pods"]:
                        if pod.get("ready"):
                            summary["healthy_pods"] += 1
                        else:
                            summary["unhealthy_pods"] += 1
                        summary["restart_count"] += int(pod.get("restart_count") or 0)
                except Exception:
                    group.setdefault("cluster_name", environment.cluster_name)
                    item.update({
                        "status": "Unknown",
                        "deployment": None,
                        "pods": [],
                        "error": {
                            "code": "RUNTIME_TARGET_UNAVAILABLE",
                            "message": self.ERROR_MESSAGE,
                        },
                    })
                group["applications"].append(item)

        environments = [groups[name] for name in sorted(groups)]
        summary["environments"] = len(environments)
        return {
            "summary": summary,
            "environments": environments,
            "refreshed_at": datetime.now(timezone.utc).isoformat(),
        }
