# 03. Domain Model

## 1. Purpose

本文件从软件工程与领域建模的角度，描述 Aegis 平台中的核心业务对象、对象关系、对象生命周期，以及这些对象在系统中的职责边界。

Aegis 当前最核心的领域思想是：

> 用 `Application` 作为软件交付的主聚合根，将环境、配置、发布、审批、流水线和运行态统一组织在应用上下文内。

---

## 2. Core Domain Objects

当前平台的核心对象包括：

1. `Application`
2. `ApplicationEnvironment`
3. `ApplicationConfig`
4. `PipelineExecution`
5. `ReleaseRecord`
6. `ApprovalRecord`
7. `ContainerRegistry`
8. `Project`

其中最关键的是前六个。

---

## 3. Application

## 3.1 Definition

`Application` 代表平台中的一个“软件服务”或“交付对象”。

它不是 Kubernetes Deployment 的简单镜像，也不是 Git 仓库的简单映射，而是：

- 一个软件交付单元
- 一个运行工作区
- 一个与环境、配置、发布和审批关联的业务中心对象

## 3.2 Key Responsibilities

`Application` 负责承载：
- 代码来源
- 技术栈识别结果
- 统一 Application Spec
- 默认部署信息
- 最近一次交付状态

## 3.3 Typical Fields

典型字段包括：
- `name`
- `repo_url`
- `branch`
- `language`
- `framework`
- `build_type`
- `namespace`
- `image_name`
- `image_tag`
- `port`
- `status`
- `application_spec`

## 3.4 Relationships

一个 `Application` 通常拥有：
- 多个 `ApplicationEnvironment`
- 多个 `ApplicationConfig`
- 多个 `ReleaseRecord`
- 多个 `PipelineExecution`
- 多个 `ApprovalRecord`

---

## 4. ApplicationEnvironment

## 4.1 Definition

`ApplicationEnvironment` 表示一个应用在某个环境中的交付与运行配置。

环境是 Aegis 中非常关键的二级上下文，因为同一个应用在不同环境中的配置天然不同。

## 4.2 Responsibilities

它负责定义：
- 目标 namespace
- 副本数
- CPU / Memory 请求与限制
- Ingress 域名
- 发布策略
- 是否需要审批
- 当前环境状态

## 4.3 Examples

典型环境包括：
- `dev`
- `test`
- `staging`
- `prod`

## 4.4 Why It Matters

环境对象的存在，使平台不必把所有配置堆在 `Application` 上，而是能以“应用 × 环境”的方式表达交付差异。

---

## 5. ApplicationConfig

## 5.1 Definition

`ApplicationConfig` 表示一个应用在某个环境中的配置条目。

它用于统一描述：
- 环境变量
- ConfigMap
- Secret
- 资源配置
- Ingress 配置

## 5.2 Responsibilities

它负责：
- 保存配置内容
- 保存配置类型
- 保存变更人和版本
- 区分 Secret 与非 Secret
- 为未来配置历史审计提供基础

## 5.3 Key Value

`ApplicationConfig` 的最大价值不是“存一条配置”，而是：

> 把应用运行配置从零散输入，提升为可版本管理、可环境隔离、可追踪的领域对象。

---

## 6. PipelineExecution

## 6.1 Definition

`PipelineExecution` 表示一次流水线执行记录。

它是交付动作的执行轨迹，但不是业务层面最终的“发布事实”。

## 6.2 Responsibilities

它负责表达：
- `pipeline_run_name`
- Tekton 状态
- 执行时间
- 执行阶段
- 最近执行结果

## 6.3 Design Note

在 Aegis 中：
- `PipelineExecution` 更偏“执行过程对象”
- `ReleaseRecord` 更偏“业务交付结果对象”

这两者相关，但不完全等价。

---

## 7. ReleaseRecord

## 7.1 Definition

`ReleaseRecord` 是平台中非常关键的业务对象。

它表示：

> 一次可审计、可查询、可回滚的软件版本交付结果。

## 7.2 Responsibilities

它负责记录：
- 发布类型（deploy / rollback）
- 目标环境
- 镜像与标签
- 触发用户
- 对应 PipelineRun
- 发布状态
- 发布时间
- 错误信息

## 7.3 Why Not Only Pipeline

因为流水线是执行技术细节，而发布记录是业务事实。

业务更关心：
- 哪个版本进了哪个环境
- 是谁发的
- 是否成功
- 是否需要回滚

而不是单纯关心 Tekton 对象本身。

---

## 8. ApprovalRecord

## 8.1 Definition

`ApprovalRecord` 表示一个需要人工治理判断的发布请求。

它主要用于生产环境发布。

## 8.2 Responsibilities

