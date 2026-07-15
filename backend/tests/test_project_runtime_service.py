import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.services.project_runtime_service import ProjectRuntimeService


def environment(name, display_name, namespace, cluster_name="cluster-a"):
    return SimpleNamespace(
        environment_name=name,
        display_name=display_name,
        namespace=namespace,
        cluster_name=cluster_name,
    )


def application(app_id, name, environments):
    return SimpleNamespace(id=app_id, name=name, environments=environments)


class ProjectRuntimeServiceTest(unittest.TestCase):
    @patch("app.services.project_runtime_service.ApplicationRuntimeService.status")
    @patch("app.services.project_runtime_service.DeliveryContextService.resolve")
    def test_groups_applications_by_environment_and_calculates_summary(
        self, resolve, status
    ):
        dev = environment("dev", "Development", "payments-dev")
        prod = environment("prod", "Production", "payments-prod", "cluster-prod")
        project = SimpleNamespace(
            applications=[
                application(2, "worker", [prod]),
                application(1, "api", [dev]),
            ]
        )
        resolve.side_effect = lambda _project, app, env: SimpleNamespace(
            application=app,
            environment=dev if env == "dev" else prod,
            cluster=SimpleNamespace(name=("cluster-a" if env == "dev" else "cluster-prod")),
        )
        status.side_effect = [
            {
                "status": "Healthy",
                "deployment": {"name": "api", "replicas": 1, "ready_replicas": 1},
                "pods": [{"name": "api-1", "ready": True, "restart_count": 1}],
            },
            {
                "status": "Degraded",
                "deployment": {"name": "worker", "replicas": 2, "ready_replicas": 1},
                "pods": [
                    {"name": "worker-1", "ready": True, "restart_count": 2},
                    {"name": "worker-2", "ready": False, "restart_count": 3},
                ],
            },
        ]

        result = ProjectRuntimeService().overview(project)

        self.assertEqual([item["name"] for item in result["environments"]], ["dev", "prod"])
        self.assertEqual(
            result["summary"],
            {
                "environments": 2,
                "deployments": 2,
                "healthy_pods": 2,
                "unhealthy_pods": 1,
                "restart_count": 6,
            },
        )
        self.assertEqual(
            result["environments"][0]["applications"][0]["application_name"],
            "api",
        )
        self.assertIn("refreshed_at", result)

    @patch("app.services.project_runtime_service.ApplicationRuntimeService.status")
    @patch("app.services.project_runtime_service.DeliveryContextService.resolve")
    def test_returns_sanitized_partial_error_without_hiding_healthy_targets(
        self, resolve, status
    ):
        dev = environment("dev", "Development", "api-dev")
        prod = environment("prod", "Production", "api-prod")
        app = application(1, "api", [dev, prod])
        project = SimpleNamespace(applications=[app])
        resolve.side_effect = lambda _project, _app, env: SimpleNamespace(
            application=app,
            environment=dev if env == "dev" else prod,
            cluster=SimpleNamespace(name="cluster-a"),
        )
        status.side_effect = [
            {"status": "Healthy", "deployment": {"name": "api"}, "pods": []},
            RuntimeError("token=super-secret cluster rejected request"),
        ]

        result = ProjectRuntimeService().overview(project)

        self.assertEqual(result["summary"]["deployments"], 1)
        failed = result["environments"][1]["applications"][0]
        self.assertEqual(failed["error"]["code"], "RUNTIME_TARGET_UNAVAILABLE")
        self.assertNotIn("super-secret", failed["error"]["message"])
        self.assertEqual(result["environments"][0]["applications"][0]["status"], "Healthy")


if __name__ == "__main__":
    unittest.main()
