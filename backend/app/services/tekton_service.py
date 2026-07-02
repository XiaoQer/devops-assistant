from kubernetes.client.exceptions import ApiException

from .kubernetes_service import KubernetesService


class TektonService:
    GROUP = "tekton.dev"
    VERSION = "v1"

    def __init__(self, kubernetes_service=None):
        self.kubernetes = kubernetes_service or KubernetesService()
        self.custom_api = self.kubernetes.custom_api
        self.core_api = self.kubernetes.core_api

    def create_pipeline_run(
        self, pipeline_name, app_name, repo_url, branch, image_name, image_tag,
        namespace, container_port, deploy_namespace=None, deployment_config=None,
    ):
        deployment_config = deployment_config or {}
        registry_secret_name = deployment_config.get("registry_secret_name")
        body = {
            "apiVersion": "tekton.dev/v1",
            "kind": "PipelineRun",
            "metadata": {
                "generateName": f"{app_name}-run-",
                "namespace": namespace,
                "labels": {"app.kubernetes.io/name": app_name},
            },
            "spec": {
                "taskRunTemplate": {
                    "serviceAccountName": "devops-platform-pipeline",
                    "podTemplate": {
                        "volumes": [{
                            "name": "docker-config",
                            "secret": {
                                "secretName": deployment_config.get(
                                    "registry_secret_name"
                                ) or "registry-credentials",
                                # A configured registry must never silently fall back
                                # to an anonymous push when its Secret is missing.
                                "optional": not bool(registry_secret_name),
                                "items": [{
                                    "key": ".dockerconfigjson",
                                    "path": "config.json",
                                }],
                            },
                        }]
                    },
                },
                "pipelineRef": {"name": pipeline_name},
                "workspaces": [{
                    "name": "source",
                    "volumeClaimTemplate": {
                        "spec": {
                            "accessModes": ["ReadWriteOnce"],
                            "resources": {"requests": {"storage": "1Gi"}},
                        }
                    },
                }],
                "params": [
                    {"name": "repo_url", "value": repo_url},
                    {"name": "branch", "value": branch},
                    {"name": "image_name", "value": image_name},
                    {"name": "image_tag", "value": image_tag},
                    {"name": "app_name", "value": app_name},
                    {"name": "namespace", "value": deploy_namespace or namespace},
                    {"name": "container_port", "value": str(container_port)},
                    {"name": "replicas", "value": str(deployment_config.get("replicas", 1))},
                    {"name": "cpu_request", "value": deployment_config.get("cpu_request", "100m")},
                    {"name": "cpu_limit", "value": deployment_config.get("cpu_limit", "500m")},
                    {"name": "memory_request", "value": deployment_config.get("memory_request", "128Mi")},
                    {"name": "memory_limit", "value": deployment_config.get("memory_limit", "512Mi")},
                    {"name": "deploy_strategy", "value": deployment_config.get("deploy_strategy", "RollingUpdate")},
                    {"name": "max_unavailable", "value": deployment_config.get("max_unavailable", "25%")},
                    {"name": "max_surge", "value": deployment_config.get("max_surge", "25%")},
                    {"name": "ingress_host", "value": deployment_config.get("ingress_host", "")},
                    {"name": "config_map_name", "value": deployment_config.get("config_map_name", f"{app_name}-config")},
                    {"name": "secret_name", "value": deployment_config.get("secret_name", f"{app_name}-secret")},
                    {"name": "registry_secret_name", "value": deployment_config.get("registry_secret_name", "")},
                ],
            },
        }
        result = self.custom_api.create_namespaced_custom_object(
            self.GROUP, self.VERSION, namespace, "pipelineruns", body
        )
        return result["metadata"]["name"]

    def get_pipeline_run_status(self, pipeline_run_name, namespace):
        run = self.custom_api.get_namespaced_custom_object(
            self.GROUP, self.VERSION, namespace, "pipelineruns", pipeline_run_name
        )
        status = run.get("status", {})
        condition = next(iter(status.get("conditions", [])), {})
        reason = condition.get("reason", "Pending")
        state = {"True": "Succeeded", "False": "Failed"}.get(
            condition.get("status"), reason
        )
        return {
            "name": pipeline_run_name,
            "status": state,
            "reason": reason,
            "message": condition.get("message"),
            "started_at": status.get("startTime"),
            "finished_at": status.get("completionTime"),
        }

    def list_pipeline_runs(self, namespace, limit=200):
        result = self.custom_api.list_namespaced_custom_object(
            self.GROUP, self.VERSION, namespace, "pipelineruns", limit=limit
        )
        runs = []
        for item in result.get("items", []):
            metadata = item.get("metadata", {})
            spec = item.get("spec", {})
            status = item.get("status", {})
            condition = next(iter(status.get("conditions", [])), {})
            reason = condition.get("reason", "Pending")
            state = {"True": "Succeeded", "False": "Failed"}.get(
                condition.get("status"), reason
            )
            params = {
                param["name"]: param.get("value")
                for param in spec.get("params", [])
            }
            pipeline_ref = spec.get("pipelineRef", {})
            runs.append({
                "name": metadata.get("name"),
                "namespace": metadata.get("namespace", namespace),
                "application": metadata.get("labels", {}).get(
                    "app.kubernetes.io/name"
                ),
                "pipeline": pipeline_ref.get("name"),
                "status": state,
                "reason": reason,
                "message": condition.get("message"),
                "repo_url": params.get("repo_url"),
                "branch": params.get("branch"),
                "image": (
                    f"{params.get('image_name')}:{params.get('image_tag')}"
                    if params.get("image_name") else None
                ),
                "started_at": status.get("startTime"),
                "finished_at": status.get("completionTime"),
                "created_at": metadata.get("creationTimestamp"),
            })
        return sorted(
            runs, key=lambda item: item.get("created_at") or "", reverse=True
        )

    def list_task_runs(self, pipeline_run_name, namespace):
        result = self.custom_api.list_namespaced_custom_object(
            self.GROUP,
            self.VERSION,
            namespace,
            "taskruns",
            label_selector=f"tekton.dev/pipelineRun={pipeline_run_name}",
        )
        task_runs = []
        for item in result.get("items", []):
            condition = next(iter(item.get("status", {}).get("conditions", [])), {})
            task_runs.append({
                "name": item["metadata"]["name"],
                "task_name": item["metadata"].get("labels", {}).get("tekton.dev/pipelineTask"),
                "status": condition.get("reason", "Pending"),
                "started_at": item.get("status", {}).get("startTime"),
                "finished_at": item.get("status", {}).get("completionTime"),
            })
        return task_runs

    def get_pipeline_run_logs(self, pipeline_run_name, namespace):
        pods = self.core_api.list_namespaced_pod(
            namespace,
            label_selector=f"tekton.dev/pipelineRun={pipeline_run_name}",
        ).items
        chunks = []
        task_pods = [
            pod for pod in pods
            if pod.metadata.labels.get("tekton.dev/taskRun")
        ]
        for pod in sorted(
            task_pods, key=lambda value: value.metadata.creation_timestamp
        ):
            statuses = {
                status.name: status
                for status in (pod.status.container_statuses or [])
            }
            # prepare/place-scripts 等 init container 属于 Tekton 内部实现，
            # 这里只展示真正的 Pipeline Step 日志。
            containers = [
                item.name for item in pod.spec.containers
                if item.name.startswith("step-")
            ]
            for container in containers:
                heading = f"===== {pod.metadata.name}/{container} ====="
                status = statuses.get(container)
                if not status:
                    chunks.append(f"{heading}\n等待容器状态...")
                    continue
                if status.state.waiting:
                    detail = status.state.waiting
                    message = f"等待启动: {detail.reason}"
                    if detail.message:
                        message += f"\n{detail.message}"
                    chunks.append(f"{heading}\n{message}")
                    continue
                try:
                    log = self.core_api.read_namespaced_pod_log(
                        pod.metadata.name, namespace, container=container, timestamps=True
                    )
                    chunks.append(f"{heading}\n{log or '该步骤没有输出日志。'}")
                except ApiException as exc:
                    state = status.state.terminated
                    if state:
                        message = (
                            f"容器已结束（{state.reason}，退出码 {state.exit_code}），"
                            "日志暂不可用。"
                        )
                    else:
                        message = "日志尚未就绪，请稍后刷新。"
                    chunks.append(f"{heading}\n{message}")
        return "\n\n".join(chunks)

    def get_pipeline_run_log_details(self, pipeline_run_name, namespace):
        pipeline = self.get_pipeline_run_status(pipeline_run_name, namespace)
        task_runs = self.list_task_runs(pipeline_run_name, namespace)
        pods = self.core_api.list_namespaced_pod(
            namespace,
            label_selector=f"tekton.dev/pipelineRun={pipeline_run_name}",
        ).items
        pods_by_task = {
            pod.metadata.labels.get("tekton.dev/taskRun"): pod
            for pod in pods
            if pod.metadata.labels.get("tekton.dev/taskRun")
        }
        tasks = []
        for task in task_runs:
            pod = pods_by_task.get(task["name"])
            logs = []
            if pod:
                statuses = {
                    item.name: item for item in (pod.status.container_statuses or [])
                }
                for container in pod.spec.containers:
                    if not container.name.startswith("step-"):
                        continue
                    status = statuses.get(container.name)
                    text = ""
                    if status and status.state.waiting:
                        text = f"等待启动: {status.state.waiting.reason}"
                    elif status:
                        try:
                            text = self.core_api.read_namespaced_pod_log(
                                pod.metadata.name,
                                namespace,
                                container=container.name,
                                timestamps=True,
                            )
                        except ApiException:
                            text = "日志尚未就绪，请稍后刷新。"
                    logs.append({
                        "step": container.name.removeprefix("step-"),
                        "container": container.name,
                        "logs": text,
                    })
            tasks.append({**task, "pod": pod.metadata.name if pod else None, "steps": logs})
        return {
            "pipeline_run": pipeline_run_name,
            "status": pipeline["status"],
            "reason": pipeline.get("reason"),
            "message": pipeline.get("message"),
            "started_at": pipeline.get("started_at"),
            "finished_at": pipeline.get("finished_at"),
            "tasks": tasks,
        }
