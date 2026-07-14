# 功能：Project CI/CD 工作台

- 状态：已验收
- 负责人：Codex
- 创建日期：2026-07-14

## 背景

开发者当前需要进入 Project，再进入某个 Application，切换到 Pipeline 区域后才能触发
新版本。对于包含 10–30 个 Application 的 Project，频繁在服务间切换会拉长日常构建和
发布路径。

需要在 Project 交付边界内提供一个面向多个 Application 的 CI/CD 工作台。它用于快速
了解每个服务的最近交付状态，并从同一页面发起单个 Application 的构建和可选的多环境
发布；它不是 Application Pipeline 详情页的替代品。

## 当前行为

- `/devcenter/projects/:projectId/pipelines` 已汇总 Project 内的 PipelineRun，并支持状态、
  搜索、分页和详情跳转，但主要用于查看执行和排障，不能直接发起构建。
- Application 工作区允许选择分支、最近 20 条 Commit 和多个环境来创建发布批次。
- `ReleaseBatchService.create()` 当前要求至少选择一个环境，因此不能通过同一套精确 Commit
  工作流执行“只构建”。
- 构建版本、Build once/Promote、Deploy-only Pipeline、多环境独立状态和生产审批已经存在。
- 构建完成后的交付推进当前依赖批次或 Pipeline flow 请求触发 Reconciler；后台常驻调度
  不在当前范围。

## 目标行为

在 DevCenter 的 Project 范围提供“CI/CD 工作台”：

1. 页面以紧凑 Application 卡片为主，适配每个 Project 约 10–30 个 Application。
2. 卡片展示 Application 名称、最近一次构建或发布状态、分支、短 Commit、时间、构建阶段、
   已关联环境状态及当前可执行动作。
3. 页面支持按 Application 名称或仓库搜索、按状态筛选，并默认按最近活动排序。
4. 用户从 Application 卡片点击“构建”后，在侧边面板中确认：
   - 默认分支；
   - 默认分支的最新 Commit；
   - 可切换的分支与该分支最近 20 条 Commit；
   - 零个或多个目标环境；
   - 即将使用的镜像 Tag 和 Commit 摘要。
5. 目标环境为空时，只创建 Build Pipeline 和可复用的构建版本。
6. 选择目标环境时，Build Pipeline 成功后自动推进这些环境的 Deploy-only Pipeline；需要
   审批的环境先进入审批，批准后再部署。
7. Build Pipeline 运行期间不允许修改本次批次的目标环境。
8. 构建成功后，用户可以从构建版本追加尚未关联的目标环境。追加环境不重新构建镜像；需要
   审批的环境仍进入既有审批流程。
9. 已处于等待构建、等待审批、部署中或部署成功状态的目标环境不可重复追加。同批次不同环境
   独立推进和失败，单个环境失败不影响其他环境。
10. 卡片提供查看进度、查看日志、重试、发布此版本及进入 Application/Pipeline 详情的入口；
    深度配置、完整历史和运行态排障仍保留在现有详情页。

## 范围

- 包含：Project 级 CI/CD 工作台路由、导航入口和 Application 卡片列表。
- 包含：适合 10–30 个 Application 的聚合查询，避免前端逐个 Application 请求构建、环境
  和批次数据。
- 包含：默认分支、最新 Commit、最近 20 条 Commit、可选目标环境的快速构建面板。
- 包含：允许零环境的构建批次，以及构建成功后为同一批次追加环境的服务端用例。
- 包含：构建、审批和多环境 Deploy-only 状态的展示与刷新。
- 包含：相应的后端 Service/路由测试、前端类型检查和生产构建验证。
- 包含：统一 API 响应结构、Project/Application 归属校验和可信当前用户审计字段。

## 非目标

- 不支持一次选择多个 Application 批量构建。
- 不提供跨 Project 的全局 CI/CD 操作页。
- 不替代 Pipeline 详情、Application 工作区、发布历史或运行态页面。
- 不允许在 Build Pipeline 运行期间增删本批次目标环境。
- 不实现取消 Pipeline、定时构建、Webhook 自动触发或自定义 Pipeline 编辑器。
- 不实现后台常驻 Delivery Reconciler、镜像 Digest 采集或新的 RBAC 体系。
- 不绕过生产确认、审批、Project 集群/Registry 校验或 Secret 边界。

## 验收条件

- [x] 给定一个包含多个 Application 的 Project，当用户打开 CI/CD 工作台时，则一次聚合加载
      每个 Application 的最近交付摘要，并能搜索、筛选和按最近活动查看。
- [x] 给定某个 Application，当用户点击“构建”时，则默认分支和最新 Commit 被选中，并能
      切换分支及选择该分支最近 20 条 Commit。
- [x] 给定用户未选择环境，当确认触发时，则只创建 Build Pipeline；构建成功后存在可发布的
      构建版本，且不会创建 Deploy-only Pipeline 或审批。
- [x] 给定用户选择一个或多个非审批环境，当 Build Pipeline 成功时，则每个环境自动创建独立
      Deploy-only Pipeline，并复用同一构建版本和镜像。
- [x] 给定用户选择需要审批的环境，当 Build Pipeline 成功时，则该环境进入等待审批状态；
      只有审批通过后才创建 Deploy-only Pipeline。
