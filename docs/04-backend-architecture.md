# 04. Backend Architecture

## 1. Overview

Aegis 后端是平台的 **控制面（Control Plane）**。

技术栈主要包括：
- Python 3.11+
- Flask
- Flask-SQLAlchemy
- Alembic
- Kubernetes Python Client
- GitPython
- PyMySQL

后端的核心职责不是直接执行构建任务，而是：

- 管理平台状态
- 编排业务流程
- 调用 Kubernetes / Tekton
- 把底层执行状态转换成平台级语义
- 对前端和 AI 提供统一接口

---

## 2. Backend Directory Structure

核心目录：

```text
backend/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── extensions.py
│   ├── models/
│   ├── routes/
│   ├── services/
│   └── utils/
├── migrations/
├── requirements.txt
└── run.py
```

---

## 3. Bootstrapping

### 3.1 `run.py`
负责启动 Flask 应用。

### 3.2 `app/__init__.py`
负责：
- 创建 Flask app
- 加载配置
- 初始化扩展
- 注册蓝图
- 统一错误处理
- 暴露额外 CLI/同步能力

从工程角度看，`app/__init__.py` 是后端应用装配根（composition root）。

---

## 4. Configuration

### 4.1 `app/config.py`
配置来源主要通过环境变量注入，典型包括：
- `DATABASE_URL`
- `AUTO_CREATE_SCHEMA`
- `SECRET_KEY`
- `TEKTON_NAMESPACE`
- `DEFAULT_IMAGE_REGISTRY`

### 4.2 Configuration Philosophy
当前后端配置遵循：
- 本地开发通过环境变量快速覆盖
- 集群部署通过 Secret / Deployment env 注入
- 避免在代码中写死具体环境值

---

## 5. Extensions Layer

### 5.1 `app/extensions.py`
负责初始化：
- SQLAlchemy
- Alembic / migration 支持

这让数据库依赖从具体模块中解耦出来，便于应用初始化统一装配。

---

## 6. Routes Layer

位于 `backend/app/routes/`。

目前主要蓝图包括：
- `applications.py`
- `approvals.py`
- `environments.py`
- `health.py`
- `pipelines.py`
- `registries.py`
- `releases.py`

### 6.1 角色
Routes 层的理想职责是：
- 参数校验
- 请求解析
- 调用服务层
- 响应封装

### 6.2 当前特点
当前代码中，Routes 层总体保持较薄，但仍有少量业务判断直接存在于路由中。整体上已经具备典型 Flask 分层应用结构。

---

## 7. Services Layer

位于 `backend/app/services/`。

这是后端最核心的部分。

### 7.1 `application_service.py`
核心职责：
- 创建应用
- 调用仓库分析
- 初始化环境
- 触发部署工作流
- 协调发布与审批逻辑

可以把它看成 **应用交付的主编排服务**。

### 7.2 `repo_analyzer_service.py`
职责：
- 克隆仓库
- 检测语言与框架
- 判断构建方式
- 推导 Application Spec

它是平台“Git → 平台理解”链路的起点。

### 7.3 `tekton_service.py`
职责：
- 根据应用类型选择 Tekton Pipeline 模板
- 创建 PipelineRun
- 组织执行参数
- 与 Tekton 资源交互

它是典型的 **执行面适配器**。

### 7.4 `kubernetes_service.py`
职责：
- 加载 kubeconfig / incluster config
- 查询 Deployment、Service、Ingress、Pods、Events
- 创建或更新配置资源
- 读取运行态信息

它是 Kubernetes 统一接入点。

### 7.5 `release_service.py`
职责：
- 创建发布记录
- 同步 Tekton 执行结果到业务发布状态
- 处理回滚相关记录

它将“执行状态”提升为“发布事实”。

### 7.6 `environment_service.py`
职责：
- 创建默认环境
- 环境更新与克隆
- 环境对比

### 7.7 `configuration_service.py`
职责：
- 保存配置项
- 管理配置版本
- 区分 Secret 和普通配置

### 7.8 `registry_service.py`
职责：
- 管理镜像仓库连接
- 加密保存凭据
- 维护默认 Registry
- 为 Tekton / Deployment 生成所需凭据材料

### 7.9 `approval_service.py`
职责：
- 创建审批申请
- 审批通过 / 拒绝
- 串联审批状态与后续发布链路

### 7.10 `ai_assistant_service.py`
当前更接近预留模块，未来适合作为：
- AI Prompt Orchestrator
- AI Recommendation Engine
- Intent → Plan → Action 的桥接层

---

## 8. Models Layer

位于 `backend/app/models/`。

