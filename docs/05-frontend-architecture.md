# 05. Frontend Architecture

## 1. Overview

Aegis 前端是平台的 **交互面（Interaction Layer）**，负责把后端和基础设施的复杂状态，组织成更适合开发者理解的软件工作区。

当前技术栈：
- Vue 3
- TypeScript
- Vite
- Vue Router
- Pinia
- Element Plus
- Axios

从软件工程角度看，前端承担的不是简单的“页面渲染”，而是：

- 组织软件交付工作流
- 呈现应用、发布、审批、运行状态
- 提供 AI Native 的操作入口
- 将复杂对象转换为更低认知负担的界面语义

---

## 2. Frontend Structure

核心目录：

```text
frontend/src/
├── api/
├── components/
│   ├── application/
│   ├── common/
│   ├── icons/
│   └── pipeline/
├── composables/
├── layouts/
├── router/
├── stores/
├── styles/
├── views/
├── App.vue
├── main.ts
└── types.ts
```

---

## 3. Architectural Layers

前端大体可以分为五层：

### 3.1 App Shell Layer
包括：
- `App.vue`
- `layouts/MainLayout.vue`

职责：
- 注入全局框架
- 承载侧边栏、顶部栏、主内容区
- 注入全局 Command Palette

### 3.2 Route / View Layer
位于 `views/`。

职责：
- 表达平台一级能力面
- 组合业务组件
- 调用 store / api 获取数据

### 3.3 Feature Component Layer
位于：
- `components/application/`
- `components/pipeline/`

职责：
- 承载页面内部复杂业务模块
- 表达“应用工作区”“流水线工作区”内部视图

### 3.4 Common UI Layer
位于 `components/common/`。

职责：
- 提供统一视觉和交互元素
- 避免样式与交互逻辑分散

### 3.5 Data Layer
包括：
- `api/`
- `stores/`
- `composables/`
- `types.ts`

职责：
- 访问后端 API
- 管理跨页面状态
- 提供可复用交互逻辑
- 统一数据结构定义

---

## 4. App Shell Design

## 4.1 `App.vue`
当前作为应用根节点，职责很轻：
- 渲染路由
- 挂载全局 `CommandPalette`

这保证了命令面板不会被限制在某个具体页面内部。

## 4.2 `MainLayout.vue`
这是当前最关键的前端框架组件。

承担：
- 侧边导航
- 顶部上下文标题
- 全局工作区布局
- 主题切换
- 侧边栏折叠
- AI Command 入口按钮

从产品设计角度，`MainLayout` 代表了平台的“Software OS 外壳”。

---

## 5. Routing Design

路由位于：
- `router/index.ts`

当前采用：
- 一个主布局 `MainLayout`
- 多个子页面懒加载

主要页面包括：
- `/dashboard`
- `/applications`
- `/applications/new`
- `/applications/:id`
- `/pipelines`
- `/pipelines/:name`
- `/releases`
- `/approvals`
- `/settings/registries`

这种结构适合后续继续扩展更多工作区能力，而不会破坏整体布局。

---

## 6. State Management

当前主要使用 Pinia。

### 6.1 `stores/application.ts`
职责：
- 管理应用列表
- 提供应用加载状态

### 6.2 `stores/ui.ts`
职责：
- 管理主题（light / dark）
- 管理侧边栏折叠
- 做本地持久化

### 6.3 `stores/command.ts`
职责：
- 管理 Command Palette 打开状态
- 管理当前查询词
- 管理最近使用命令

这种拆分方式是合理的：
- 业务实体状态放业务 store
- 纯界面状态放 ui store
- 全局命令交互放 command store

---

## 7. API Access Layer

位于 `api/`。

主要文件包括：
- `application.ts`
- `approval.ts`
- `pipeline.ts`
- `registry.ts`
- `release.ts`
- `client.ts`

### 7.1 `client.ts`
负责：
- Axios 实例初始化
- 统一基础地址
- 可扩展请求/响应拦截

### 7.2 API Module Pattern
每个模块按领域拆分，例如：
- Application API
- Pipeline API
- Release API

这种模式有两个好处：
1. 便于按领域维护
2. 更适合被 AI 或后续代码生成工具理解和扩展

---

## 8. Type System

位于：
- `types.ts`

定义了平台的核心前端数据结构，如：
- `Application`
- `Execution`
- `Release`
- `RuntimeStatus`
- `ApplicationEnvironment`
- `ApplicationConfig`
- `Approval`
- `ContainerRegistry`

这是前端和后端语义对齐的重要基础。

未来如果继续演进，建议进一步：
- 区分 DTO 与 UI ViewModel
- 分拆 `types.ts` 为领域模块

---

## 9. Page-Level Capabilities

## 9.1 Dashboard
职责：
- 展示全局 AI Command Hero
- 展���推荐动作
- 展示 recent activity
- 展示 health summary

它回答的问题是：

