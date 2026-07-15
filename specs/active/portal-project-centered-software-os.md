# 功能：Portal Project 中心化 Software OS 展示

- 状态：草稿
- 负责人：Aegis Team
- 创建日期：2026-07-15

## 背景

Portal 首页当前以大段产品说明和四层系统模型描述 Aegis。它能够说明产品定位，但不能让
研发负责人、平台工程师和交付负责人快速理解：Project 如何成为治理边界，Application
如何在该边界内完成交付，以及 Aegis 如何从 DevOps 向 Cloud Governance、FinOps 和
AIOps 演进。

## 当前行为

- `frontend/src/views/PortalHome.vue` 使用文字区块介绍 Software OS、事实层、控制层、
  执行层和智能层。
- 页面下方提供 Project Center、DevCenter 两个工作空间入口和静态生命周期步骤。
- 首页未形成 Project、Application、交付链路和未来能力域之间的可视关系。

## 目标行为

Portal 首屏使用一张以 Project 为核心的 Software OS 能力地图替代现有文字概览：

1. Project 是统一治理上下文，承载成员、Application、Kubernetes、Registry、环境、
   配置和交付历史。
2. DevOps、FinOps、AIOps、Cloud Governance 四个能力域从 Project 向外展开。
3. DevOps 作为当前主要可用能力，展示 Application 从提交、构建到多环境晋级和生产
   审批的真实主链路。
4. Aegis Intelligence 横跨各能力域，表达上下文建议、风险解释和辅助决策；所有生产或
   破坏性动作仍由人确认或审批。
5. 能力必须明确标注“已可用”“演进中”或“规划”，不能把产品愿景表达成已上线功能。

## 范围

- 包含：重构 Portal 首页核心概览区的信息架构、视觉层级和响应式布局。
- 包含：展示通用 Project 治理模型，不硬编码具体客户、组织或项目名称。
- 包含：展示四个能力域及其能力状态。
- 包含：保留 Project Center 和 DevCenter 的可达入口。
- 包含：使用仓库现有设计变量、图标风格和浅色企业软件视觉语言。
- 包含：为关键展示数据和状态配置前端静态模型，便于后续替换为真实摘要接口。

## 非目标

- 不包含：新增 FinOps、AIOps 或阿里云资源初始化的后端实现。
- 不包含：宣称已实现监控告警生命周期、自主修复、自主生产发布或真实成本数据。
- 不包含：新增 Portal 摘要 API。
- 不包含：改变 Project Center、DevCenter 或 Application 工作空间的业务行为。
- 不包含：硬编码 `OTR` 或其他具体业务项目名称。

## 能力表达

### Project 核心

Project 作为能力地图中心，使用通用标签“Project 治理上下文”，呈现其连接的软件对象和
资源类型，不展示来源不明的真实数量。它向四个能力域提供同一份组织、交付、资源、成本
和运行上下文。

### DevOps · 已可用

- Application 与代码仓库。
- Build once / Promote：一次构建，多环境晋级。
- 环境、配置、Pipeline、Release 和生产审批。
- Kubernetes 运行态检查。

### Cloud Governance · 部分可用 / 规划

- 已可用：Kubernetes 接入、Registry 接入和 Project 级绑定。
- 规划：阿里云资源组、ACK 初始化、VPC 治理和外部权限同步。

### FinOps · 规划

- Project 成本归集。
- 预算与趋势。
- 环境成本对比。

页面不得展示虚构金额、趋势或实时成本数据。

### AIOps · 演进中

- 已有基础：运行态检查、确定性意图识别。
- 演进方向：运行态理解、异常关联和变更影响分析。

页面不得暗示已经具备完整监控、告警、事件生命周期或自主修复能力。

### Aegis Intelligence

智能层连接 Project 事实、交付上下文、资源上下文、未来成本信号和运行状态，输出上下文
建议、风险解释和辅助决策。视觉上使用贯穿各域的连接轨迹，而不是独立聊天窗口。明确展示
“人确认后执行”。

## 交互与响应式

- 桌面端以 Project 为视觉中心，四个能力域围绕或从中心展开；DevOps 信息层级最深。
- 能力域可使用悬停或键盘聚焦强化对应连接关系，但不依赖交互才能读懂状态。
- 工作空间入口继续可点击，行为保持现状。
- 窄屏按 Project、DevOps、Cloud Governance、FinOps、AIOps、Intelligence 顺序纵向排列。
- 状态不能只依赖颜色；同时显示文字标签并使用实线、虚线或点线等辅助编码。

## 验收条件

- [ ] 给定用户打开 Portal 首页，当查看首屏时，则能识别 Project 是统一治理边界。
- [ ] 给定用户查看能力地图，当浏览四个能力域时，则能区分 DevOps、FinOps、AIOps 和
      Cloud Governance，并理解它们与 Project 的关系。
- [ ] 给定用户查看 DevOps 域，当阅读交付链路时，则能理解 Commit、Build once、
      多环境 Promote 和生产审批。
- [ ] 给定用户查看能力状态，当能力尚未实现时，则页面明确显示“演进中”或“规划”。
- [ ] 页面不出现 `OTR` 或其他硬编码业务项目名，不展示虚构成本和运行数据。
- [ ] Aegis Intelligence 表达辅助决策，并明确生产操作需要人工确认。
- [ ] Project Center 和 DevCenter 入口行为保持可用。
- [ ] 桌面和移动布局无溢出、遮挡或不可读文本，键盘焦点清晰。
- [ ] 前端类型检查和生产构建通过，`./scripts/verify.sh` 通过。
- [ ] `docs/current-state.md` 只记录最终实现的展示能力，不把规划能力写成已实现。

## 设计说明

采用“核心—能力域—落地链路”三层信息架构：

- 核心：Project 治理上下文。
- 能力域：DevOps、FinOps、AIOps、Cloud Governance。
- 落地链路：DevOps 内展开 Application 的真实交付流程。

视觉延续现有浅色企业软件风格，以 Aegis 蓝表示 Project 与 DevOps，以青色、橙色、紫色
区分 Cloud Governance、FinOps 和 AIOps。Aegis Intelligence 使用克制的蓝紫连接轨迹。
已可用能力采用实线与实色状态，演进中采用虚线，规划采用点线和弱化表面。

备选方案包括只展示 Application 交付链路，以及四域等权卡片网格。前者无法表达 Project
和平台愿景；后者容易退化为功能清单，因此不采用。

## 验证证据

实现过程中补充类型检查、构建、完整验证和浏览器截图对比结果。

## 完成

验收后将状态改为“已验收”，记录日期，并把文件移至 `specs/completed/`。
