# 系统架构

## 系统结构

```text
Vue 3 + TypeScript 前端
            │ REST
            ▼
Flask 控制面 ───────── MySQL 业务状态
            │
            ├──────── Kubernetes API：运行资源与状态检查
            └──────── Tekton：PipelineRun → Kaniko → Kubernetes 部署
```

前端提供门户、项目治理和开发交付工作空间。Flask 后端协调业务工作流，MySQL 记录
平台状态与历史，Kubernetes 和 Tekton 构成执行面。

## 后端边界

```text
路由 → Service → Model / 外部系统适配器
```

- `backend/app/routes` 负责 HTTP 解析和响应处理。
- `backend/app/services` 负责用例和工作流协调。
- `backend/app/models` 负责 SQLAlchemy 持久化模型。
- `KubernetesService` 集中处理 Kubernetes 连接和运行态访问。
- `TektonService` 集中处理 PipelineRun 构建与交互。
- `RepoAnalyzerService` 负责分析 Git 仓库。

当前分层以实用为主，并不纯粹：部分 Service 仍混合工作流和基础设施职责。这是已知
的 MVP 限制，不应随意扩大。

## 前端边界

- `frontend/src/views` 存放路由级工作空间。
- `frontend/src/layouts` 区分门户、项目中心、开发中心和旧版主导航。
- `frontend/src/components` 存放功能组件和公共 UI。
- `frontend/src/stores` 管理客户端共享状态。
- `frontend/src/api` 负责后端通信。

路由当前同时支持新的项目级路由和旧的全局路由。新交付流程优先使用
`/devcenter/projects/:projectId/...`；旧路由仅为兼容保留，等待明确迁移。

## 运行工作流

### 应用接入

后端接收仓库信息、分析代码、推导构建元数据、创建应用并初始化交付上下文。

### 部署

后端解析目标应用环境和镜像仓库，生成部署计划，在需要时通过审批阻断操作，然后创建
Tekton PipelineRun。发布记录和执行记录分别保留业务历史与技术历史。

### 运行态检查

后端从 Kubernetes 查询 Deployment、Service、Ingress、Pod、Event、日志和资源
YAML，并将标准化数据提供给应用工作空间。

## 横切约束

- API 响应使用统一结构和 Trace ID。
- Secret 和镜像仓库凭据在存储及响应边界受到保护。
- 影响生产的操作通过确认或审批进行治理。
- Schema 演进使用 Alembic；自动建表仅用于本地环境。
