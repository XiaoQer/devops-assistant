from app.services.tekton_service import TektonService


class CustomApi:
    def create_namespaced_custom_object(self, *args):
        self.args = args
        return {"metadata": {"name": "demo-run-abc"}}

    def get_namespaced_custom_object(self, *args):
        return self.run


class Kubernetes:
    def __init__(self):
        self.custom_api = CustomApi()
        self.core_api = object()


def test_pipeline_run_contains_source_workspace_and_target_namespace():
    kubernetes = Kubernetes()
    name = TektonService(kubernetes).create_pipeline_run(
        "node-npm-kaniko-deploy",
        "demo",
        "https://github.com/acme/demo.git",
        "main",
        "registry.local/demo",
        "latest",
        "devops-platform",
        3000,
        deploy_namespace="staging",
    )
    body = kubernetes.custom_api.args[-1]
    assert name == "demo-run-abc"
    assert body["metadata"]["namespace"] == "devops-platform"
    assert body["spec"]["workspaces"][0]["name"] == "source"
    secret = body["spec"]["taskRunTemplate"]["podTemplate"]["volumes"][0]["secret"]
    assert secret["items"] == [
        {"key": ".dockerconfigjson", "path": "config.json"}
    ]
    params = {param["name"]: param["value"] for param in body["spec"]["params"]}
    assert params["namespace"] == "staging"


def test_configured_registry_secret_is_required():
    kubernetes = Kubernetes()
    TektonService(kubernetes).create_pipeline_run(
        "java-maven-kaniko-deploy",
        "demo",
        "https://github.com/acme/demo.git",
        "main",
        "registry.example.com/team/demo",
        "latest",
        "devops-platform",
        8080,
        deployment_config={"registry_secret_name": "aegis-registry-credentials"},
    )
    body = kubernetes.custom_api.args[-1]
    secret = body["spec"]["taskRunTemplate"]["podTemplate"]["volumes"][0]["secret"]
    assert secret["secretName"] == "aegis-registry-credentials"
    assert secret["optional"] is False


def test_retry_pipeline_run_reuses_existing_spec_with_retry_label():
    kubernetes = Kubernetes()
    kubernetes.custom_api.run = {
        "apiVersion": "tekton.dev/v1",
        "kind": "PipelineRun",
        "metadata": {
            "name": "demo-run-failed",
            "generateName": "demo-run-",
            "labels": {"app.kubernetes.io/name": "demo"},
            "annotations": {"example": "1"},
        },
        "spec": {
            "pipelineRef": {"name": "java-maven-kaniko-deploy"},
            "params": [{"name": "app_name", "value": "demo"}],
        },
        "status": {"conditions": [{"status": "False", "reason": "Failed"}]},
    }

    retried = TektonService(kubernetes).retry_pipeline_run("demo-run-failed", "devops-platform")
    body = kubernetes.custom_api.args[-1]

    assert retried["name"] == "demo-run-abc"
    assert retried["retried_from"] == "demo-run-failed"
    assert body["metadata"]["generateName"] == "demo-run-"
    assert body["metadata"]["labels"]["aegis.dev/retry-of"] == "demo-run-failed"
    assert body["spec"]["pipelineRef"]["name"] == "java-maven-kaniko-deploy"


def test_retry_pipeline_run_rejects_non_failed_runs():
    kubernetes = Kubernetes()
    kubernetes.custom_api.run = {
        "metadata": {"name": "demo-run-success", "labels": {"app.kubernetes.io/name": "demo"}},
        "spec": {"pipelineRef": {"name": "java-maven-kaniko-deploy"}},
        "status": {"conditions": [{"status": "True", "reason": "Succeeded"}]},
    }

    try:
        TektonService(kubernetes).retry_pipeline_run("demo-run-success", "devops-platform")
        raise AssertionError("expected retry to be rejected for succeeded runs")
    except ValueError as exc:
        assert str(exc) == "只有失败或取消的 PipelineRun 才能重试"

