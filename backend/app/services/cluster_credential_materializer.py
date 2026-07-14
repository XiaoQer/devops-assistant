from flask import current_app

from .kubernetes_cluster_service import KubernetesClusterService


class ClusterCredentialMaterializer:
    @staticmethod
    def secret_name(project_id, cluster_id):
        return f"aegis-kubeconfig-p{project_id}-c{cluster_id}"

    def materialize(self, project, cluster, central_kubernetes):
        kubeconfig, _context = KubernetesClusterService().credentials(cluster)
        name = self.secret_name(project.id, cluster.id)
        namespace = current_app.config["TEKTON_NAMESPACE"]
        central_kubernetes.ensure_namespace(namespace)
        central_kubernetes.apply_secret(
            name,
            namespace,
            {"config": kubeconfig},
            labels={
                "app.kubernetes.io/managed-by": "aegis",
                "aegis.dev/project-id": str(project.id),
                "aegis.dev/cluster-id": str(cluster.id),
            },
        )
        return name

    def delete(self, project, cluster, central_kubernetes):
        central_kubernetes.delete_secret(
            self.secret_name(project.id, cluster.id),
            current_app.config["TEKTON_NAMESPACE"],
        )
