# 功能：Project 作用域 Application 多集群交付

- 状态：第一阶段已实现
- 负责人：Aegis Team
- 创建日期：2026-07-14

## 背景

Project 已经能够管理成员、Kubernetes 集群和 OCI Registry。Application 也已经具备
仓库分析、环境配置、Tekton PipelineRun、发布审批、运行状态和回滚等基础能力，但这些
能力尚未形成完整的 Project 治理闭环：Application API 仍有全局入口，Environment 绑定
的 Kubernetes 集群没有被实际部署和运行态客户端使用，Pipeline、Release 和 Approval
也没有统一按 Project 隔离。

本功能让 Application 真正消费 Project 提供的 Kubernetes 和 Registry 上下文，并在
第一阶段通过中央 Tekton Pipeline 挂载目标集群 kubeconfig 的方式完成跨集群部署。

## 当前行为

- Application、Environment、Pipeline、Release、Approval 和 Runtime 均通过显式 Project
  路径访问，父子资源归属不匹配时返回 404。
- Application 创建不再回退平台级 Registry；发布前必须解析出当前 Project 的有效交付上下文。
- Environment 绑定的 Kubernetes 集群负责配置、运行态、日志、YAML 和回滚；中央 Kubernetes
  仅负责 Tekton 与构建凭据。
- 发布计划、直接发布和审批通过都会校验 Cluster/Registry 的启用状态及最近连接状态。
- 前端交付导航、API 和 Pipeline/Release/Approval 链接都保留当前 Project 上下文。
- 当前 Tekton Pipeline 在中央集群中执行构建、镜像推送和目标集群部署；发布批次完成构建后，
  由第一版 Delivery Reconciler 按环境创建 Deploy-only PipelineRun。

相关证据包括：

- `backend/app/services/application_service.py`
- `backend/app/services/environment_service.py`
- `backend/app/services/deployment_plan_service.py`
- `backend/app/routes/applications.py`
- `backend/app/services/tekton_service.py`
- `deploy/tekton/pipelines/`
- `frontend/src/router/index.ts`

## 目标行为

Application、Environment、Pipeline、Release、Approval 和 Runtime 全部位于显式 Project
作用域中。Application Environment 绑定的 Kubernetes 集群是配置写入、部署、状态、日志、
YAML 和回滚的唯一目标集群。Project 默认 Registry 是构建和部署使用的唯一镜像仓库。

第一阶段继续由中央 Tekton 执行构建和部署。平台为每个 Project Kubernetes 集群在中央
Tekton Namespace 中维护一个确定性命名的持久 kubeconfig Secret，只有 Pipeline 的
deploy Task 挂载该 Secret，并显式选择 Environment 保存的 kube context。

## 范围

- 包含：Application 及其 Environment、Config、Execution、Release、Approval、Runtime
  API 统一改为 Project 子资源，并对父子资源归属进行 404 隔离。
- 包含：历史 Application、PipelineExecution、ReleaseRecord 和 ApprovalRecord 的
  Project 关联回填与非空约束迁移。
- 包含：Environment 解析目标集群、Project 默认 Registry 和 Namespace 的统一交付上下文。
- 包含：Cluster 和 Registry 必须启用且最近一次连接状态为 `connected` 才能发布。
- 包含：目标集群客户端用于 Namespace、ConfigMap、Secret、镜像拉取 Secret、运行态和
  回滚；中央集群客户端仅用于 Tekton、中央 Registry Secret 和 kubeconfig Secret。
- 包含：三个现有 Tekton Pipeline 的 deploy Task 挂载 kubeconfig，并显式使用 kube
  context 执行 `kubectl`。
- 包含：前端所有 Application、Pipeline、Release、Approval 和 Runtime 导航保持当前
  Project 上下文。
- 包含：发布计划展示目标集群、Namespace、Registry、连接状态和阻塞原因。
- 包含：构建版本与发布解耦，Build Pipeline 只构建镜像，Deploy-only Pipeline 使用已成功构建版本向 Environment Promotion。

## 非目标

- 不包含 Delivery Reconciler 的后台常驻 Worker、事件监听和持久 kubeconfig Secret 的移除；
  当前阶段保留按请求触发的 Reconciler 与中央 Tekton kubeconfig Secret。
- 不包含 ProjectMember 与登录用户的身份绑定和角色授权；本阶段所有操作仍要求登录，并
  只实现资源作用域隔离。
