from __future__ import annotations

from typing import Any, Dict, Optional

from app.models import ApplicationConfig, ApplicationEnvironment, ReleaseRecord
from app.models import Project
from app.utils.errors import ApiError
from .application_service import ApplicationService
from .delivery_context_service import DeliveryContextService
from .environment_service import EnvironmentService
from .build_version_service import BuildVersionService


class DeploymentPlanService:
    def build_plan(self, app, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        environment_name = str(payload.get("environment", "dev") or "dev").strip().lower()
        build_version = None
        if payload.get("build_version_id"):
            build_version = BuildVersionService().require_publishable(app, int(payload["build_version_id"]))
        environment = ApplicationEnvironment.query.filter_by(
            application_id=app.id, environment_name=environment_name
        ).first()
        if not environment:
            EnvironmentService().list(app, ensure_defaults=True)
            environment = ApplicationEnvironment.query.filter_by(
                application_id=app.id, environment_name=environment_name
            ).first()

        pipeline_map = ApplicationService.DEPLOY_PIPELINES if build_version else ApplicationService.PIPELINES
        pipeline_name = pipeline_map.get((app.language, app.build_type))
        image_tag = build_version.image_tag if build_version else str(payload.get("image_tag", app.image_tag) or app.image_tag)
        project = Project.query.filter_by(id=app.project_id).first()
        context = None
        context_error = None
        if project:
            try:
                context = DeliveryContextService().resolve(
                    project, app, environment_name
                )
            except ApiError as exc:
                context_error = exc
        image_name = build_version.image_name if build_version else (context.image_name if context else app.image_name)

        checks: list[dict[str, str]] = []

        def add_check(name: str, status: str, summary: str, detail: str):
            checks.append({
                "name": name,
                "status": status,
                "summary": summary,
                "detail": detail,
            })

        if environment:
            add_check(
                "environment",
                "pass",
                f"目标环境 {environment.environment_name} 已就绪",
                f"将发布到 namespace {environment.namespace}。",
            )
        else:
            add_check(
                "environment",
                "blocked",
                f"目标环境 {environment_name} 不存在",
                "请先创建环境或选择一个已存在的环境。",
            )

        if pipeline_name:
            add_check(
                "build_type",
                "pass",
                "已匹配可用的流水线模板",
                f"将使用 {pipeline_name} 执行构建与部署。",
            )
        else:
            add_check(
                "build_type",
                "blocked",
                "当前项目构建类型尚不支持自动部署",
                f"{app.language}/{app.build_type} 尚未配置 Tekton 流水线模板。",
            )

        if context:
            add_check(
                "cluster",
                "pass",
                "目标 Kubernetes 集群已就绪",
                f"将使用 {context.cluster.name} / {context.kube_context}。",
            )
            add_check(
                "registry",
                "pass",
                "检测到默认镜像仓库",
                f"镜像将推送到 {context.registry.image_prefix}。",
            )
        elif context_error and context_error.code in {
            "CLUSTER_REQUIRED",
            "CLUSTER_NOT_READY",
        }:
            add_check(
                "cluster",
                "blocked",
                context_error.message,
                "请在 Environment 中绑定并测试当前 Project 的 Kubernetes 集群。",
            )
        elif context_error and context_error.code in {
            "REGISTRY_REQUIRED",
            "REGISTRY_NOT_READY",
        }:
            if environment and environment.kubernetes_cluster:
                add_check(
                    "cluster",
                    "pass",
                    "目标 Kubernetes 集群已就绪",
                    f"将使用 {environment.kubernetes_cluster.name}。",
                )
            add_check(
                "registry",
                "blocked",
                context_error.message,
                "请配置并测试当前 Project 的默认 Registry。",
            )

        config_items = []
        if environment:
            config_items = ApplicationConfig.query.filter_by(
                application_id=app.id,
                environment_id=environment.id,
                is_active=True,
            ).all()
        config_type_counts: dict[str, int] = {}
        for item in config_items:
            config_type_counts[item.config_type] = config_type_counts.get(item.config_type, 0) + 1
        if config_items:
            add_check(
                "configuration",
                "pass",
                "已找到环境配置",
                "、".join(
                    f"{config_type}:{count}"
                    for config_type, count in sorted(config_type_counts.items())
                ),
            )
        else:
            add_check(
                "configuration",
                "warn",
                "目标环境尚未配置任何应用参数",
                "平台会按默认模板部署，但建议先补齐 env/configmap/secret。",
            )

        baseline_check = self._baseline_config_check(app.id, environment)
        if baseline_check:
            add_check("config_drift", *baseline_check)

        latest_release = None
        if environment:
            latest_release = ReleaseRecord.query.filter_by(
                application_id=app.id,
                environment=environment.environment_name,
            ).order_by(ReleaseRecord.created_at.desc()).first()
        if latest_release and latest_release.deploy_status == "Failed":
            add_check(
                "recent_release",
                "warn",
                "最近一次发布失败",
                f"最近失败版本为 {latest_release.image_tag}，建议先确认失败原因。",
            )
        elif latest_release and latest_release.deploy_status in {"Pending", "Running"}:
            add_check(
                "recent_release",
                "warn",
                "目标环境存在未结束的发布记录",
                f"最近一次发布状态为 {latest_release.deploy_status}。",
            )
        else:
            add_check(
                "recent_release",
                "pass",
                "最近发布记录未发现阻塞问题",
                "可以继续本次发布。",
            )

        runtime_status = environment.status if environment else "Unknown"
        if runtime_status in {"Failed", "Unknown"}:
            add_check(
                "runtime",
                "warn",
                f"当前环境健康状态为 {runtime_status}",
                "建议先检查运行态再继续部署。",
            )
        else:
            add_check(
                "runtime",
                "pass",
                f"当前环境状态为 {runtime_status}",
                "运行态没有显式阻塞。",
            )

        if environment and environment.approval_required:
            add_check(
                "approval",
                "warn",
                "目标环境需要审批",
                "提交发布后会进入审批流，而不是直接创建 PipelineRun。",
            )
        else:
            add_check(
                "approval",
                "pass",
                "目标环境可直接交付",
                "本次发布不会进入审批队列。",
            )

        blocked = [item for item in checks if item["status"] == "blocked"]
        warnings = [item for item in checks if item["status"] == "warn"]
        risk_level = self._risk_level(environment, blocked, warnings)
        return {
            "can_deploy": not blocked,
            "risk_level": risk_level,
            "summary": self._summary(environment_name, blocked, warnings, risk_level),
            "target": {
                "application_id": app.id,
                "application_name": app.name,
                "environment": environment_name,
                "build_version": build_version.to_dict() if build_version else None,
                "namespace": environment.namespace if environment else payload.get("namespace", app.namespace),
                "image_name": image_name,
                "image_tag": image_tag,
                "pipeline_name": pipeline_name,
                "approval_required": bool(environment and environment.approval_required),
                "cluster": (
                    {
                        "id": context.cluster.id,
                        "name": context.cluster.name,
                        "connection_status": context.cluster.connection_status,
                    }
                    if context else None
                ),
                "registry": (
                    {
                        "id": context.registry.id,
                        "name": context.registry.name,
                        "image_prefix": context.registry.image_prefix,
                        "connection_status": context.registry.connection_status,
                    }
                    if context else None
                ),
            },
            "checks": checks,
            "blocked_checks": [item["name"] for item in blocked],
            "warning_checks": [item["name"] for item in warnings],
        }

    def _baseline_config_check(
        self,
        application_id: int,
        environment: Optional[ApplicationEnvironment],
    ):
        if not environment or environment.environment_name == "dev":
            return None
        baseline = ApplicationEnvironment.query.filter(
            ApplicationEnvironment.application_id == application_id,
            ApplicationEnvironment.environment_name.in_(["staging", "test", "dev"]),
            ApplicationEnvironment.id != environment.id,
        ).order_by(ApplicationEnvironment.id.desc()).first()
        if not baseline:
            return (
                "pass",
                "没有可对比的参考环境",
                "暂时无法判断配置漂移风险。",
            )
        current_keys = {
            item.config_key
            for item in ApplicationConfig.query.filter_by(
                application_id=application_id,
                environment_id=environment.id,
                is_active=True,
            ).all()
        }
        baseline_keys = {
            item.config_key
            for item in ApplicationConfig.query.filter_by(
                application_id=application_id,
                environment_id=baseline.id,
                is_active=True,
            ).all()
        }
        missing = sorted(baseline_keys - current_keys)
        extra = sorted(current_keys - baseline_keys)
        if missing:
            return (
                "warn",
                f"与 {baseline.environment_name} 相比存在配置缺口",
                f"缺少 {', '.join(missing[:6])}{' 等' if len(missing) > 6 else ''}。",
            )
        if extra:
            return (
                "warn",
                f"与 {baseline.environment_name} 相比存在额外配置项",
                f"新增 {', '.join(extra[:6])}{' 等' if len(extra) > 6 else ''}。",
            )
        return (
            "pass",
            f"与 {baseline.environment_name} 的配置键集合一致",
            "未发现明显的配置键漂移。",
        )

    @staticmethod
    def _risk_level(environment, blocked, warnings):
        if blocked:
            return "high"
        if environment and environment.approval_required:
            return "high" if len(warnings) >= 2 else "medium"
        if len(warnings) >= 2:
            return "medium"
        return "low"

    @staticmethod
    def _summary(environment_name: str, blocked, warnings, risk_level: str):
        if blocked:
            return f"{environment_name} 环境的发布前检查未通过，请先处理 {len(blocked)} 个阻塞项。"
        if warnings:
            return (
                f"{environment_name} 环境可继续发布，但存在 {len(warnings)} 个"
                f"{'高' if risk_level == 'high' else ''}风险提示。"
            )
        return f"{environment_name} 环境的发布前检查已通过，可以直接执行部署。"