它负责记录：
- 哪个应用提出发布请求
- 目标环境与 namespace
- 目标镜像
- 申请人
- 审批人
- 审批状态
- 审批意见
- 审批完成时间
- 审批后关联的 PipelineRun

## 8.3 Business Meaning

它把“治理”纳入交付链路，而不是让生产发布成为无条件自动执行动作。

---

## 9. ContainerRegistry

## 9.1 Definition

`ContainerRegistry` 表示平台可用的镜像仓库连接。

## 9.2 Responsibilities

它负责：
- 保存 Registry 地址
- 保存 provider 类型
- 保存用户名 / 密码 / Token
- 保存默认 namespace / project
- 标识默认 Registry
- 标识启用状态

## 9.3 Architectural Importance

Registry 之所以是独立领域对象，是因为镜像构建与部署都依赖它，并且平台希望实现：
- 平台级默认仓库
- 应用自动继承
- 凭据统一管理

---

## 10. Project

`Project` 当前更像保留能力，用于未来：
- 按项目组织应用
- 按团队管理边界
- 支持更强的 RBAC 和工作空间划分

在当前代码状态中，它还不是最核心对象，但从软件工程角度是合理的预留。

---

## 11. Domain Relationship Diagram

```text
Project
  └── Application
        ├── ApplicationEnvironment (1..n)
        │      └── ApplicationConfig (1..n)
        ├── PipelineExecution (1..n)
        ├── ReleaseRecord (1..n)
        └── ApprovalRecord (1..n)

ContainerRegistry
  └── referenced by Application / Tekton / Kubernetes delivery flow
```

---

## 12. Aggregate and Boundary Thinking

从领域驱动设计视角，可做如下理解：

### 12.1 Primary Aggregate Root
当前最适合被视为主聚合根的是：

- `Application`

因为：
- 绝大多数核心操作都围绕应用发生
- 环境、配置、发布、审批都与应用直接关联
- 应用是用户最自然的心智对象

### 12.2 Secondary Aggregates
次级聚合可视为：
- `ApplicationEnvironment`
- `ReleaseRecord`
- `ApprovalRecord`
- `ContainerRegistry`

### 12.3 Execution vs Business State
Aegis 有一个非常重要的边界区分：

#### 执行态对象
- PipelineExecution
- Tekton PipelineRun
- Pod / Deployment / Events

#### 业务态对象
- Application
- ReleaseRecord
- ApprovalRecord
- ApplicationConfig
- ApplicationEnvironment

这使得系统不会被底层 K8s 资源结构绑死，而是能保留更稳定的平台业务语义。

---

## 13. Domain Lifecycle

### 13.1 Application Lifecycle
```text
Created
  → Analyzed
  → Deployable
  → Running / Failed / Pending
```

### 13.2 Environment Lifecycle
```text
Initialized
  → Configured
  → Updated
  → Cloned / Deleted
```

### 13.3 Release Lifecycle
```text
Requested
  → Pipeline Started
  → Succeeded / Failed
  → Rolled back (optional)
```

### 13.4 Approval Lifecycle
```text
Pending
  → Approved
  → Pipeline Continues
or
Pending
  → Rejected
  → Release Blocked
```

---

## 14. Domain Invariants (Conceptual)

从工程设计角度，平台应该逐步确保以下不变量：

1. 一个应用必须至少有一个环境
2. 一个发布记录必须关联明确的应用与目标环境
3. 生产环境若要求审批，则不能绕过审批直接发布
4. Secret 配置必须可区分为加密存储
5. 回滚必须只能针对有效的历史发布记录进行
6. 默认 Registry 在任意时刻最多只能有一个

这些规则有些当前代码已部分实现，有些仍适合在后续版本继续强化。

---

## 15. Domain Evolution Suggestions

未来如要继续提升领域模型，可考虑：

### 15.1 引入 DeliveryPlan / DeploymentIntent
把“用户想发布什么”与“系统如何执行”分离开来。

### 15.2 引入 Incident / Recommendation
让 AI 对失败执行和运行异常的分析结果成为正式领域对象。

### 15.3 引入 Workspace / Team / Permission Model
支持更大规模协作和权限治理。

### 15.4 引入 Versioned Application Spec
让 Application Spec 自身也可成为可比较、可审计的对象。

---

## 16. Summary

Aegis 当前的领域建模已经具备一个不错的软件平台雏形：

- `Application` 作为核心聚合根
- `Environment` 与 `Config` 作为配置化交付上下文
- `Release` 与 `Approval` 作为业务交付事实
- `PipelineExecution` 与 K8s 状态作为执行层观测对象

这种设计让平台既能对接基础设施执行面，又能维持稳定的软件工程语义，是它演进为 Software OS 的重要基础。

