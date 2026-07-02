class AiAssistantService:
    def analyze_user_intent(self, text):
        return {"intent": "unknown", "text": text, "mock": True}

    def explain_pipeline_failure(self, logs):
        return "流水线失败，请优先检查日志末尾的错误信息。"

    def suggest_fix(self, application, logs):
        return "请确认构建命令、镜像仓库凭证与 Kubernetes 部署权限。"

