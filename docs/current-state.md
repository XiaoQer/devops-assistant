# 当前状态

最近审计：2026-07-14

本文件用于区分经过验证的仓库事实与产品愿景。

## 仓库中已经实现

- 基于 Vue 3、TypeScript、Pinia、Vue Router、Element Plus 和 Vite 的前端。
- Portal、项目中心和开发中心导航。
- Portal 将 Aegis 定位为 Software OS，介绍统一软件上下文、事实层、控制层、
  执行层和智能层，并提供项目治理与应用交付两个工作空间入口。
- 项目 CRUD、成员管理、Kubernetes 集群管理和项目级镜像仓库。
- Project 本体保存治理和外部资源绑定元信息，包括业务负责人、成本负责人、GitHub
  组边界、仓库默认可见性、Aliyun 账号、资源组、区域、VPC 和绑定状态。
- Project 列表默认隐藏系统兜底 Project；Project 详情页按基础信息、Owner、GitHub
  和 Aliyun 分类展示 Project 本体治理元信息，并支持分类进入编辑态。详情页使用
  后台详情摘要栏、单列设置面板和关联资源列表呈现，Project Name 和 Project Key 在详情页只读。
  Kubernetes 集群和 Registry 已在 Project Center 中作为独立项目级菜单管理，成员和应用
  不再嵌入 Project 详情页。
- Project Center 提供统一的浅色紧凑弹窗表单样式基座，Kubernetes 集群和 Registry
  新增/编辑弹窗已接入统一 Dialog/Form 样式。
- Project 的 Registries 页面支持 ACR、Harbor、Docker Hub、ECR、GCR、GHCR 和
  Generic OCI 配置；用户名和 Token 为必填，Token 加密保存且不通过 API 回显。新增/编辑
  表单可使用当前内容预检，资源卡片可对已保存配置复测，并记录未测试、已连接或失败状态、
  最近测试时间和脱敏消息。
- Registry 连通性测试访问 HTTPS OCI `/v2/`，支持 Basic 和 Bearer Challenge；显式跳过
  TLS 校验时持续显示风险。连接前拒绝 HTTP、loopback、link-local、云元数据等危险目标，
  并把实际连接固定到已校验地址，避免 DNS 重绑定绕过。测试不执行镜像推拉。
- Project 的 Kubernetes 页面提供“初始化新集群”和“添加已有集群”两个入口；Aliyun
  初始化仅展示为即将支持，已有集群支持粘贴完整 kubeconfig、选择 context、设置内置或
  自定义单值环境标签，并在保存前或保存后测试 Kubernetes Version API 连通性。
- Project 的 Kubernetes 页面在宽屏使用双列资源卡片并在窄屏自动切换单列；API Server、
  Context、连接状态和最近测试时间按层级呈现，测试与编辑保持直接可见，默认设置和删除收纳
  到更多操作菜单。添加/编辑弹窗按基本信息、连接配置和治理设置分区展示。
- 集群 kubeconfig 使用由服务端 `SECRET_KEY` 派生的 Fernet 密钥加密保存，API 仅返回
  `has_kubeconfig`；连通性测试记录脱敏状态、时间、Kubernetes 版本和成功发现的 API Server，
  并拒绝 `exec` 认证、本地凭据文件引用、非 HTTPS Server 和超过 1 MiB 的配置。
- 基于代码仓库创建应用，并分析 Java、Node.js 或 Dockerfile 项目。
- 应用环境和配置的增删改查、克隆、比较与导出。
- Application Environment 配置中心支持按环境管理环境变量、ConfigMap、Secret、资源参数
  和 Ingress；配置值加密保存并在目标环境发布时物化为 Kubernetes 配置资源和工作负载参数。
- 部署计划、Tekton PipelineRun 创建、重试、结构化状态和日志。
- Application 构建版本与 Build once/Promote 流程：Build Pipeline 只构建并推送镜像，发布使用已成功构建版本执行 Deploy-only Pipeline；同一构建版本可连续发布到多个环境，生产发布审批关联具体构建版本。
- Application 发布批次支持从公共 Git 仓库切换分支，读取最近 20 条提交，选择一个提交并多选环境；一次 Build Pipeline 产出构建版本，Delivery Reconciler 按环境 fan-out Deploy-only PipelineRun，复用同一镜像并独立记录环境状态，生产环境审批只阻断对应目标。
- 发布历史、回滚流程和交付状态同步。
- Application Environment 已解析为 Project 交付上下文：环境由用户在 Application 工作区
  中显式创建、编辑和删除，不再自动补建 dev；已绑定且连接成功的 Kubernetes 集群作为唯一
  目标客户端，Project 默认且连接成功的 Registry 作为构建镜像地址；未测试、失败、停用或
  跨 Project 的上下文会在发布计划和审批执行时阻断。
- 第一阶段中央 Tekton 构建并部署：目标 kubeconfig 以 Project/Cluster 确定性命名 Secret
  幂等物化到中央 Tekton Namespace，只有 deploy Task 以只读方式挂载并显式指定 kubeconfig
  路径和 context；目标配置写入目标集群，中央集群只保存 Tekton 与构建 Registry Secret。
