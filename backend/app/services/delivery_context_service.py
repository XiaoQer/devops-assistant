from dataclasses import dataclass

from app.models import (
    Application,
    ApplicationEnvironment,
    ContainerRegistry,
    KubernetesCluster,
    Project,
)
from app.utils.errors import ApiError


@dataclass(frozen=True)
class DeliveryContext:
    project: Project
    application: Application
    environment: ApplicationEnvironment
    cluster: KubernetesCluster
    registry: ContainerRegistry
    namespace: str
    image_name: str
    kube_context: str


class DeliveryContextService:
    def resolve(self, project, application, environment_name):
        if application.project_id != project.id:
            raise ApiError("应用不存在", 404, "APPLICATION_NOT_FOUND")

        environment = ApplicationEnvironment.query.filter_by(
            application_id=application.id,
            environment_name=environment_name,
        ).first()
        if not environment:
            raise ApiError("目标环境不存在", 404, "ENVIRONMENT_NOT_FOUND")
        if not environment.kubernetes_cluster_id:
            raise ApiError(
                "目标环境尚未绑定 Kubernetes 集群",
                409,
                "CLUSTER_REQUIRED",
            )

        cluster = KubernetesCluster.query.filter_by(
            id=environment.kubernetes_cluster_id,
            project_id=project.id,
        ).first()
        if (
            not cluster
            or not cluster.is_active
            or cluster.connection_status != "connected"
            or not cluster.encrypted_kubeconfig
        ):
            raise ApiError(
                "目标 Kubernetes 集群尚未就绪",
                409,
                "CLUSTER_NOT_READY",
            )

        registry = ContainerRegistry.query.filter_by(
            project_id=project.id,
            is_default=True,
        ).first()
        if not registry:
            raise ApiError(
                "Project 尚未配置默认 Registry",
                409,
                "REGISTRY_REQUIRED",
            )
        if (
            not registry.is_active
            or registry.connection_status != "connected"
            or not registry.encrypted_password
        ):
            raise ApiError(
                "Project 默认 Registry 尚未就绪",
                409,
                "REGISTRY_NOT_READY",
            )

        return DeliveryContext(
            project=project,
            application=application,
            environment=environment,
            cluster=cluster,
            registry=registry,
            namespace=environment.namespace,
            image_name=f"{registry.image_prefix}/{application.name}",
            kube_context=cluster.kube_context,
        )
