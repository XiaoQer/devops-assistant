from .kubernetes_cluster_service import KubernetesClusterService


class ApplicationRuntimeService:
    def _client(self, context):
        return KubernetesClusterService().client(context.cluster)

    def status(self, context):
        return self._client(context).get_application_status(
            context.application.name,
            context.environment.namespace,
        )

    def pod_logs(self, context, pod_name, container=None, tail_lines=500):
        return self._client(context).get_application_pod_logs(
            pod_name,
            context.environment.namespace,
            context.application.name,
            container,
            tail_lines,
        )

    def pod_manifest(self, context, pod_name):
        return self._client(context).get_application_pod_manifest(
            pod_name,
            context.environment.namespace,
            context.application.name,
        )

    def rollback(self, context, image):
        return self._client(context).rollback_deployment(
            context.application.name,
            context.environment.namespace,
            image,
        )