- 不包含 Project GitHub Organization、Team 或 Repo Group 对仓库地址的强制校验。
- 不包含 pnpm、yarn 或其他新的流水线模板。
- 不包含 Application AI 分析、修复或发布建议能力。
- 不包含构建产物跨 Application 复用；构建版本仍限定在单个 Application 内。
- 不删除历史 Default Project 或平台级 Registry 数据，但新的 Application 交付不再回退
  使用这些资源。

## 验收条件

- [x] 给定 Project A 下的 Application，当用户通过 Project B 的 API 路径访问详情、环境、
      配置、发布、运行态、Pipeline、Release 或 Approval 时，则返回 404 且不泄露资源信息。
- [x] 给定创建 Application 的请求缺少 Project 上下文，当请求到达后端时，则请求被拒绝，
      且不会创建或回退到 Default Project。
- [x] 给定 Environment 未绑定集群，或绑定集群停用、未测试、连接失败，当生成发布计划或
      提交发布时，则返回明确阻塞项且不创建 PipelineRun。
- [x] 给定 Project 缺少启用、默认且连接成功的 Registry，当生成发布计划或提交发布时，
      则返回明确阻塞项且不创建 PipelineRun。
- [x] 给定交付上下文有效，当发布时，则应用配置写入 Environment 目标集群，中央 Tekton
      Namespace 获得确定性命名的集群 kubeconfig Secret 和 Registry Secret。
- [x] 给定 PipelineRun 被创建，当检查 Pipeline 资源时，则只有 deploy Task 挂载 kubeconfig，
      并通过显式 kubeconfig 路径和 kube context 向目标 Namespace 执行 `kubectl`。
- [x] 给定用户查询状态、Pod 日志、Pod YAML 或执行回滚，当 Environment 绑定目标集群时，
      则操作使用该集群客户端，不使用平台默认 Kubernetes 客户端。
- [x] 给定待审批发布的 Environment、Cluster 或 Registry 在审批期间发生变化，当审批通过时，
      则系统重新解析和校验交付上下文；失效上下文不能继续创建 PipelineRun。
- [x] 给定 Pipeline、Release 或 Approval 的 Project 列表接口，当查询时，则结果只包含当前
      Project 的数据库记录，且 PipelineRun 名称不能绕过数据库归属校验直接访问中央 Tekton。
- [x] 给定 kubeconfig、Registry Token 或应用 Secret，当执行 API、日志和测试时，则明文不会
      出现在响应、错误消息、Pipeline 参数、Release 记录或测试输出中。
- [x] Alembic migration 能升级和降级，历史记录的 Project 与交付目标关联得到保留。
- [x] 后端相关自动化检查、前端类型检查、生产构建和 `./scripts/verify.sh` 全部通过。
- [x] `docs/current-state.md` 在实现并验证完成后反映最终能力和已知缺口。
- [x] 构建版本只创建 Build PipelineRun；发布已有构建版本时只创建 Deploy-only PipelineRun，且同一版本可发布到多个 Environment。
- [x] 生产审批记录具体 `build_version_id`，审批通过后不重复执行构建。

## 设计说明

新增 `DeliveryContextService` 统一解析并验证 Project、Application、Environment、Cluster、
Registry 和 Namespace。它不执行外部操作，也不向调用者暴露明文凭据。

`KubernetesClusterService` 负责从加密 kubeconfig 创建目标集群客户端；新增
`ClusterCredentialMaterializer` 负责将 kubeconfig 同步到中央 Tekton Namespace。
`ConfigurationService` 使用目标集群客户端物化应用配置；`TektonService` 只操作中央
Tekton；新增 `ApplicationRuntimeService` 统一目标集群的状态、日志、YAML 和回滚行为。

持久 kubeconfig Secret 采用 Project ID 与 Cluster ID 组成的确定性名称。每次发布前执行
幂等 upsert，从而保证 Project 中 kubeconfig 更新后下一次发布使用新内容。Secret 内容不
进入数据库新增字段、API、日志或 Pipeline 参数。

## 验证证据

实现过程中补充具体测试命令、migration 升降级结果、前端构建结果和
`./scripts/verify.sh` 输出。

## 完成

验收后将状态改为“已验收”，记录验收日期，并把本文件移至 `specs/completed/`。
