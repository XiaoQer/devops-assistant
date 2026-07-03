from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.models import Application


@dataclass
class IntentResolution:
    intent: str
    confidence: float
    target: Optional[Dict[str, Any]] = None
    requires_confirmation: bool = False
    recommended_action: Optional[Dict[str, Any]] = None
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent,
            "confidence": self.confidence,
            "target": self.target or {},
            "requires_confirmation": self.requires_confirmation,
            "recommended_action": self.recommended_action or {},
            "reasoning": self.reasoning,
        }


class AiAssistantService:
    ENVIRONMENT_ALIASES = {
        "production": "prod",
        "prod": "prod",
        "staging": "staging",
        "test": "test",
        "testing": "test",
        "dev": "dev",
        "development": "dev",
    }

    def analyze_user_intent(self, text: str) -> Dict[str, Any]:
        normalized = (text or "").strip().lower()
        app = self._match_application(normalized)
        environment = self._match_environment(normalized)

        resolution = self._resolve_intent(normalized, app, environment)
        payload = resolution.to_dict()
        payload.update(
            {
                "text": text,
                "matched_application": app.to_dict(include_spec=False) if app else None,
                "matched_environment": environment,
                "mock": False,
            }
        )
        return payload

    def explain_pipeline_failure(self, logs):
        return "流水线失败，请优先检查日志末尾的错误信息。"

    def suggest_fix(self, application, logs):
        return "请确认构建命令、镜像仓库凭证与 Kubernetes 部署权限。"

    def _resolve_intent(
        self,
        normalized: str,
        app: Optional[Application],
        environment: Optional[str],
    ) -> IntentResolution:
        if not normalized:
            return IntentResolution(
                intent="open_command_palette",
                confidence=0.6,
                recommended_action={"type": "open_palette"},
                reasoning="未提供明确指令，建议打开命令面板继续选择操作。",
            )

        if self._contains_any(normalized, ["deploy", "发布", "部署"]):
            if app:
                return IntentResolution(
                    intent="deploy_application",
                    confidence=0.96,
                    target={"application_id": app.id, "application_name": app.name, "environment": environment or "dev"},
                    requires_confirmation=(environment or "dev") == "prod",
                    recommended_action={"type": "deploy", "route": f"/applications/{app.id}"},
                    reasoning="已识别为应用部署指令，并匹配到目标应用。",
                )
            return IntentResolution(
                intent="open_releases",
                confidence=0.72,
                recommended_action={"type": "navigate", "route": "/releases"},
                reasoning="识别为部署相关意图，但未匹配到明确应用，建议进入发布中心。",
            )

        if self._contains_any(normalized, ["rollback", "回滚"]):
            if app:
                return IntentResolution(
                    intent="rollback_application",
                    confidence=0.92,
                    target={"application_id": app.id, "application_name": app.name, "environment": environment or "dev"},
                    requires_confirmation=True,
                    recommended_action={"type": "navigate", "route": "/releases"},
                    reasoning="识别为回滚意图，建议进入发布历史选择目标版本。",
                )
            return IntentResolution(
                intent="open_releases",
                confidence=0.76,
                recommended_action={"type": "navigate", "route": "/releases"},
                reasoning="识别为回滚相关意图，建议进入发布中心。",
            )

        if self._contains_any(normalized, ["incident", "故障", "error", "failed", "失败"]):
            return IntentResolution(
                intent="show_incidents",
                confidence=0.88,
                recommended_action={"type": "navigate", "route": "/pipelines"},
                reasoning="识别为故障/失败排查意图，建议查看流水线执行与失败记录。",
            )

        if self._contains_any(normalized, ["approval", "审批"]):
            return IntentResolution(
                intent="open_approvals",
                confidence=0.9,
                recommended_action={"type": "navigate", "route": "/approvals"},
                reasoning="识别为审批治理相关意图。",
            )

        if self._contains_any(normalized, ["create", "新建", "创建"]):
            return IntentResolution(
                intent="create_application",
                confidence=0.84,
                recommended_action={"type": "navigate", "route": "/applications/new"},
                reasoning="识别为创建应用工作区意图。",
            )

        if app and self._contains_any(normalized, ["open", "查看", "打开"]):
            return IntentResolution(
                intent="open_application",
                confidence=0.93,
                target={"application_id": app.id, "application_name": app.name},
                recommended_action={"type": "navigate", "route": f"/applications/{app.id}"},
                reasoning="识别为查看应用工作区意图。",
            )

        return IntentResolution(
            intent="unknown",
            confidence=0.35,
            recommended_action={"type": "open_palette"},
            reasoning="未能将输入稳定映射到平台动作，建议保留原始文本继续由前端命令面板筛选。",
        )

    def _match_application(self, normalized: str) -> Optional[Application]:
        if not normalized:
            return None
        applications = Application.query.all()
        return next((app for app in applications if app.name.lower() in normalized), None)

    def _match_environment(self, normalized: str) -> Optional[str]:
        for key, value in self.ENVIRONMENT_ALIASES.items():
            if key in normalized:
                return value
        return None

    @staticmethod
    def _contains_any(text: str, words: list[str]) -> bool:
        return any(word in text for word in words)
