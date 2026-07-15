from datetime import datetime, timezone

from .application_runtime_service import ApplicationRuntimeService
from .delivery_context_service import DeliveryContextService
from app.utils.errors import ApiError
from .runtime_exec_service import RuntimeExecService


class ProjectRuntimeService:
    ERROR_MESSAGE = "暂时无法读取该环境的 Kubernetes 运行状态"

    def environments(self, project, actor=None):
        result = {}
        for application in project.applications:
            for environment in application.environments:
                approval_required = bool(getattr(environment, "approval_required", False))
                result.setdefault(environment.environment_name, {
                    "name": environment.environment_name,
                    "display_name": environment.display_name or environment.environment_name,
                    "approval_required": approval_required,
                    "terminal_allowed": (
                        not approval_required
                        or (actor is not None and RuntimeExecService.has_permission(project, actor))
                    ),
                })
        return [result[name] for name in sorted(result)]

    def inventory(
        self, project, environment_name, resource, page, page_size,
        query=None, status=None,
    ):
        targets = []
        for application in sorted(project.applications, key=lambda item: (item.name, item.id)):
            if any(env.environment_name == environment_name for env in application.environments):
                targets.append(application)
        if not targets:
            raise ApiError("目标环境不存在", 404, "ENVIRONMENT_NOT_FOUND")

        runtime = ApplicationRuntimeService()
        resolver = DeliveryContextService()
        items = []
        cluster_ids = set()
        environment_meta = None
        summary = {"deployments": 0, "healthy_pods": 0, "unhealthy_pods": 0, "restart_count": 0}
        for application in targets:
            try:
                context = resolver.resolve(project, application, environment_name)
                cluster_ids.add(context.cluster.id)
                if len(cluster_ids) > 1:
                    raise ApiError(
                        "同名 Environment 绑定了不同 Kubernetes 集群",
                        409,
                        "RUNTIME_ENVIRONMENT_CONFLICT",
                    )
                environment_meta = {
                    "name": environment_name,
                    "display_name": context.environment.display_name or environment_name,
                    "cluster_name": context.cluster.name,
                }
                data = runtime.status(context)
                pods = data.get("pods", [])
                deployment = data.get("deployment")
                if deployment:
                    summary["deployments"] += 1
                    items.append({
                        "resource": "deployment",
                        "application_id": application.id,
                        "application_name": application.name,
                        "namespace": context.namespace,
                        "status": data.get("status", "Unknown"),
                        "deployment": deployment,
                        "pod_count": len(pods),
                        "restart_count": sum(int(pod.get("restart_count") or 0) for pod in pods),
                    })
                for pod in pods:
                    summary["healthy_pods" if pod.get("ready") else "unhealthy_pods"] += 1
                    summary["restart_count"] += int(pod.get("restart_count") or 0)
                    if resource == "pods":
                        items.append({
                            "resource": "pod",
                            "application_id": application.id,
                            "application_name": application.name,
                            "namespace": context.namespace,
                            **pod,
                        })
            except ApiError:
                raise
            except Exception:
                if resource == "deployments":
                    items.append({
                        "resource": "deployment",
                        "application_id": application.id,
                        "application_name": application.name,
                        "namespace": next(env.namespace for env in application.environments if env.environment_name == environment_name),
                        "status": "Unknown",
                        "deployment": None,
                        "pod_count": 0,
                        "restart_count": 0,
                        "error": {"code": "RUNTIME_TARGET_UNAVAILABLE", "message": self.ERROR_MESSAGE},
                    })

        if resource == "pods":
            items = [item for item in items if item.get("resource") == "pod"]
        needle = str(query or "").strip().lower()
        if needle:
            items = [item for item in items if needle in " ".join(str(value) for value in (
                item.get("application_name"), item.get("name"), item.get("namespace"),
                (item.get("deployment") or {}).get("name"),
                " ".join((item.get("deployment") or {}).get("images", [])),
            )).lower()]
        if status:
            items = [item for item in items if item.get("status") == status]
        total = len(items)
        start = (page - 1) * page_size
        pages = (total + page_size - 1) // page_size
        return {
            "environment": environment_meta or {"name": environment_name, "display_name": environment_name},
            "summary": summary,
            "items": items[start:start + page_size],
            "pagination": {"page": page, "page_size": page_size, "total": total, "pages": pages},
            "refreshed_at": datetime.now(timezone.utc).isoformat(),
        }

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
