from pathlib import Path

import pytest
import yaml

from app.services.tekton_service import TektonService


class CustomApi:
    def create_namespaced_custom_object(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        return {"metadata": {"name": "demo-run-abc"}}

    def get_namespaced_custom_object(self, *args):
        return self.run

    def list_namespaced_custom_object(self, *args, **kwargs):
        self.list_args = args
        self.list_kwargs = kwargs
        return getattr(self, "list_result", {"items": []})


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
        kubeconfig_secret_name="aegis-kubeconfig-p1-c2",
        kube_context="prod",
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
    assert params["kubeconfig_secret_name"] == "aegis-kubeconfig-p1-c2"
    assert params["kube_context"] == "prod"
    assert "test-token" not in str(body).lower()


@pytest.mark.parametrize(
    "filename",
    [
        "java-maven-kaniko-deploy.yaml",
        "node-npm-kaniko-deploy.yaml",
        "dockerfile-kaniko-deploy.yaml",
    ],
)
def test_only_deploy_task_mounts_target_kubeconfig(filename):
    path = Path(__file__).parents[2] / "deploy" / "tekton" / "pipelines" / filename
    pipeline = yaml.safe_load(path.read_text())
    pipeline_params = {item["name"] for item in pipeline["spec"]["params"]}
    assert {"kubeconfig_secret_name", "kube_context"} <= pipeline_params

    tasks = {item["name"]: item for item in pipeline["spec"]["tasks"]}
    deploy = tasks["deploy"]
    volumes = deploy["taskSpec"]["volumes"]
    assert volumes == [
        {
            "name": "target-kubeconfig",
            "secret": {"secretName": "$(params.kubeconfig_secret_name)"},
        }
    ]
    deploy_step = deploy["taskSpec"]["steps"][0]
    assert deploy_step["volumeMounts"] == [
        {
            "name": "target-kubeconfig",
            "mountPath": "/var/run/aegis/kubeconfig",
            "readOnly": True,
        }
    ]
    assert (
        'kubectl --kubeconfig=/var/run/aegis/kubeconfig/config '
        '--context="$(params.kube_context)" -n "$(params.namespace)"'
        in deploy_step["script"]
    )

    deploy_params = {item["name"]: item["value"] for item in deploy["params"]}
    assert deploy_params["kubeconfig_secret_name"] == "$(params.kubeconfig_secret_name)"
    assert deploy_params["kube_context"] == "$(params.kube_context)"

    for name, task in tasks.items():
        if name == "deploy":
            continue
        assert "target-kubeconfig" not in str(task)


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


def test_deploy_pipeline_run_carries_release_target_label_and_can_be_recovered():
    kubernetes = Kubernetes()
    service = TektonService(kubernetes)

    service.create_deploy_pipeline_run(
        "java-maven-deploy-only",
        "demo",
        "registry.local/demo",
        "build-123",
        "devops-platform",
        "demo-dev",
        8080,
        labels={"aegis.dev/release-target-id": "42"},
    )
    body = kubernetes.custom_api.args[-1]
    assert body["metadata"]["labels"]["aegis.dev/release-target-id"] == "42"
    assert kubernetes.custom_api.kwargs["_request_timeout"] == 30

    kubernetes.custom_api.list_result = {
        "items": [{"metadata": {"name": "demo-deploy-existing"}}]
    }
    found = service.find_pipeline_run_by_label(
        "devops-platform", "aegis.dev/release-target-id", "42"
    )
    assert found == "demo-deploy-existing"
    assert kubernetes.custom_api.list_kwargs["label_selector"] == (
        "aegis.dev/release-target-id=42"
    )


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
