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
    def test_environment_directory_is_unique_and_sorted(self):
        project = SimpleNamespace(applications=[
            application(1, "api", [environment("prod", "Production", "api-prod")]),
            application(2, "worker", [
                environment("dev", "Development", "worker-dev"),
                environment("prod", "Production", "worker-prod"),
            ]),
        ])

        result = ProjectRuntimeService().environments(project)

        self.assertEqual([item["name"] for item in result], ["dev", "prod"])

    @patch("app.services.project_runtime_service.ApplicationRuntimeService.status")
    @patch("app.services.project_runtime_service.DeliveryContextService.resolve")
    def test_inventory_queries_only_requested_environment_and_paginates_after_filter(
        self, resolve, status
    ):
        dev = environment("dev", "Development", "api-dev")
        prod_a = environment("prod", "Production", "api-prod", "prod-cluster")
        prod_b = environment("prod", "Production", "worker-prod", "prod-cluster")
        apps = [application(1, "api", [dev, prod_a]), application(2, "worker", [prod_b])]
        project = SimpleNamespace(applications=apps)
        resolve.side_effect = lambda _project, app, _env: SimpleNamespace(
            application=app,
            environment=prod_a if app.name == "api" else prod_b,
            cluster=SimpleNamespace(id=9, name="prod-cluster"),
            namespace="api-prod" if app.name == "api" else "worker-prod",
        )
        status.side_effect = [
            {"status": "Healthy", "deployment": {"name": "api", "replicas": 2, "ready_replicas": 2, "updated_replicas": 2, "available_replicas": 2, "images": ["api:v1"]}, "pods": [{"name": "api-a", "ready": True, "restart_count": 0}]},
            {"status": "Degraded", "deployment": {"name": "worker", "replicas": 1, "ready_replicas": 0, "updated_replicas": 1, "available_replicas": 0, "images": ["worker:v1"]}, "pods": [{"name": "worker-a", "ready": False, "restart_count": 3}]},
        ]

        result = ProjectRuntimeService().inventory(
            project, "prod", "deployments", 1, 20, query="work", status="Degraded"
        )

        self.assertEqual(resolve.call_count, 2)
        self.assertEqual(result["environment"]["name"], "prod")
        self.assertEqual([item["application_name"] for item in result["items"]], ["worker"])
        self.assertEqual(result["pagination"], {"page": 1, "page_size": 20, "total": 1, "pages": 1})
        self.assertEqual(result["summary"]["unhealthy_pods"], 1)

    @patch("app.services.project_runtime_service.ApplicationRuntimeService.status")
    @patch("app.services.project_runtime_service.DeliveryContextService.resolve")
    def test_inventory_rejects_same_environment_across_different_clusters(
        self, resolve, _status
    ):
        prod = environment("prod", "Production", "prod")
        project = SimpleNamespace(applications=[application(1, "a", [prod]), application(2, "b", [prod])])
        resolve.side_effect = [
            SimpleNamespace(application=project.applications[0], environment=prod, cluster=SimpleNamespace(id=1, name="a")),
            SimpleNamespace(application=project.applications[1], environment=prod, cluster=SimpleNamespace(id=2, name="b")),
        ]

        with self.assertRaises(Exception) as caught:
            ProjectRuntimeService().inventory(project, "prod", "pods", 1, 20)

        self.assertEqual(caught.exception.code, "RUNTIME_ENVIRONMENT_CONFLICT")

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