> 我现在下一步该做什么？

而不是：

> 我有哪些系统指标？

## 9.2 Application List
职责：
- 展示软件服务目录
- 支持搜索和状态筛选
- 快速进入应用工作区
- 快速触发部署

## 9.3 Application Detail
职责：
- 承载应用工作区
- 展示应用概览、环境、配置、发布、运行态
- 表达“一个应用的完整软件生命周期视图”

## 9.4 Pipeline Pages
职责：
- 全局查看执行活动
- 查看任务流、日志、失败任务
- 支持 AI 分析入口

## 9.5 Release Center
职责：
- 展示发布活动流
- 支持版本回滚入口
- 统一跨应用交付记录

## 9.6 Approvals
职责：
- 展示审批队列
- 让决策者快速批准 / 拒绝生产发布

## 9.7 Registries
职责：
- 管理平台级镜像仓库连接
- 统一交付基础设施配置

---

## 10. Feature Components

### 10.1 Application Components
位于 `components/application/`。

关键组件包括：
- `ApplicationOverview.vue`
- `EnvironmentCenter.vue`
- `ConfigurationCenter.vue`
- `ReleaseHistoryTable.vue`
- `RuntimeStatusPanel.vue`

这些组件共同定义了“应用工作��”的内部模块。

### 10.2 Pipeline Components
位于 `components/pipeline/`。

关键组件包括：
- `PipelineStatusTimeline.vue`
- `TaskRunLogViewer.vue`

它们定义了流水线诊断与日志查看体验。

### 10.3 Common Components
位于 `components/common/`。

关键组件包括：
- `PageHeader.vue`
- `MetricCard.vue`
- `StatusBadge.vue`
- `EmptyState.vue`
- `CommandPalette.vue`

这些组件统一了平台视觉语言。

---

## 11. Design System

全局样式位于：
- `styles/design-system.css`

当前已经引入：
- 主题变量（light / dark）
- 统一圆角
- 阴影与边框风格
- SaaS 风格浅色优先主题
- 通用 surface / card / code block 样式

设计目标是：
- 简洁
- calm
- developer-first
- AI-first
- premium SaaS

---

## 12. AI Command / Command Palette Architecture

这是当前前端里最接近 AI Native 的模块。

### 12.1 组成
- `stores/command.ts`
- `composables/useCommandCenter.ts`
- `components/common/CommandPalette.vue`

### 12.2 职责
- 提供全局命令入口
- 支持 `⌘K / Ctrl+K`
- 支持推荐命令与最近命令
- 支持简单参数化匹配
- 将自然语言意图映射到平台动作

### 12.3 当前限制
目前仍然是“前端命令中心��，还不是完整的后端 AI Agent。

也就是说，当前更像：
- command launcher
- intent matcher
- action router

而不是：
- full AI planner
- multi-step executor

---

## 13. Frontend Strengths

当前前端的主要优点：

1. **结构清晰**
   - views / feature components / common / stores / api 分层合理

2. **交互开始 AI Native 化**
   - 已有 Hero Command + Global Command Palette

3. **信息组织比传统后台更好**
   - 活动流、工作区、卡片、建议动作都比表格导向更贴近软件工作流

4. **状态管理简单可维护**
   - Pinia 用法克制，没有过度复杂化

5. **类型基础较完整**
   - 核心领域对象已具备 TypeScript 描述

---

## 14. Frontend Risks / Improvement Points

### 14.1 仍依赖 Element Plus 视觉底层
虽然交互层已经重构很多，但底层组件样式仍受 Element Plus 影响。

后续如要进一步提升设计统一性，可考虑：
- Tailwind
- Radix Vue
- 更轻量的自定义基础组件系统

### 14.2 Data Layer 可继续解耦
未来可逐步引入：
- query/cache 层
- 分离 command / query
- 更细的 composable 复用

### 14.3 Command Palette 仍偏静态
当前命令系统已经可用，但未来可以继续增加：
- ��览区
- 多步参数确认
- AI 建议生成
- 历史上下文记忆

### 14.4 测试体系尚不完善
建议未来加入：
- 组件测试
- 页面工作流测试
- 命令面板行为测试

---

## 15. Suggested Evolution Direction

建议前端逐步向以下方向演进：

### Phase 1
- 继续统一低层 UI 组件
- 拆分更多 composables
- 完善命令面板体验

### Phase 2
- 引入更系统的 design token
- 做真正的 AI side panel / preview panel
- 建立更完整的前端测试体系

### Phase 3
- 让前端不只是“页面系统”，而是“软件操作系统界面”
- 以命令、推荐、对话、工作区为主要交互模型

---

## 16. Summary

Aegis 前端当前已经从传统后台界面，逐步演进为：

> 一个围绕软件对象、交付动作与 AI 命令组织的 Software OS 交互层。

这使得它不只是展示后端数据，而是开始承担平台级工作流组织与 AI Native 交互入口的职责。

