# 02. System Architecture

## 1. Architecture Summary

Aegis 的系统架构可以概括为：

> 一个以 Flask 为控制面、以 MySQL 为状态存储、以 Kubernetes + Tekton 为执行面、以 Vue 3 为用户交互面的 AI Native DevOps Platform。

它不是一个单体“执行引擎”，而是一个围绕 **应用交付与运行** 的协调层。

平台负责：
- 管理应用元数据
- 管理环境与配置
- 触发交付动作
- 追踪发布记录
- 编排审批流程
- 查询运行状态
- 为前端和 AI 提供统一上下文

---

## 2. High-Level Architecture Diagram

```text
┌────────────────────────────────────────────────────────────┐
│ Frontend (Vue 3 + TypeScript + Vite)                      │
│ - Dashboard / Applications / Pipelines / Releases         │
│ - AI Command / Command Palette                            │
└────────────────────────────────────────────────────────────┘
                           │
                           │ REST API
                           ▼
┌────────────────────────────────────────────────────────────┐
│ Backend Control Plane (Flask)                             │
│                                                            │
│  Routes  →  Services  →  Models / Infra                    │
│                                                            │
│ - Applications                                              │
│ - Environments                                              │
│ - Configurations                                            │
│ - Releases                                                  │
│ - Pipelines                                                 │
│ - Approvals                                                 │
│ - Registries                                                │
└────────────────────────────────────────────────────────────┘
              │                           │
              │                           │
              ▼                           ▼
┌───────────────────────┐       ┌──────────────────────────┐
│ MySQL                 │       │ Kubernetes API           │
│ - Platform state      │       │ - Deployments            │
│ - Release records     │       │ - Services               │
│ - Environments        │       │ - Ingress                │
│ - Config versions     │       │ - ConfigMaps / Secrets   │
│ - Approvals           │       │ - Pods / Events          │
└───────────────────────┘       │ - Tekton PipelineRuns    │
                                └──────────────────────────┘
                                           │
                                           ▼
                                ┌──────────────────────────┐
                                │ Execution Plane          │
                                │ - Tekton Pipelines       │
                                │ - Kaniko Builds          │
                                │ - Kubernetes Deploy      │
                                └──────────────────────────┘
```

---

## 3. Core Architectural Style

Aegis 当前采用的是一种 **控制面 + 执行面** 的架构思路。

### 3.1 Control Plane
由 Flask 后端承担。

职责：
- 管理业务状态
- 保存平台元数据
- 对外暴露统一 API
- 组织多步骤工作流
- 驱动 Kubernetes / Tekton

### 3.2 Execution Plane
由 Kubernetes + Tekton + Kaniko 承担。

职责：
- 实际拉取源码
- 实际构建镜像
- 实际部署工作负载
- 提供运行期状态与日志

### 3.3 Presentation Layer
由 Vue 前端承担。

职责：
- 组织人类交互
- 把复杂基础设施信息转化成软件交付上下文
- 提供 AI Native 的交互入口

---

## 4. Backend Layering

后端遵循相对清晰的分层：

```text
Routes / Controllers
        ↓
Services / Application Logic
        ↓
Models / Persistence
        ↓
Infrastructure Adapters
(Kubernetes, Tekton, Git, Registry, DB)
```

### 4.1 Routes Layer
位于 `backend/app/routes/`。

职责：
- 接收 HTTP 请求
- 处理参数与响应格式
- 调用 Service 层
- 返回统一 JSON 响应

### 4.2 Services Layer
位于 `backend/app/services/`。

职责：
- 实现业务用例
- 组织多资源、多步骤流程
- 隔离路由层与基础设施细节

### 4.3 Models Layer
位于 `backend/app/models/`。

职责：
- 维护平台领域对象与关系
- 作为 MySQL 持久化模型
- 保存平台“事实状态”

### 4.4 Infrastructure Responsibilities
虽然当前项目未单独拆成 `infrastructure/` 包，但多个 Service 已经承担适配器角色：

- `KubernetesService`
- `TektonService`
- `RepoAnalyzerService`
- `RegistryService`

这些组件本质上就是外部系统适配层。

---

## 5. Frontend Architecture Style

前端采用：

- Vue 3
- TypeScript
- Pinia
- Vue Router
- Element Plus
- Vite

在结构上大体是：

```text
Views (page-level)
    ↓
Feature Components
    ↓
Common Components
    ↓
API Layer / Stores
```

### 5.1 Views
位于 `frontend/src/views/`。

代表平台一级能力面：
- Dashboard
- Applications
- Application Detail
- Pipelines
- Releases
- Approvals
- Registries

### 5.2 Feature Components
位于：
- `frontend/src/components/application/`
- `frontend/src/components/pipeline/`

职责：
- 承载页面内部复杂业务视图
- 形成“应用工作区”“流水线工作区”等能力模块

### 5.3 Common Components
位于 `frontend/src/components/common/`。

职责：
- 统一通用视觉与交互
- 提供 PageHeader / MetricCard / StatusBadge / EmptyState / CommandPalette

