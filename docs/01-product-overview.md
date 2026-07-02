# 01. Product Overview

## 1. Product Name

**Aegis**

当前可以理解为一个：

> 面向中小到中型研发团队的 AI Native DevOps Platform / Software Operating System。

它不是传统意义上的“运维后台”，而是一个围绕 **软件交付生命周期** 组织的工作平台。

---

## 2. Product Vision

Aegis 的目标不是成为另一个复杂的 DevOps 控制台，而是成为：

- 让开发者更自然地发布软件
- 让平台更自动地识别项目、生成流水线与部署配置
- 让环境、配置、发布、审批、运行状态都被统一建模
- 让 AI 可以参与软件交付与运行操作

一句话概括：

> 让团队通过更少的配置、更少的点击、更多的自动化和更强的 AI 理解，完成软件从代码到运行的交付过程。

---

## 3. Problem Statement

传统 DevOps 平台经常存在以下问题：

1. **系统割裂**
   - 代码仓库、流水线、镜像仓库、Kubernetes、发布记录、审批流程分散在不同工具中。

2. **操作复杂**
   - 开发者需要理解过多基础设施细节，才能完成一次部署或定位一次失败。

3. **配置负担重**
   - 环境配置、资源限制、镜像路径、流水线参数通常需要手工维护。

4. **认知成本高**
   - 大量表格、字段、状态、资源对象并不能直接回答“我现在该做什么”。

5. **AI 无法真正介入**
   - 缺少结构化平台上下文，导致大模型难以对真实系统做出可靠建议或操作映射。

Aegis 尝试解决的核心问题是：

> 如何把软件交付过程，从一套工具拼装，变成一个统一、结构化、可自动化、可 AI 理解的软件操作系统。

---

## 4. Core Product Positioning

当前平台的核心定位可以拆解为五层：

### 4.1 Application-Centric
Aegis 以 **Application** 作为中心对象，而不是以集群资源、流水线资源或容器镜像作为中心对象。

平台关心的是：
- 一个应用来自哪个仓库
- 它是什么语言/框架
- 它怎么构建
- 它如何部署到多个环境
- 它最近的交付状态如何
- 它的配置、版本、审批与运行态如何统一管理

### 4.2 Git-to-Delivery
平台从 Git 仓库出发：
- 自动识别项目类型
- 生成 Application Spec
- 选择合适的 Tekton Pipeline 模板
- 触发镜像构建与部署

### 4.3 Multi-Environment Delivery
平台原生支持：
- `dev`
- `test`
- `staging`
- `prod`

每个环境都有自己独立的：
- namespace
- 副本数
- 资源限制
- ingress 域名
- 发布策略
- 是否需要审批

### 4.4 Governed Production Delivery
生产环境交付不是无条件直接执行，而是支持：
- 提交审批申请
- 审批通过后继续执行
- 审批拒绝后阻断发布
- 审计记录保留

### 4.5 AI-Native Interface
平台正在逐步演进为：
- 不是让用户“找功能”
- 而是让用户“表达意图”

例如：
- Deploy payment service
- Rollback order service
- Show production incidents
- Create application workspace

这也是当前前端引入全局 Command Palette 的核心背景。

---

## 5. Current Capability Scope

截至当前代码状态，平台已经具备的能力包括：

### 5.1 应用接入
- 从 Git 仓库创建应用
- 自动识别语言、框架、构建方式
- 生成统一 Application Spec

### 5.2 流水线与部署
- 基于 Tekton 创建 PipelineRun
- 支持 Java / Node.js / Dockerfile 类型项目
- 通过 Kaniko 构建镜像并推送到 Registry
- 部署到 Kubernetes

### 5.3 多环境管理
- 创建、编辑、克隆环境
- 按环境管理资源、命名空间与部署策略
- 支持环境配置对比

### 5.4 配置管理
- 按环境维护配置项
- 区分 env / configmap / secret / resource / ingress
- 支持版本化变更记录

