from datetime import datetime, timezone
from uuid import uuid4
from flask import current_app

from app.extensions import db
from app.models import Application, PipelineExecution, ApplicationEnvironment, ApplicationBuildVersion, ApplicationReleaseTarget
from app.utils.errors import ApiError
from .repo_analyzer_service import RepoAnalyzerService
from .tekton_service import TektonService
from .git_metadata_service import GitMetadataService
from .release_service import ReleaseService
from .configuration_service import ConfigurationService
from .kubernetes_service import KubernetesService
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
        return app

    def build(self, app, build_user="local-user", branch=None, git_commit=None,
              commit_message=None, commit_author=None, release_batch=None):
        pipeline = self.BUILD_PIPELINES.get((app.language, app.build_type))
        if not pipeline:
            raise ApiError(f"暂不支持 {app.language}/{app.build_type} 项目", 422, "UNSUPPORTED_BUILD_TYPE")
        registry = RegistryService().get_project_default(app.project_id)
        if not registry:
            raise ApiError("项目尚未配置默认镜像仓库", 409, "REGISTRY_REQUIRED")
        branch = branch or app.branch
        if not git_commit:
            commits = GitMetadataService().list_commits(app.repo_url, branch, 1)
            if not commits:
                raise ApiError("分支没有可构建的提交", 422, "GIT_COMMIT_NOT_FOUND")
            git_commit = commits[0]["sha"]
            commit_message = commits[0]["message"]
            commit_author = commits[0]["author"]
        image_name = f"{registry.image_prefix}/{app.name}"
        tag = f"build-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:6]}"
        version = ApplicationBuildVersion(
            application_id=app.id,
            project_id=app.project_id,
            version=tag,
            git_repo=app.repo_url,
            git_branch=branch,
            git_commit=git_commit,
            commit_message=commit_message,
            commit_author=commit_author,
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
            pipeline, app.name, app.repo_url, branch, image_name, tag,
            tekton_namespace, registry_secret, git_commit,
        )
        if release_batch:
            version.release_batch = release_batch
        db.session.commit()
        return version

    def deploy(self, app, payload=None, deploy_user="local-user", recovery=None):
        payload = payload or {}
        recovery = recovery or {}
        environment_name = payload.get("environment", "dev")
        environment = ApplicationEnvironment.query.filter_by(
            application_id=app.id, environment_name=environment_name
        ).first()
        if not environment:
            environment = None
        if environment:
            payload.setdefault("namespace", environment.namespace)
        build_version = None
        if payload.get("build_version_id"):
            build_version = BuildVersionService().require_publishable(
                app, int(payload["build_version_id"])
            )
        release_target = None
        if recovery.get("release_target_id"):
            release_target = db.session.get(
                ApplicationReleaseTarget,
                int(recovery["release_target_id"]),
            )
            if (
                not release_target
                or release_target.batch.application_id != app.id
                or release_target.batch.project_id != app.project_id
                or release_target.environment_id != (environment.id if environment else None)
                or release_target.batch.build_version_id != (
                    build_version.id if build_version else None
                )
            ):
                raise ApiError(
                    "发布目标与应用、环境或构建版本不匹配",
                    409,
                    "RELEASE_TARGET_CONTEXT_MISMATCH",
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
            "env_config_map_name": f"{app.name}-env",
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
            deployment_config.update(resources.get("resource_overrides", {}))
        payload["image_name"] = image_name
        payload["image_tag"] = image_tag
        if build_version:
            payload["build_version_id"] = build_version.id
        if build_version:
            renew_claim = recovery.get("renew_claim")
            if renew_claim:
                renew_claim()
            run_name = recovery.get("existing_pipeline_run_name")
            if not run_name:
                release_target_id = recovery.get("release_target_id")
                labels = (
                    {"aegis.dev/release-target-id": str(release_target_id)}
                    if release_target_id else None
                )
                run_name = TektonService().create_deploy_pipeline_run(
                    pipeline, app.name, image_name, image_tag, tekton_namespace,
                    deploy_namespace, app.port, deployment_config,
                    kubeconfig_secret_name, kube_context, labels,
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
        if release_target:
            release_target.pipeline_run_name = run_name
            release_target.build_version_id = build_version.id if build_version else None
            release_target.status = "Running"
            release_target.error_message = None
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