### 5.4 Stores
当前主要包括：
- `application.ts`
- `ui.ts`
- `command.ts`

职责：
- 管理页面级共享状态
- 管理主题/侧边栏/UI 状态
- 管理全局 AI Command 面板状态

---

## 6. Core Runtime Flow

### 6.1 Application Creation Flow

```text
User submits repo URL
  → Application API
  → RepoAnalyzerService clones repository
  → detect language / framework / build type
  → generate Application Spec
  → create Application record
  → initialize default environments
  → return application workspace
```

### 6.2 Deployment Flow

```text
User triggers deploy
  → ApplicationService.deploy()
  → load target environment
  → if approval required:
        create approval record
        stop until approval accepted
    else:
        create Tekton PipelineRun
        create release record
        return pipeline run info
```

### 6.3 Approval Flow

```text
Production deploy request
  → ApprovalRecord created
  → Reviewer opens approval queue
  → approve / reject
  → if approved:
        continue pipeline/deploy flow
  → if rejected:
        release blocked and recorded
```

### 6.4 Runtime Inspection Flow

```text
User opens application runtime status
  → Backend calls KubernetesService
  → collect deployment/service/ingress/pods/events
  → normalize data into RuntimeStatus
  → return to frontend runtime workspace
```

---

## 7. Core Architectural Decisions

### 7.1 Why Application is the Primary Aggregate
相比直接围绕 Pipeline、Deployment 或 Namespace 建模，Aegis 选择以 `Application` 为核心。

原因：
- 开发者最关心的是“我的服务”
- 一切交付动作都可以回归到某个应用
- 便于组织环境、配置、发布、审批和运行态

### 7.2 Why Tekton Instead of Custom Build Engine
当前选择 Tekton 作为执行平面编排工具。

好处：
- 原生 Kubernetes 生态
- 流水线模板可 declarative 管理
- 与 Kaniko、PVC、ServiceAccount、Secrets 更容易集成
- 避免自己写一套复杂任务调度器

### 7.3 Why Keep State in MySQL
Kubernetes 和 Tekton 提供的是“执行态”，但平台还需要保存：
- 业务级历史
- 配置版本
- 审批记录
- 镜像仓库配置
- 应用元数据

这些信息不适合完全依赖 K8s 对象本身，因此 MySQL 是平台状态的稳定来源。

### 7.4 Why Frontend is Becoming AI-Native
前端不再只是“页面集合”，而是在演进成：
- 操作意图入口
- 软件工作区
- 推荐动作界面
- 命令式交互层

因此加入了：
- AI Command Hero
- Global Command Palette
- Recommended / Recent Commands

---

## 8. Architectural Strengths

当前架构的主要优点：

1. **边界清晰**
   - 前端、控制面、执行面、状态存储分工明确

2. **可扩展性较好**
   - 支持增加新的语言、构建模板、环境策略

3. **面向真实交付链路**
   - 不只是静态资源管理，而是覆盖 Git → Build → Deploy → Runtime

4. **领域对象相对统一**
   - Application / Environment / Config / Release / Approval 模型较一致

5. **具备 AI 接入基础**
   - 现在已经存在 UI 层的 AI 交互入口和结构化平台上下文

---

## 9. Architectural Weaknesses / Current Gaps

当前仍存在一些典型 MVP 阶段问题：

### 9.1 Service 边界仍有耦合
部分 Service 同时承担：
- 业务流程编排
- 外部系统适配
- 数据更新

后续可继续拆分为：
- Domain Service
- Infra Adapter
- Workflow Orchestrator

### 9.2 缺少显式事件机制
当前很多流程更像同步调用链。

未来可考虑：
- 领域事件
- 异步任务
- 统一状态同步机制

### 9.3 AI 还主要在前端层
现在 AI 交互能力更多停留在：
- 命令入口
- 提示型体验

尚未完整进入后端执行体系。

### 9.4 监控体系未闭环
当前可查运行态，但还不是一个真正的 observability platform。

---

## 10. Architecture Evolution Direction

建议未来继续演进为：

### Phase 1：工程化增强
- 更清晰的后端模块分层
- 更系统的文档与 API 契约
- 更好的测试覆盖

### Phase 2：AI Workflow Integration
- 引入 AI planning / execution orchestration
- 自然语言 → 平台动作 → 人工确认 → 执行

### Phase 3：Software OS 化
- 项目 / 需求 / 代码 / 发布 / 运行 / 知识统一进入一个平台上下文
- Command Palette 升级为真正的 AI Command Center

---

## 11. Summary

Aegis 当前架构的本质是：

> 以前端作为 AI Native 交互层，以 Flask 作为软件交付控制面，以 Kubernetes + Tekton 作为执行面，以 MySQL 作为平台状态存储的应用交付系统。

从软件工程角度，它已经具备清晰的核心对象、可工作的运行流和明确的扩展方向。

从产品角度，它正在从“DevOps 平台 MVP”向“Software OS”演进。

