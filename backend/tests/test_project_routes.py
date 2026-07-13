import unittest
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models import Application, ContainerRegistry, KubernetesCluster, Project, User

from auth_helpers import create_user, csrf_post, login


VALID_KUBECONFIG = """
apiVersion: v1
kind: Config
current-context: dev
clusters:
  - name: dev-cluster
    cluster:
      server: https://kubernetes.example.test
      certificate-authority-data: dGVzdA==
users:
  - name: dev-user
    user:
      token: route-test-token
contexts:
  - name: dev
    context:
      cluster: dev-cluster
      user: dev-user
"""


class TestConfig:
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False
    TEKTON_NAMESPACE = "tekton"
    DEFAULT_IMAGE_REGISTRY = "registry.local"
    AUTO_CREATE_SCHEMA = True
    SECRET_KEY = "project-routes-test-secret"
    TESTING = True
    AUTH_SESSION_HOURS = 8
    AUTH_COOKIE_NAME = "test_session"
    AUTH_CSRF_COOKIE_NAME = "test_csrf"
    AUTH_COOKIE_SECURE = False


class ProjectRoutesTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.context = self.app.app_context()
        self.context.push()
        self.client = self.app.test_client()
        create_user(db, User)
        _response, auth = login(self.client)
        self.csrf_token = auth["csrf_token"]
        project = Project(key="payments", name="Payments")
        other = Project(key="platform", name="Platform")
        db.session.add_all([project, other])
        db.session.commit()
        self.project_id = project.id
        self.other_project_id = other.id

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    def test_create_project_with_owner(self):
        response = csrf_post(
            self.client,
            "/api/projects",
            self.csrf_token,
            json={
                "key": "orders",
                "name": "Orders",
                "owner_name": "Alice",
                "owner_email": "alice@example.com",
            },
        )

        self.assertEqual(response.status_code, 201)
        body = response.get_json()["data"]
        self.assertEqual(body["key"], "orders")

        members = self.client.get(f"/api/projects/{body['id']}/members").get_json()["data"]
        self.assertEqual(len(members), 1)
        self.assertEqual(members[0]["role"], "owner")

    def test_list_projects_hides_system_default_project(self):
        default_project = Project(key="default", name="Default Project")
        db.session.add(default_project)
        db.session.commit()

        response = self.client.get("/api/projects")

        self.assertEqual(response.status_code, 200)
        keys = [item["key"] for item in response.get_json()["data"]]
        self.assertNotIn("default", keys)
        self.assertIn("payments", keys)
        self.assertIn("platform", keys)

        detail = self.client.get(f"/api/projects/{default_project.id}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.get_json()["data"]["key"], "default")

    def test_create_project_with_minimal_payload_sets_governance_defaults(self):
        response = csrf_post(
            self.client,
            "/api/projects",
            self.csrf_token,
            json={
                "key": "orders",
                "name": "Orders",
            },
        )

        self.assertEqual(response.status_code, 201)
        body = response.get_json()["data"]
        self.assertEqual(body["status"], "active")
        self.assertEqual(body["github_default_visibility"], "private")
        self.assertEqual(body["aliyun_region"], "cn-hangzhou")
        self.assertEqual(body["aliyun_binding_status"], "unbound")

        detail = self.client.get(f"/api/projects/{body['id']}").get_json()["data"]
        self.assertEqual(detail["status"], "active")
        self.assertEqual(detail["github_default_visibility"], "private")
        self.assertEqual(detail["aliyun_region"], "cn-hangzhou")
        self.assertEqual(detail["aliyun_binding_status"], "unbound")

    def test_create_project_with_governance_metadata(self):
        response = csrf_post(
            self.client,
            "/api/projects",
            self.csrf_token,
            json={
                "key": "orders",
                "name": "Orders",
                "description": "Order domain delivery boundary",
                "status": "active",
                "business_owner": "Order Platform Team",
                "billing_owner": "FinOps",
                "github_group": "acme/orders",
                "github_default_visibility": "private",
                "aliyun_account_id": "1234567890123456",
                "aliyun_resource_group_id": "rg-acfm2pz25js****",
                "aliyun_region": "cn-hangzhou",
                "aliyun_vpc_id": "vpc-bp1example",
                "aliyun_binding_status": "linked",
            },
        )

        self.assertEqual(response.status_code, 201)
        body = response.get_json()["data"]
        self.assertEqual(body["status"], "active")
        self.assertEqual(body["business_owner"], "Order Platform Team")
        self.assertEqual(body["billing_owner"], "FinOps")
        self.assertEqual(body["github_group"], "acme/orders")
        self.assertEqual(body["github_default_visibility"], "private")
        self.assertEqual(body["aliyun_account_id"], "1234567890123456")
        self.assertEqual(body["aliyun_resource_group_id"], "rg-acfm2pz25js****")
        self.assertEqual(body["aliyun_region"], "cn-hangzhou")
        self.assertEqual(body["aliyun_vpc_id"], "vpc-bp1example")
        self.assertEqual(body["aliyun_binding_status"], "linked")

        detail = self.client.get(f"/api/projects/{body['id']}").get_json()["data"]
        self.assertEqual(detail["github_group"], "acme/orders")
        self.assertEqual(detail["aliyun_region"], "cn-hangzhou")

    def test_update_project_governance_metadata(self):
        response = self.client.patch(
            f"/api/projects/{self.project_id}",
            headers={"X-CSRF-Token": self.csrf_token},
            json={
                "name": "Payments Core",
                "status": "archived",
                "business_owner": "Payments Platform",
                "billing_owner": "Finance Ops",
                "github_group": "acme/payments-core",
                "github_default_visibility": "internal",
                "aliyun_account_id": "9988776655443322",
                "aliyun_resource_group_id": "rg-payments-core",
                "aliyun_region": "cn-shanghai",
                "aliyun_vpc_id": "vpc-payments-core",
                "aliyun_binding_status": "pending",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()["data"]
        self.assertEqual(body["name"], "Payments Core")
        self.assertEqual(body["status"], "archived")
        self.assertEqual(body["github_default_visibility"], "internal")
        self.assertEqual(body["aliyun_binding_status"], "pending")

        list_response = self.client.get("/api/projects")
        items = list_response.get_json()["data"]
        updated = next(item for item in items if item["id"] == self.project_id)
        self.assertEqual(updated["github_group"], "acme/payments-core")
        self.assertEqual(updated["aliyun_resource_group_id"], "rg-payments-core")

    def test_project_rejects_invalid_metadata(self):
        response = csrf_post(
            self.client,
            "/api/projects",
            self.csrf_token,
            json={
                "key": "orders",
                "name": "Orders",
                "status": "provisioning",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "PROJECT_INVALID_STATUS")

        update_response = self.client.patch(
            f"/api/projects/{self.project_id}",
            headers={"X-CSRF-Token": self.csrf_token},
            json={"aliyun_binding_status": "ready"},
        )

        self.assertEqual(update_response.status_code, 400)
        self.assertEqual(
            update_response.get_json()["error"]["code"],
            "PROJECT_INVALID_ALIYUN_BINDING_STATUS",
        )

    def test_project_rejects_sensitive_metadata_fields(self):
        response = csrf_post(
            self.client,
            "/api/projects",
            self.csrf_token,
            json={
                "key": "orders",
                "name": "Orders",
                "aliyun_access_key_secret": "never-store-me",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"]["code"], "PROJECT_SENSITIVE_FIELD")

    def test_member_and_cluster_routes(self):
        member_response = csrf_post(
            self.client,
            f"/api/projects/{self.project_id}/members",
            self.csrf_token,
            json={
                "name": "Bob",
                "email": "bob@example.com",
                "role": "admin",
            },
        )
        cluster_response = csrf_post(
            self.client,
            f"/api/projects/{self.project_id}/clusters",
            self.csrf_token,
            json={
                "name": "prod-cn-1",
                "kube_context": "gke-prod-cn-1",
                "environment_label": "production",
                "kubeconfig": VALID_KUBECONFIG.replace(
                    "current-context: dev", "current-context: gke-prod-cn-1"
                ).replace("name: dev\n", "name: gke-prod-cn-1\n"),
                "namespace_prefix": "payments",
            },
        )

        self.assertEqual(member_response.status_code, 201)
        self.assertEqual(cluster_response.status_code, 201)
        self.assertEqual(member_response.get_json()["data"]["role"], "admin")
        self.assertEqual(cluster_response.get_json()["data"]["name"], "prod-cn-1")

    @patch("app.routes.projects.cluster_service.test_connection")
    def test_transient_cluster_connection_uses_standard_envelope_without_persisting(self, test_connection):
        test_connection.return_value = {
            "connected": True,
            "message": "Kubernetes API 连接成功",
            "api_server": "https://kubernetes.example.test",
            "kubernetes_version": "v1.31.2",
        }

        response = csrf_post(
            self.client,
            f"/api/projects/{self.project_id}/clusters/test-connection",
            self.csrf_token,
            json={"kubeconfig": VALID_KUBECONFIG, "kube_context": "dev"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(
            set(body),
            {"success", "message", "data", "timestamp", "trace_id"},
        )
        self.assertTrue(body["data"]["connected"])
        self.assertEqual(KubernetesCluster.query.count(), 0)
        test_connection.assert_called_once_with(VALID_KUBECONFIG, "dev")

    @patch("app.routes.projects.cluster_service.test_saved_connection")
    def test_saved_cluster_connection_is_project_scoped(self, test_saved_connection):
        create_response = csrf_post(
            self.client,
            f"/api/projects/{self.project_id}/clusters",
            self.csrf_token,
            json={
                "name": "payments-dev",
                "environment_label": "development",
                "kubeconfig": VALID_KUBECONFIG,
                "kube_context": "dev",
            },
        )
        cluster_id = create_response.get_json()["data"]["id"]
        test_saved_connection.return_value = {
            "connected": False,
            "message": "Kubernetes 网络不可达",
        }

        response = csrf_post(
            self.client,
            f"/api/projects/{self.project_id}/clusters/{cluster_id}/test-connection",
            self.csrf_token,
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.get_json()["data"]["connected"])

        cross_project = csrf_post(
            self.client,
            f"/api/projects/{self.other_project_id}/clusters/{cluster_id}/test-connection",
            self.csrf_token,
        )
        self.assertEqual(cross_project.status_code, 404)
        self.assertEqual(cross_project.get_json()["error"]["code"], "CLUSTER_NOT_FOUND")
        test_saved_connection.assert_called_once()

    def test_registry_list_is_project_scoped(self):
        db.session.add_all([
            ContainerRegistry(
                project_id=self.project_id,
                name="Payments Harbor",
                provider="harbor",
                server="harbor.payments.local",
            ),
            ContainerRegistry(
                project_id=self.other_project_id,
                name="Platform ACR",
                provider="acr",
                server="platform.azurecr.io",
            ),
        ])
        db.session.commit()

        response = self.client.get("/api/registries", query_string={"projectId": self.project_id})

        self.assertEqual(response.status_code, 200)
        items = response.get_json()["data"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["project_id"], self.project_id)

    def test_applications_list_is_project_scoped(self):
        db.session.add_all([
            Application(
                project_id=self.project_id,
                name="payment-service-a",
                repo_url="https://github.com/example/payment-service-a.git",
                branch="main",
                language="java",
                framework="spring-boot",
                build_type="maven",
                namespace="default",
                image_name="registry.local/payment-service-a",
                image_tag="latest",
                port=8080,
                status="Running",
            ),
            Application(
                project_id=self.other_project_id,
                name="platform-service-b",
                repo_url="https://github.com/example/platform-service-b.git",
                branch="main",
                language="java",
                framework="spring-boot",
                build_type="maven",
                namespace="default",
                image_name="registry.local/platform-service-b",
                image_tag="latest",
                port=8080,
                status="Running",
            ),
        ])
        db.session.commit()

        response = self.client.get("/api/applications", query_string={"projectId": self.project_id})

        self.assertEqual(response.status_code, 200)
        items = response.get_json()["data"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["project_id"], self.project_id)


if __name__ == "__main__":
    unittest.main()
