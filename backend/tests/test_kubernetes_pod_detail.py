import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

from app.services.kubernetes_service import KubernetesService


def ns(**values):
    return SimpleNamespace(**values)


class KubernetesPodDetailTest(unittest.TestCase):
    def test_returns_standardized_runtime_detail_without_environment_values(self):
        now = datetime(2026, 7, 15, tzinfo=timezone.utc)
        running = ns(started_at=now)
        status = ns(
            name="api", image="registry.test/api:v2", ready=True, restart_count=2,
            state=ns(running=running, waiting=None, terminated=None),
        )
        pod = ns(
            metadata=ns(name="payments-api-a", labels={"app": "payments-api"}, creation_timestamp=now),
            spec=ns(node_name="worker-1", containers=[ns(name="api", image="registry.test/api:v2", env=[ns(name="SECRET", value="hidden")])]),
            status=ns(
                phase="Running", pod_ip="10.0.0.8", host_ip="10.0.0.2", qos_class="Burstable",
                start_time=now, container_statuses=[status],
                conditions=[ns(type="Ready", status="True", reason=None, message=None, last_transition_time=now)],
            ),
        )
        event = ns(type="Normal", reason="Started", message="Started container", count=1, last_timestamp=now, event_time=None, first_timestamp=None)
        service = KubernetesService.__new__(KubernetesService)
        service.core_api = Mock()
        service.core_api.read_namespaced_pod.return_value = pod
        service.core_api.list_namespaced_event.return_value = ns(items=[event])

        result = service.get_application_pod_detail("payments-api-a", "payments-prod", "payments-api")

        self.assertEqual(result["node"], "worker-1")
        self.assertEqual(result["containers"][0]["state"], "running")
        self.assertEqual(result["containers"][0]["started_at"], now.isoformat())
        self.assertNotIn("env", result["containers"][0])
        self.assertEqual(result["conditions"][0]["type"], "Ready")
        self.assertEqual(result["events"][0]["reason"], "Started")
        service.core_api.list_namespaced_event.assert_called_once_with(
            "payments-prod", field_selector="involvedObject.name=payments-api-a"
        )


if __name__ == "__main__":
    unittest.main()