- [x] 给定成功的构建版本，当用户追加尚未关联的环境时，则不重新构建并为新增环境创建交付
      目标；已有目标不能重复追加。
- [x] 给定 Build Pipeline 尚未成功，当用户尝试追加环境时，则服务端拒绝请求，且不会改变
      批次目标。
- [x] 给定同一批次包含多个环境，当一个环境部署失败时，则其他环境仍可独立推进，并可从工作台
      查看失败日志或重试允许重试的 PipelineRun。
- [x] 给定跨 Project 的 Application、环境、批次或 PipelineRun 标识，当用户请求工作台操作时，
      则服务端拒绝越界访问。
- [x] 所有新增接口保持 `success`、`message`、`data`、`timestamp`、`trace_id` 响应结构，
      且不返回 Registry 凭据、应用 Secret 或 kubeconfig。
- [x] 后端自动化测试覆盖纯构建、预选环境自动推进、审批环境、追加环境、重复环境、构建未完成、
      无效 Commit 和跨 Project 校验。
- [x] 前端类型检查、生产构建和 `./scripts/verify.sh` 通过。
- [x] `docs/current-state.md` 只在能力实际完成后更新，并记录最终状态及已知缺口。

## 设计说明

### 信息架构

工作台位于 `/devcenter/projects/:projectId/pipelines`。保留现有 Project 边界，将当前以
PipelineRun 为主的页面升级为 Application 优先的 CI/CD 工作台。Application 卡片网格是
默认主视图，现有 PipelineRun 列表保留为同页卡片网格下方的“最近执行”区域，并继续提供
分页和详情跳转。

### 前端组件边界

- 路由级工作台负责聚合加载、筛选、刷新和页面状态。
- Application 交付卡片只负责展示一个服务的摘要和上下文动作。
- 快速构建侧边面板负责分支、Commit、可选环境和提交确认。
- 构建版本发布面板负责追加环境，并排除已关联目标。
- 所有 HTTP 请求继续集中在 `frontend/src/api`。

### 后端边界

- 新增 Project 级工作台查询 Service，使用 MySQL 中的 Application、BuildVersion、
  ReleaseBatch、ReleaseTarget 和 PipelineExecution 业务历史形成摘要，不在列表查询中逐卡
  直接访问 Kubernetes。
- 扩展 ReleaseBatch Service，使环境列表可以为空，同时仍校验分支、Commit、Project 归属
  和当前用户。
- 新增向已成功构建批次追加环境的 Service 用例。路由只做传输层解析；环境去重、状态门禁、
  审批和交付推进由 Service 负责。
- Kubernetes 访问继续集中在 `KubernetesService`，Tekton 操作继续集中在
  `TektonService`。

### 数据与状态

继续使用 ApplicationReleaseBatch 表示一次精确 Commit 构建，允许其初始没有
ApplicationReleaseTarget。追加环境时为原批次创建新的 Target，不复制 BuildVersion。
现有数据模型允许批次没有 Target，并已通过 `uq_release_target_environment` 唯一约束阻止
同一批次重复关联环境，因此第一阶段不新增持久化模型或 Alembic migration。

状态至少区分：构建中、构建失败、构建成功、等待构建完成、等待审批、部署中、部署成功和
部署失败。页面状态来自持久化业务记录；Tekton 查询用于同步尚未终态的执行，不把短暂的
PipelineRun 当作唯一历史来源。

### 错误和安全

- Git 分支或 Commit 获取失败时，保留已加载的 Application 卡片并在构建面板显示可重试错误。
- Registry、Cluster 或环境交付上下文无效时，在创建目标或部署计划阶段明确阻断并返回原因。
- 构建提交失败时不留下虚假的成功批次；事务与现有构建创建保持一致。
- 追加环境使用幂等式去重；并发重复请求不能为同一批次和环境生成重复有效目标。
- 所有生产和破坏性操作继续遵循显式确认或审批要求。

### 备选方案

- 仅增强现有 PipelineRun 列表：改动较小，但不能有效支持频繁跨服务操作，未采用。
- 固定构建控制台：触发路径最短，但弱化 10–30 个服务的全局状态，未采用。
- Application 优先卡片工作台：兼顾服务切换、状态感知和快速动作，已采用。

## 验证证据

- `backend/.venv/bin/python -m pytest -q tests/test_cicd_workbench_service.py tests/test_release_batch_service.py tests/test_project_application_routes.py tests/test_application_service.py tests/test_approval_service.py tests/test_tekton_service.py`：64 个聚焦测试通过。
- 独立代码评审覆盖 Project 越界、敏感字段最小化、构建/批次匹配、终态、并发追加、Target
  原子认领、租约恢复、旧 Worker 所有权丢失和多环境失败重试；最终无 Critical/Important 问题。
- `./scripts/verify.sh` 于 2026-07-14 通过：后端 207 个测试通过；前端 Vue TypeScript 检查
  和 Vite 生产构建通过，共转换 1808 个模块。
- 产品设计阶段的浏览器交互草图由用户确认采用 Application 优先的紧凑卡片、侧边快速构建
  和构建后追加环境方案。最终代码通过生产构建；未依赖在线 Kubernetes 集群执行单元检查。

## 完成

验收日期：2026-07-14。
