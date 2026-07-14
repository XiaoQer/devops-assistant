import os
import base64
from datetime import datetime, timezone

from kubernetes import client, config
from kubernetes.client import ApiClient


class KubernetesService:
    def __init__(self):
        self.mode = "incluster" if os.getenv("KUBERNETES_SERVICE_HOST") else "kubeconfig"
        if self.mode == "incluster":
            config.load_incluster_config()
        else:
            config.load_kube_config()
        self.api_client = client.ApiClient()
        self.core_api = client.CoreV1Api(self.api_client)
        self.apps_api = client.AppsV1Api(self.api_client)
        self.networking_api = client.NetworkingV1Api(self.api_client)
        self.custom_api = client.CustomObjectsApi(self.api_client)
        self.version_api = client.VersionApi(self.api_client)

    @classmethod
    def from_kubeconfig(cls, kubeconfig, context):
        instance = cls.__new__(cls)
        instance.mode = "cluster-kubeconfig"
        configuration = client.Configuration()
        config.load_kube_config_from_dict(
            kubeconfig,
            context=context,
            client_configuration=configuration,
            persist_config=False,
        )
        instance.api_client = client.ApiClient(configuration)
        instance.core_api = client.CoreV1Api(instance.api_client)
        instance.apps_api = client.AppsV1Api(instance.api_client)
        instance.networking_api = client.NetworkingV1Api(instance.api_client)
        instance.custom_api = client.CustomObjectsApi(instance.api_client)
        instance.version_api = client.VersionApi(instance.api_client)
        return instance

    @property
    def server(self):
        return self.api_client.configuration.host

    def health(self):
        self.core_api.get_api_resources()
        self.custom_api.list_cluster_custom_object(
            group="tekton.dev", version="v1", plural="pipelineruns", limit=1
        )
        return {
            "connected": True,
            "mode": self.mode,
            "server": self.server,
            "tektonInstalled": True,
        }

    def version(self):
        result = self.version_api.get_code(_request_timeout=5)
        return {"server": self.server, "version": result.git_version}

    def ensure_namespace(self, namespace):
        try:
            self.core_api.read_namespace(namespace)
        except client.ApiException as exc:
            if exc.status != 404:
                raise
            self.core_api.create_namespace(
                client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace))
            )

    def apply_config_map(self, name, namespace, data):
        body = client.V1ConfigMap(
            metadata=client.V1ObjectMeta(
                name=name,
                labels={"app.kubernetes.io/managed-by": "aegis"},
            ),
            data=data,
        )
        try:
            self.core_api.read_namespaced_config_map(name, namespace)
            self.core_api.patch_namespaced_config_map(
                name, namespace, {"data": data, "metadata": {"labels": body.metadata.labels}}
            )
        except client.ApiException as exc:
            if exc.status != 404:
                raise
            self.core_api.create_namespaced_config_map(namespace, body)
        return name

    def apply_secret(
        self, name, namespace, data, secret_type="Opaque", labels=None
    ):
        secret_labels = {
            "app.kubernetes.io/managed-by": "aegis",
            **(labels or {}),
        }
        body = client.V1Secret(
            metadata=client.V1ObjectMeta(
                name=name,
                labels=secret_labels,
            ),
            type=secret_type,
            string_data=data,
        )
        try:
            self.core_api.read_namespaced_secret(name, namespace)
            self.core_api.patch_namespaced_secret(
                name,
                namespace,
                {
                    "stringData": data,
                    "type": secret_type,
                    "metadata": {"labels": body.metadata.labels},
                },
            )
        except client.ApiException as exc:
            if exc.status != 404:
                raise
            self.core_api.create_namespaced_secret(namespace, body)
        return name

    def delete_secret(self, name, namespace):
        try:
            self.core_api.delete_namespaced_secret(name, namespace)
        except client.ApiException as exc:
            if exc.status != 404:
                raise

    def apply_registry_secret(
        self, name, namespace, server, username, password, email=""
    ):
        auth = base64.b64encode(f"{username}:{password}".encode()).decode()
        docker_config = {
            "auths": {
                server: {
                    "username": username,
                    "password": password,
                    "email": email,
                    "auth": auth,
                }
            }
        }
        import json
        return self.apply_secret(
            name,
            namespace,
            {".dockerconfigjson": json.dumps(docker_config)},
            "kubernetes.io/dockerconfigjson",
        )

    def get_application_status(self, app_name, namespace):
        try:
            deployment = self.apps_api.read_namespaced_deployment(app_name, namespace)
        except client.ApiException as exc:
            if exc.status != 404:
                raise
            return {
                "status": "Unknown",
                "deployment": {
                    "name": app_name,
                    "replicas": 0,
                    "ready_replicas": 0,
                    "updated_replicas": 0,
                    "available_replicas": 0,
                    "images": [],
                },
                "pods": [],
                "service": None,
                "ingress": None,
                "events": [],
                "message": f"Namespace {namespace} 中尚未找到 Deployment {app_name}",
            }
        desired = deployment.spec.replicas or 0
        ready = deployment.status.ready_replicas or 0
        updated = deployment.status.updated_replicas or 0
        available = deployment.status.available_replicas or 0

        pods = self.core_api.list_namespaced_pod(
            namespace, label_selector=f"app={app_name}"
        ).items
        if not pods:
            pods = self.core_api.list_namespaced_pod(
                namespace, label_selector=f"app.kubernetes.io/name={app_name}"
            ).items
        pod_items = []
        has_failed = False
        for pod in pods:
            statuses = pod.status.container_statuses or []
            restart_count = sum(item.restart_count for item in statuses)
            containers_ready = bool(statuses) and all(item.ready for item in statuses)
            waiting_reasons = [
                item.state.waiting.reason
                for item in statuses
                if item.state and item.state.waiting
            ]
            has_failed = has_failed or pod.status.phase == "Failed" or any(
                reason in {"CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"}
                for reason in waiting_reasons
            )
            pod_items.append({
                "name": pod.metadata.name,
                "status": waiting_reasons[0] if waiting_reasons else pod.status.phase,
                "ready": containers_ready,
                "restart_count": restart_count,
                "node": pod.spec.node_name,
            })

        if has_failed or (desired and available == 0 and pods):
            health = "Failed"
        elif ready == desired and updated == desired:
            health = "Healthy"
        elif ready > 0:
            health = "Progressing" if updated < desired else "Degraded"
        else:
            health = "Progressing"

        service_data = None
        try:
            service = self.core_api.read_namespaced_service(app_name, namespace)
            service_data = {
                "name": service.metadata.name,
                "type": service.spec.type,
                "cluster_ip": service.spec.cluster_ip,
                "ports": [port.port for port in (service.spec.ports or [])],
            }
        except client.ApiException as exc:
            if exc.status != 404:
                raise

        ingress_data = None
        try:
            ingress = self.networking_api.read_namespaced_ingress(app_name, namespace)
            rules = ingress.spec.rules or []
            addresses = ingress.status.load_balancer.ingress or []
            ingress_data = {
                "host": rules[0].host if rules else None,
                "address": (
                    addresses[0].ip or addresses[0].hostname if addresses else None
                ),
            }
        except client.ApiException as exc:
            if exc.status != 404:
                raise

        events = self.core_api.list_namespaced_event(
            namespace,
            field_selector=f"involvedObject.name={app_name}",
        ).items
        replica_sets = self.apps_api.list_namespaced_replica_set(
            namespace, label_selector=f"app={app_name}"
        ).items
        pvcs = self.core_api.list_namespaced_persistent_volume_claim(namespace).items
        config_maps = self.core_api.list_namespaced_config_map(namespace).items
        secrets = self.core_api.list_namespaced_secret(namespace).items
        return {
            "status": health,
            "deployment": {
                "name": deployment.metadata.name,
                "replicas": desired,
                "ready_replicas": ready,
                "updated_replicas": updated,
                "available_replicas": available,
                "images": [
                    container.image for container in deployment.spec.template.spec.containers
                ],
            },
            "pods": pod_items,
            "service": service_data,
            "ingress": ingress_data,
            "replica_sets": [{
                "name": item.metadata.name,
                "replicas": item.status.replicas or 0,
                "ready_replicas": item.status.ready_replicas or 0,
                "created_at": (
                    item.metadata.creation_timestamp.isoformat()
                    if item.metadata.creation_timestamp else None
                ),
            } for item in replica_sets],
            "persistent_volume_claims": [{
                "name": item.metadata.name,
                "status": item.status.phase,
                "storage_class": item.spec.storage_class_name,
                "capacity": (
                    item.status.capacity.get("storage")
                    if item.status.capacity else None
                ),
            } for item in pvcs],
            "config_maps": [
                {"name": item.metadata.name, "keys": sorted((item.data or {}).keys())}
                for item in config_maps
            ],
            "secrets": [
                {"name": item.metadata.name, "type": item.type}
                for item in secrets
                if not item.metadata.name.startswith("default-token-")
            ],
            "events": [{
                "type": event.type,
                "reason": event.reason,
                "message": event.message,
                "count": event.count,
                "timestamp": (
                    event.last_timestamp.isoformat() if event.last_timestamp else None
                ),
            } for event in events[-20:]],
        }

    def get_pod_logs(self, pod_name, namespace, container=None, tail_lines=500):
        return self.core_api.read_namespaced_pod_log(
            pod_name,
            namespace,
            container=container,
            tail_lines=min(max(tail_lines, 1), 5000),
            timestamps=True,
        )

    def get_pod_manifest(self, pod_name, namespace):
        pod = self.core_api.read_namespaced_pod(pod_name, namespace)
        data = ApiClient().sanitize_for_serialization(pod)
        data.get("metadata", {}).pop("managedFields", None)
        return data

    def rollback_deployment(self, deployment_name, namespace, image):
        deployment = self.apps_api.read_namespaced_deployment(
            deployment_name, namespace
        )
        containers = deployment.spec.template.spec.containers
        if not containers:
            raise ValueError("Deployment 没有可更新的容器")
        target = next(
            (item for item in containers if item.name == deployment_name),
            containers[0],
        )
        body = {
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {
                            "devops.ai/rollback-at": datetime.now(timezone.utc).isoformat()
                        }
                    },
                    "spec": {
                        "containers": [{"name": target.name, "image": image}]
                    },
                }
            }
        }
        self.apps_api.patch_namespaced_deployment(
            deployment_name, namespace, body
        )
        return {"deployment": deployment_name, "namespace": namespace, "image": image}
