# 09. Engineering Roadmap

## 1. Purpose

本文件描述 Aegis 的工程演进方向，用于统一：
- 产品演��预期
- 架构优化方向
- 技术债治理顺序
- AI Native 能力建设路线

它不是纯产品路线图，也不是纯技术 TODO，而是站在软件工程角度描述平台从 MVP 到更成熟形态的升级路径。

---

## 2. Current Stage Assessment

当前 Aegis 最适合被定义为：

> 一个已经跑通核心交付闭环的 AI Native DevOps Platform MVP。

它已经具备：
- 应用接入
- 仓库分析
- 多环境建模
- 配置管理
- Tekton 流水线触发
- 发布记录与回滚
- 审批流
- 运行态查看
- AI Native 前端交互起点

但它还没有完全进入：
- 大规模平台治理
- 完整 AI Agent 执行闭环
- 企业级运维可观测性
- 高成熟度工程体系

---

## 3. Phase-Based Roadmap

## Phase 1 — Stabilize the Platform MVP

目标：
- 让现有系统更稳定、更可维护、更容易协作开发。

### 3.1 Backend
- 进一步明确 Service 边界
- 补充更清晰的 DTO / schema 层
- 完善错误码和异常路径
- 提升测试覆盖率

### 3.2 Frontend
- 统一剩余基础组件与交互风格
- 继续优化 Command Palette
- 减少传统 admin dashboard 模式残留
- 增加组件 / 页面测试

### 3.3 Repo Hygiene
- 完善 `.gitignore`
- 保持 build artifact 不��库
- 规范 README / docs / commit message

### 3.4 Outcome
- 成为一个“工程上可靠的 MVP”
- 能支持多人协作开发和稳定演示

---

## Phase 2 — Strengthen Delivery Workflows

目标：
- 让交付链路更完整、更可追踪、更适合真实团队使用。

### 3.5 Delivery Enhancements
- 支持更多语言与构建方式（Python / Go / Rust 等）
- 更智能地识别或生成 Dockerfile
- 支持更丰富的部署策略
- 增加发布前检查与风险提示

### 3.6 Approval & Governance
- 更细粒度的审批策略
- 审批模板与审批规则
- 审批与发布记录联动增强

### 3.7 Release Management
- 版本对比
- 发布 diff 视图
- 回滚预检查
- 更完整的交付审计链路

### 3.8 Outcome
- 平台从“能发”升级到“能安全地发、可治理地发”

---

## Phase 3 — Introduce Real AI-Assisted Workflows

目标：
- 让 AI 不只是一个 UI 命令入口，而是进入平台工作流本身。

### 3.9 AI Intent Resolution
- 增加自然语言意图解析 API
- 把用户命令转成平台动作计划

### 3.10 AI Recommendations
- 发布建议
- 故障优先级排序
- 配置优化建议
- 环境差异风险提示

### 3.11 AI Runtime Analysis
- Pipeline 失败日志分析
- Kubernetes 事件归因
- 常见错误模式识别

### 3.12 AI Safety Model
- 人工确认步骤
- 风险操作白名单 / 黑名单
- AI 只建议，不直接执行（初期）

### 3.13 Outcome
- 从“AI-friendly UI”升级到“AI-assisted platform workflows”

---

## Phase 4 — Evolve into a Software OS

目标：
- 从 DevOps 平台升级为真正的软件操作系统。

### 3.14 Unified Workspace
- 应用工作区
- 发布工作区
- 运行工作区
- 治理工作区
- AI 工作区

### 3.15 Project / Team / Multi-Tenant Model
- Project 归属
- Team 隔离
- Permission model
- Workspace scope

### 3.16 Knowledge & Memory
- 平台知识库
- AI Memory
- 常见问题知识沉淀
- 运维与交付经验积累

### 3.17 System of Record Expansion
从只记录部署事实，扩展为记录：
- 软件定义
- 环境定义
- 配置变更
- 交付轨迹
- 运行事件
- AI 建议与执行记录

### 3.18 Outcome
- 平台从“交付系统”升级为“Software Operating System”

---

## 4. Key Engineering Priorities

如果只按优先级选择几个最值得做的方向，建议顺序如下：

### Priority 1
- 文档体系完善
- 测试补齐
- 后端 Service 边界优化
- 前端命令系统继续增强

### Priority 2
- 发布风险分析
- 配置建议系统
- 审批与回滚增强
- 更多构建类型支持

### Priority 3
- AI Agent 后端执行链路
- 多租户与权限模型
- 更系统的监控/告警能力

---

## 5. Technical Debt Register

当前值得特别关注的技术债：

### 5.1 Backend
- Service 层职责仍偏重
- API schema 契约还不够显式
- 测试覆盖有限

### 5.2 Frontend
- 仍依赖 Element Plus 作为底层组件体系
- 部分页面仍可进一步从“管理页”进化为“工作区”
- chunk 体积偏大，仍有性能优化空间

### 5.3 Platform Ops
- observability 能力较弱
- security hardening 仍需补强
- 生产 RBAC 粒度仍应收敛

---

## 6. Documentation Roadmap

文档本身也应作为工程路线的一部分。

建议维持以下机制：
- 每次架构升级同步更新 `docs/`
- 新增核心 API 同步更新 `07-api-design.md`
- AI 能力升级同步更新 `08-ai-context-prompt.md`
- 每个大版本更新 `09-engineering-roadmap.md`

---

## 7. Success Indicators

判断平台是否进入下一阶段，可以参考以下信号：

### MVP Stabilized
- 本地 / 集群部署流程稳定
- 核心工作流可重复演示
- 文档与测试足够支撑协作

### Delivery Platform Matured
- 支持多团队真实使用
- 发布、审批、回滚更可靠
- 常见故障定位时间缩短

### AI Workflow Ready
- 用户可通过自然语言完成高频操作
- AI 建议可被解释、可被确认、可被追踪

### Software OS Stage
- 平台不只是“部署工具”，而成为团队的软件工作入口

---

## 8. Summary

Aegis 的工程演进路径可以概括为：

```text
MVP
  → Stable Delivery Platform
  → AI-Assisted Platform
  → Software Operating System
```

当前平台已经站在一个很好的起点上：
- 核心对象清晰
- 交付链路闭环
- 前端已开始 AI Native 化

接下来最重要的工作，不是盲目扩功能，而是：

> 在保持核心模型稳定的前提下，持续增强交付可靠性、AI 能力和工程可维护性。