- 审批提交、批准和拒绝流程。
- Kubernetes 运行状态、Pod 日志和 Pod YAML 接口。
- 面向少量平台命令、基于规则的 AI 意图识别。
- Alembic migration 以及 Kubernetes/Tekton 部署清单。
- 基础身份认证：通过环境变量非交互初始化预置管理员，使用安全密码哈希和数据库会话；
  会话 Cookie 为 HttpOnly，非只读请求执行 CSRF 校验。
- 除健康检查和登录外的 API 全局认证保护，以及登录页、前端路由保护、会话恢复、
  401 处理和退出流程。
- 部署、回滚、审批和配置写操作从服务端验证的当前用户取得可信操作人，不再接受
  `X-User` 请求头作为身份来源。
- 覆盖核心 Service 和校验路径的后端单元测试与路由测试。

## Harness 基线验证结果

- `./scripts/verify.sh` 于 2026-07-13 执行成功。
- 后端 127 个测试全部通过。
- 前端类型检查和生产构建通过。
- 后端测试产生 68 条警告：24 条 Flask-SQLAlchemy `get_engine()` 弃用警告和
  44 条 SQLAlchemy `Query.get()` 旧 API 警告。
- 前端构建转换 1802 个模块并成功产出生产包；Rollup 报告 2 条依赖注释位置提示，
  并报告一个超过 500 kB 的 JavaScript 分包。这些是构建警告，不是构建失败。
- 独立的临时 SQLite 自动迁移测试完成 `f1a2b3c4d5e6` stamp、升级到
  `a7c8d9e0f1a2` 并降级回 `f1a2b3c4d5e6`；未对用户数据库执行降级。
- 独立的临时 SQLite 自动迁移测试完成 `a7c8d9e0f1a2` stamp、升级到
  `c3d4e5f6a7b8` 并降级回 `a7c8d9e0f1a2`；未对用户数据库执行降级。
- 独立的临时 SQLite 自动迁移测试完成 `c3d4e5f6a7b8` stamp、升级到
  `d4e5f6a7b8c9` 并降级回 `c3d4e5f6a7b8`，并验证既有集群记录保留；未对用户数据库
  执行降级。
- 独立的临时 SQLite 自动迁移测试完成 `d4e5f6a7b8c9` stamp、升级到
  `e5f6a7b8c9d0` 并降级回 `d4e5f6a7b8c9`，并验证既有 Registry 记录保留且连接字段
  默认值正确；未对用户数据库执行降级。
- 人工浏览器验收于 2026-07-08 使用本地 MySQL 开发库完成：未登录业务路由跳转登录
  并保留原目标，登录后回到项目中心，刷新后恢复会话，退出登录回到登录页，退出后
  再访问业务路由仍被保护。

## 部分实现或过渡中的能力

- 项目级路由与旧的全局路由并存。
- 模型中存在项目成员角色，但尚未用于强制 API 鉴权。
- Project 已保存 GitHub 和 Aliyun 绑定元信息，但尚未调用 GitHub 或 Aliyun API
  初始化外部资源，也尚未同步项目成员权限。
- Kubernetes 集群已能以 Project 子资源安全接入和测试；Application Environment 的多集群
  部署目标、运行客户端切换和中央 Tekton kubeconfig 挂载已在第一阶段实现，前端交付体验
  和构建/部署拆分仍可继续完善。
- AI 意图识别是确定性的关键词匹配，不是 LLM 规划器或自主执行闭环。
- 已支持运行态检查，但尚不支持监控、告警和事件生命周期管理。
- Service 已有基本边界，但部分仍混合编排、持久化和基础设施访问。
- 本地 Schema 修复代码与 Alembic 并存，不应成为常规生产迁移方式。

## 已知工程缺口

- 增加前端组件和工作流测试。
- 增加强制性的架构与 Secret 边界自动检查。
- 替换已弃用的 SQLAlchemy `Query.get()` 调用。
- 缩小或有计划地拆分过大的前端包。
- 通过明确的迁移规格解决旧导航和项目级导航并存问题。
- 身份认证不包含公开注册、邀请、密码找回或修改密码，也不包含 SSO、OAuth/OIDC、
  MFA、API Key、RBAC 或项目成员角色强制授权。
- 登录端点没有网关或共享存储支持的分布式限流；当前能力不是生产级身份系统。
- Project 级 GitHub team/repo 初始化、Aliyun 资源组/ACK 初始化和外部权限同步尚未实现。
- 个别持久化模型和 Service 仍保留 `local-user` 作为内部字段默认值；HTTP 路由已
  使用可信认证用户，但这些遗留默认值仍需在后续迁移中清理。
- 加强生产安全、备份、可观测性和 RBAC。

## 下一个 Harness 里程碑

完善 Delivery Reconciler 的后台调度与重试：当前已提供按发布批次触发的协调逻辑，后续接入
常驻 worker/定时任务，继续逐步移除中央集群中的持久 kubeconfig Secret。