主要模型包括：
- `application.py`
- `application_environment.py`
- `application_config.py`
- `approval_record.py`
- `container_registry.py`
- `pipeline_execution.py`
- `project.py`
- `release_record.py`

这些模型共同表达平台状态。

从架构角度，它们承担：
- ORM 持久化对象
- 领域实体载体
- 业务关系表达

---

## 9. Utilities Layer

位于 `backend/app/utils/`。

包括：
- `errors.py`
- `response.py`

### 9.1 `errors.py`
集中定义平台错误码与错误结构。

### 9.2 `response.py`
统一响应格式，使 API 保持一致：
- `success`
- `message`
- `data`
- `timestamp`
- `trace_id`

这对前端和 AI 都非常重要，因为它能提供更稳定的上下文契约。

---

## 10. Data Access and Persistence

### 10.1 ORM Strategy
Aegis 使用 SQLAlchemy 作为 ORM。

优点：
- 便于关系建模
- 与 Flask 生态配合成熟
- 适合 MVP 到中型平台阶段

### 10.2 Migration Strategy
使用 Alembic 管理 schema 演进。

迁移位于：
- `backend/migrations/versions/`

这意味着数据库演进已经具备工程化基础，不是纯运行时自动建表的临时方案。

---

## 11. External System Integration

后端集成了多个外部系统：

### 11.1 Git
通过 `RepoAnalyzerService` 访问 Git 仓库，用于：
- 克隆源码
- 检测项目结构

### 11.2 Kubernetes
通过 `KubernetesService` 接入 Kubernetes API，用于：
- 查询运行态
- 管理配置对象
- 执行部署相关资源操作

### 11.3 Tekton
通过 `TektonService` 创建与读取 PipelineRun，用于：
- 流水线编排
- 任务状态追踪

### 11.4 Registry
通过 `RegistryService` 管理镜像仓库连接与凭据。

---

## 12. Backend Runtime Workflows

### 12.1 Create Application Workflow
```text
HTTP POST /applications
  → ApplicationService.create
  → RepoAnalyzerService.analyze
  → persist Application
  → EnvironmentService.initialize_defaults
  → return Application + Spec
```

### 12.2 Deploy Workflow
```text
HTTP POST /applications/:id/deploy
  → load Application + Environment
  → if approval required:
        ApprovalService.submit
    else:
        TektonService.create_pipeline_run
        ReleaseService.create_release
```

### 12.3 Sync Delivery Workflow
```text
manual/cron sync-deliveries
  → query release / pipeline records
  → read Tekton PipelineRun state
  → update release statuses
```

### 12.4 Runtime Inspection Workflow
```text
HTTP GET /applications/:id/status
  → KubernetesService.query_runtime
  → normalize runtime payload
  → return RuntimeStatus DTO
```

---

## 13. Design Strengths

后端架构当前的优点：

1. **已经具备明显分层**
2. **Service 层承担了较清晰的业务编排职责**
3. **外部系统集成点较集中**
4. **领域对象较完整**
5. **数据库迁移已工程化**
6. **统一错误/响应机制已建立**

---

## 14. Design Risks and Improvement Points

### 14.1 Service Responsibilities Are Still Broad
部分 Service 既承担：
- 业务流程
- 外部适配
- 状态变更

未来建议继续拆为：
- `Domain Service`
- `Workflow Orchestrator`
- `Infra Adapter`

### 14.2 DTO / Schema Layer Is Not Explicit
当前接口输入输出更偏动态结构。

未来可考虑：
- Pydantic / dataclass DTO
- 请求响应 schema 明确化

### 14.3 Async / Event Mechanism Is Limited
目前以同步调用为主。

未来可考虑：
- 异步任务队列
- 事件驱动状态同步
- Webhook / polling 结合

### 14.4 AI Layer Is Still Early
虽然已有 `ai_assistant_service.py`，但尚未形成完整 AI orchestration 能力。

---

## 15. Suggested Future Refactoring

建议未来将后端架构演进为：

```text
API Layer
  ↓
Application Layer (use cases)
  ↓
Domain Layer (entities / rules)
  ↓
Infrastructure Layer (K8s / Tekton / Git / DB)
```

同时将当前 Service 中的大流程拆分为：
- Command handlers
- Query handlers
- External adapters
- Policy evaluators

这会更适合未来 AI Agent 与多团队协作扩展。

---

## 16. Summary

Aegis 后端已经具备一个成熟雏形：

- Flask 作为控制面
- Service 层作为业务编排中枢
- MySQL 作为平台事实状态
- Kubernetes / Tekton 作为执行系统适配对象

从软件工程角度，它已经超过简单 Demo，具备继续演进成真正平台控制面的基础。

