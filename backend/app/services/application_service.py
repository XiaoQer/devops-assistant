from datetime import datetime, timezone
from uuid import uuid4
from flask import current_app

from app.extensions import db
from app.models import Application, PipelineExecution, ApplicationEnvironment, ApplicationBuildVersion
from app.utils.errors import ApiError
from .repo_analyzer_service import RepoAnalyzerService
from .tekton_service import TektonService
from .release_service import ReleaseService
from .configuration_service import ConfigurationService
from .kubernetes_service import KubernetesService
from .environment_service import EnvironmentService
from .registry_service import RegistryService
from .delivery_context_service import DeliveryContextService
from .kubernetes_cluster_service import KubernetesClusterService
from .cluster_credential_materializer import ClusterCredentialMaterializer
from .build_version_service import BuildVersionService


class ApplicationService:
    PIPELINES = {
        ("java", "maven"): "java-maven-kaniko-deploy",
        ("nodejs", "npm"): "node-npm-kaniko-deploy",
        ("dockerfile", "dockerfile"): "dockerfile-kaniko-deploy",
    }
    BUILD_PIPELINES = {
        ("java", "maven"): "java-maven-kaniko-build",
        ("nodejs", "npm"): "node-npm-kaniko-build",
        ("dockerfile", "dockerfile"): "dockerfile-kaniko-build",
    }
    DEPLOY_PIPELINES = {
        ("java", "maven"): "java-maven-deploy-only",
        ("nodejs", "npm"): "node-npm-deploy-only",
        ("dockerfile", "dockerfile"): "dockerfile-deploy-only",
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
        registry = RegistryService().get_project_default(project.id)
        image_name = payload.get("image_name") or (
            f"{registry.image_prefix}/{payload['name']}" if registry else None
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

    def build(self, app, build_user="local-user"):
        pipeline = self.BUILD_PIPELINES.get((app.language, app.build_type))
        if not pipeline:
            raise ApiError(f"暂不支持 {app.language}/{app.build_type} 项目", 422, "UNSUPPORTED_BUILD_TYPE")
        registry = RegistryService().get_project_default(app.project_id)
        if not registry:
            raise ApiError("项目尚未配置默认镜像仓库", 409, "REGISTRY_REQUIRED")
        image_name = f"{registry.image_prefix}/{app.name}"
        tag = f"build-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:6]}"
        version = ApplicationBuildVersion(
            application_id=app.id,
            project_id=app.project_id,
            version=tag,
            git_repo=app.repo_url,
            git_branch=app.branch,
            image_name=image_name,
            image_tag=tag,
            created_by=build_user,
        )
        db.session.add(version)
        db.session.flush()
        tekton_namespace = current_app.config["TEKTON_NAMESPACE"]
        central_kubernetes = KubernetesService()
        registry_secret = ConfigurationService().materialize_build_registry(
            registry, central_kubernetes, tekton_namespace
        )
        version.pipeline_run_name = TektonService().create_build_pipeline_run(
            pipeline, app.name, app.repo_url, app.branch, image_name, tag,
            tekton_namespace, registry_secret,
        )
        db.session.commit()
        return version

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
        build_version = None
        if payload.get("build_version_id"):
            build_version = BuildVersionService().require_publishable(
                app, int(payload["build_version_id"])
            )
        pipeline = self.DEPLOY_PIPELINES.get((app.language, app.build_type)) if build_version else self.PIPELINES.get((app.language, app.build_type))
        if not pipeline:
            raise ApiError(
                f"暂不支持 {app.language}/{app.build_type} 项目",
                422,
                "UNSUPPORTED_BUILD_TYPE",
            )
        tekton_namespace = current_app.config["TEKTON_NAMESPACE"]
        image_tag = build_version.image_tag if build_version else payload.get("image_tag", app.image_tag)
        deploy_namespace = payload.get("namespace", app.namespace)
        image_name = build_version.image_name if build_version else payload.get("image_name", app.image_name)
        registry = RegistryService().get_project_default(app.project_id)
        delivery_context = None
        try:
            delivery_context = DeliveryContextService().resolve(
                app.project, app, environment_name
            )
        except ApiError:
            # The HTTP route performs the mandatory preflight check. Keep the
            # service usable for legacy callers that do not yet have a bound
            # target context; once a context exists, all writes use its client.
            if environment and (
                environment.kubernetes_cluster_id
                or registry
            ):
                raise
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
        target_kubernetes = None
        kubeconfig_secret_name = ""
        kube_context = ""
        if delivery_context:
            registry = delivery_context.registry
            if not build_version:
                image_name = delivery_context.image_name
            target_kubernetes = KubernetesClusterService().client(
                delivery_context.cluster
            )
            central_kubernetes = KubernetesService()
            kubeconfig_secret_name = ClusterCredentialMaterializer().materialize(
                app.project,
                delivery_context.cluster,
                central_kubernetes,
            )
            deployment_config["registry_secret_name"] = ConfigurationService().materialize_build_registry(
                delivery_context.registry,
                central_kubernetes,
                tekton_namespace,
            )
            kube_context = delivery_context.kube_context
        else:
            target_kubernetes = KubernetesService()
        if environment:
            if registry and not delivery_context:
                image_name = f"{registry.image_prefix}/{app.name}"
            elif environment.image_registry:
                # Backward compatibility for installations created before global registries.
                image_name = f"{environment.image_registry.rstrip('/')}/{app.name}"
            resources = ConfigurationService().materialize(
                app, environment, target_kubernetes, registry=registry
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
        payload["image_tag"] = image_tag
        if build_version:
            payload["build_version_id"] = build_version.id
        if build_version:
            run_name = TektonService().create_deploy_pipeline_run(
                pipeline, app.name, image_name, image_tag, tekton_namespace,
                deploy_namespace, app.port, deployment_config,
                kubeconfig_secret_name, kube_context,
            )
        else:
            run_name = TektonService().create_pipeline_run(
                pipeline, app.name, app.repo_url, app.branch, image_name,
                image_tag, tekton_namespace, app.port,
                deploy_namespace=deploy_namespace,
                deployment_config=deployment_config,
                kubeconfig_secret_name=kubeconfig_secret_name,
                kube_context=kube_context,
            )
        execution = PipelineExecution(
            application_id=app.id,
            project_id=app.project_id,
            build_version_id=build_version.id if build_version else None,
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
                    "image": (
                        f"{app.image_name}:{app.image_tag}"
                        if app.image_name else None
                    ),
                },
                "deploy": {
                    "type": "kubernetes",
                    "namespace": app.namespace,
                    "replicas": 1,
                    "port": app.port,
                },
            },
        }