### 5.5 发布与回滚
- 查看发布历史
- 统一发布活动流
- 从历史版本回滚

### 5.6 运行状态查看
- 查看 Deployment / Service / Ingress
- 查看 Pod 状态
- 查看 K8s Events
- 查看 Pod 日志与 YAML

### 5.7 审批治理
- 提交生产审批
- 批准 / 拒绝
- 关联 Pipeline 执行链路

### 5.8 镜像仓库管理
- 管理 ACR / Harbor / DockerHub / ECR / GCR / Generic OCI Registry
- 默认 Registry 策略
- 平台级凭据管理

### 5.9 AI Native UI 能力
- 全局 AI Command / Command Palette
- 推荐命令
- 最近使用命令
- 参数化基础意图匹配

---

## 6. Capability Boundary

平台当前明确**不包含**或**尚未完整实现**的能力：

### 6.1 监控与告警平台
当前不替代完整 observability 平台，例如：
- Prometheus
- Grafana
- Loki
- Alertmanager

### 6.2 Service Mesh / Advanced Traffic
当前未覆盖：
- 蓝绿 / 金丝雀流量治理
- Istio / Linkerd 级别的服务网格能力

### 6.3 全自动 AI Agent 执行链路
当前前端已有 AI 命令界面，但后端 AI Agent 仍处于：
- 预留接口
- 提示入口
- 能力雏形

并未完全形成：
- 意图解析
- 计划生成
- 风险评估
- 执行确认
- 自动闭环

### 6.4 企业级多租户治理
当前数据模型更接近单平台 / 单团队演示形态，尚未完整实现：
- 多租户隔离
- 组织/项目/团队权限模型
- 细粒度 RBAC

---

## 7. Target Users

### 7.1 Platform Engineers
需要统一管理流水线模板、镜像仓库、环境基线与部署流程。

### 7.2 Backend / Fullstack Developers
希望从代码仓库快速完成：
- 接入
- 构建
- 发布
- 状态查看
- 回滚

### 7.3 Tech Leads / Delivery Owners
关心：
- 现在有哪些应用在运行
- 最近哪些发布失败
- 哪些生产变更等待审批
- 当前应该优先处理什么

### 7.4 AI Agents / Coding Assistants
需要一份结构化平台上下文，以便：
- 理解系统边界
- 生成功能代码
- 分析部署问题
- 给出配置建议

---

## 8. Product Philosophy

Aegis 不应该成为：
- 传统运维门户
- 单纯的流水线面板
- Kubernetes 资源浏览器
- 另一个“后台系统”

Aegis 应该逐步成为：

> 一个围绕软件对象、交付动作和运行状态组织的 Software OS。

这意味着它的 UX、架构和 AI 能力都应该围绕以下原则展开：

- 应用优先，而不是资源优先
- 决策优先，而不是配置优先
- 工作流优先，而不是页面优先
- 意图优先，而不是功能入口优先
- 软件工程上下文优先，而不是底层基础设施术语优先

---

## 9. Near-Term Evolution Direction

Aegis 下一阶段可以继续朝以下方向演进：

1. **真正的 AI Agent 执行闭环**
2. **多步命令与参数化操作**
3. **配置建议与发布风险评估**
4. **更完善的项目 / 团队 / 权限体系**
5. **更系统的监控与运行诊断能力**
6. **更多语言和构建类型支持**

---

## 10. Summary

Aegis 当前已经不是一个简单的 CRUD DevOps Demo，而是一个具备以下雏形的平台：

- 有统一中心对象（Application）
- 有完整交付链路（Git → Tekton → Kaniko → K8s）
- 有环境与配置建模
- 有发布、审批、运行状态与回滚链路
- 有 AI Native 前端交互起点

它当前最适合被定义为：

> 一个面向容器化应用交付场景的 AI Native DevOps Platform / Software OS MVP。

