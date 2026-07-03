import unittest

from app import create_app
from app.extensions import db
from app.models import Application, ContainerRegistry, Project, User

from auth_helpers import create_user, csrf_post, login


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
                "namespace_prefix": "payments",
            },
        )

        self.assertEqual(member_response.status_code, 201)
        self.assertEqual(cluster_response.status_code, 201)
        self.assertEqual(member_response.get_json()["data"]["role"], "admin")
        self.assertEqual(cluster_response.get_json()["data"]["name"], "prod-cn-1")

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
