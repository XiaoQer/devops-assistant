from flask import current_app

from app.extensions import db
from app.models import Application, PipelineExecution, ApplicationEnvironment
from app.utils.errors import ApiError
from .repo_analyzer_service import RepoAnalyzerService
from .tekton_service import TektonService
from .release_service import ReleaseService
from .configuration_service import ConfigurationService
from .kubernetes_service import KubernetesService
from .environment_service import EnvironmentService
from .registry_service import RegistryService


class ApplicationService:
    PIPELINES = {
        ("java", "maven"): "java-maven-kaniko-deploy",
        ("nodejs", "npm"): "node-npm-kaniko-deploy",
        ("dockerfile", "dockerfile"): "dockerfile-kaniko-deploy",
    }

    def get(self, project_id, application_id):
        app = Application.query.filter_by(
            id=application_id,
            project_id=project_id,
        ).first()
        if not app:
            raise ApiError("应用不存在", 404, "APPLICATION_NOT_FOUND")
        return app

    def create(self, project, payload):
        required = ("name", "repo_url")
        missing = [key for key in required if not payload.get(key)]
        if missing:
            raise ApiError(f"缺少必填字段: {', '.join(missing)}")
        existing = Application.query.filter_by(
            project_id=project.id,
            name=payload["name"],
        ).first()
        if existing:
            raise ApiError("应用名称已存在", 409, "APPLICATION_EXISTS")
        analysis = RepoAnalyzerService().analyze(
            payload["repo_url"], payload.get("branch", "main")
        )
        registry = RegistryService().get_default(project.id)
        image_name = payload.get("image_name") or (
            f"{registry.image_prefix}/{payload['name']}"
            if registry else f"{current_app.config['DEFAULT_IMAGE_REGISTRY']}/{payload['name']}"
        )
        app = Application(
            project_id=project.id,
            name=payload["name"],
            repo_url=payload["repo_url"],
            branch=payload.get("branch", "main"),
            namespace=payload.get("namespace", "default"),
            image_name=image_name,
            image_tag=payload.get("image_tag", "latest"),
            status="analyzed",
            **analysis,
        )
        app.application_spec = self._spec(app)
        db.session.add(app)
        db.session.commit()
        EnvironmentService().list(app, ensure_defaults=True)
        return app

    def deploy(self, app, payload=None, deploy_user="local-user"):
        payload = payload or {}
        environment_name = payload.get("environment", "dev")
        environment = ApplicationEnvironment.query.filter_by(
            application_id=app.id, environment_name=environment_name
        ).first()
        if not environment:
            EnvironmentService().list(app, ensure_defaults=True)
            environment = ApplicationEnvironment.query.filter_by(
                application_id=app.id, environment_name=environment_name
            ).first()
        if environment:
            payload.setdefault("namespace", environment.namespace)
        pipeline = self.PIPELINES.get((app.language, app.build_type))
        if not pipeline:
            raise ApiError(
                f"暂不支持 {app.language}/{app.build_type} 项目",
                422,
                "UNSUPPORTED_BUILD_TYPE",
            )
        tekton_namespace = current_app.config["TEKTON_NAMESPACE"]
        image_tag = payload.get("image_tag", app.image_tag)
        deploy_namespace = payload.get("namespace", app.namespace)
        image_name = payload.get("image_name", app.image_name)
        registry = RegistryService().get_default(app.project_id)
        deployment_config = {
            "replicas": 1,
            "cpu_request": "100m",
            "cpu_limit": "500m",
            "memory_request": "128Mi",
            "memory_limit": "512Mi",
            "deploy_strategy": "RollingUpdate",
            "max_unavailable": "25%",
            "max_surge": "25%",
            "ingress_host": "",
            "config_map_name": f"{app.name}-config",
            "secret_name": f"{app.name}-secret",
            "registry_secret_name": "",
        }
        if environment:
            if registry:
                image_name = f"{registry.image_prefix}/{app.name}"
            elif environment.image_registry:
                # Backward compatibility for installations created before global registries.
                image_name = f"{environment.image_registry.rstrip('/')}/{app.name}"
            resources = ConfigurationService().materialize(
                app, environment, KubernetesService(), registry=registry
            )
            deployment_config.update({
                "replicas": environment.replicas,
                "cpu_request": environment.cpu_request,
                "cpu_limit": environment.cpu_limit,
                "memory_request": environment.memory_request,
                "memory_limit": environment.memory_limit,
                "deploy_strategy": environment.deploy_strategy,
                "max_unavailable": environment.max_unavailable,
                "max_surge": environment.max_surge,
                "ingress_host": environment.ingress_domain or "",
                **{key: value or "" for key, value in resources.items()},
            })
        payload["image_name"] = image_name
        run_name = TektonService().create_pipeline_run(
            pipeline, app.name, app.repo_url, app.branch, image_name,
            image_tag, tekton_namespace, app.port,
            deploy_namespace=deploy_namespace,
            deployment_config=deployment_config,
        )
        execution = PipelineExecution(
            application_id=app.id,
            project_id=app.project_id,
            environment=environment_name,
            kubernetes_cluster_id=(
                environment.kubernetes_cluster_id if environment else None
            ),
            deploy_namespace=deploy_namespace,
            pipeline_run_name=run_name,
            image_url=f"{image_name}:{image_tag}",
        )
        app.image_tag = image_tag
        app.status = "deploying"
        db.session.add(execution)
        db.session.flush()
        release = ReleaseService().create_deploy_release(
            app, execution, payload, deploy_user
        )
        db.session.commit()
        return execution, release

    @staticmethod
    def _spec(app):
        return {
            "apiVersion": "devops.ai/v1",
            "kind": "Application",
            "metadata": {"name": app.name},
            "spec": {
                "source": {
                    "type": "github",
                    "url": app.repo_url,
                    "branch": app.branch,
                },
                "runtime": {
                    "language": app.language,
                    "framework": app.framework,
                },
                "build": {
                    "type": app.build_type,
                    "image": f"{app.image_name}:{app.image_tag}",
                },
                "deploy": {
                    "type": "kubernetes",
                    "namespace": app.namespace,
                    "replicas": 1,
                    "port": app.port,
                },
            },
        }
