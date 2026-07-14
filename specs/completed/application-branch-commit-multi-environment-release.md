# 功能：基于分支提交的多环境构建与发布

- 状态：当前阶段已实现；Digest 与后台常驻协调延期
- 创建日期：2026-07-14
- 关联设计：`docs/superpowers/specs/2026-07-14-application-multi-environment-release-design.md`

## 背景

当前 Application 发布入口主要围绕应用默认分支和单个环境工作，无法在发布时选择其他
分支或明确的提交，也无法在一次构建后向多个环境推广同一个构建产物。需要将发布流程调整
为标准的 Build once / Promote：用户选择分支和提交，多选目标环境；平台只构建一次镜像，
构建成功后按环境独立部署。

## 目标行为

发布流程分为以下阶段：

```text
选择分支 → 加载最近提交 → 选择提交与多个环境 → 创建一次 Build PipelineRun
→ 构建成功 → Delivery Reconciler 为每个环境创建 Deploy-only PipelineRun
→ 环境独立完成、失败或等待审批
```

发布请求需要固定并持久化：

- 仓库地址
- 分支名
- 提交 SHA
- 提交信息和作者
- 目标环境集合

构建成功后所有目标环境复用同一个镜像版本。当前阶段以镜像 Tag 作为交付依据，Digest
采集与优先使用延期。

## 范围

- 包含：公共 Git 仓库的分支列表查询。
- 包含：按分支查询最近 20 条提交记录。
- 包含：默认使用 Application 当前分支，默认选中最新提交。
- 包含：发布弹窗支持切换分支、选择提交和多选环境。
- 包含：构建 Pipeline 接收 commit 参数并构建指定提交。
- 包含：一次发布批次只创建一个 Build PipelineRun。
- 包含：Delivery Reconciler 在构建成功后为每个目标环境创建 Deploy-only PipelineRun。
- 包含：各环境使用自身 Kubernetes 集群、context、Namespace 和环境变量配置。
- 包含：环境发布状态独立记录，一个环境失败不阻断其他环境继续发布。
- 包含：生产环境审批关联具体构建版本和具体目标环境。
- 包含：发布历史能够关联分支、提交、构建版本和各环境部署执行记录。

## 非目标

- 不包含私有 Git 仓库凭据、Git Token 或 OAuth/OIDC 集成。
- 不包含超过最近 20 条的提交历史分页。
- 不包含跨 Application 复用构建产物。
- 不包含构建失败后的自动重试策略设计。
- 不包含重新设计 Kubernetes 环境配置模型；沿用现有环境、配置和交付上下文。
- 不包含用单一动态 Tekton Pipeline 定义承载任意数量环境的方案。

## API 设计

新增应用级 Git 信息接口：

- `GET /api/projects/{project_id}/applications/{app_id}/git/branches`
- `GET /api/projects/{project_id}/applications/{app_id}/git/branches/{branch}/commits?limit=20`

接口要求：

- 必须校验 Application 属于当前 Project，不匹配返回 404。
- 仅访问公共仓库；仓库不可访问、分支不存在或提交读取失败返回明确错误。
- `limit` 服务端限制为 20，不能通过请求参数绕过上限。
- 不在响应、日志或错误消息中暴露仓库凭据。

发布请求扩展为：

```json
{
  "branch": "feature/example",
  "git_commit": "<sha>",
  "environment_ids": [12, 13]
}
```

服务端必须重新校验提交、环境归属、集群状态、Registry 状态和生产审批策略，不能信任
前端传入的分支提交元数据。

## 构建与部署设计

### Build Pipeline

- 接收 `repo_url`、`branch`、`commit`、镜像信息参数。
- checkout 指定 commit，不能只按 branch 的最新 HEAD 构建。
- BuildVersion 保存 branch、commit、commit message、author、镜像 Tag、Digest 和
  Build PipelineRun 名称。
- 一个发布批次只创建一个 Build PipelineRun。

### Delivery Reconciler

当前阶段由发布批次、Pipeline flow 和批次详情请求触发 Reconciler：

- 构建成功后，为每个目标环境创建独立 Deploy-only PipelineRun。
- 构建失败时，不创建任何部署 PipelineRun。
- 每个环境只使用同一 BuildVersion 的镜像 Tag/Digest。
- 每个环境的失败、成功、等待审批和上下文失效独立持久化。
- Reconciler 重复处理同一批次时必须幂等，不能重复创建同一环境的部署任务。

后台常驻 Worker、Tekton 事件监听和镜像 Digest 自动采集不属于当前阶段。

### 环境上下文

每个 Deploy-only PipelineRun 使用目标环境解析出的：

- Kubernetes 集群和 kube context
- Namespace
- 环境变量和现有配置物化结果
- 环境部署参数
- 目标环境对应的 Registry 拉取凭据

中央 Tekton 只负责构建和执行 Pipeline；目标环境的 Kubernetes API 执行仍遵守现有
Project/Cluster 交付上下文边界。

## 多环境与审批

- 非生产环境可以直接创建 Deploy-only PipelineRun。
- 生产环境为对应 BuildVersion 和 Environment 创建独立审批记录。
- 生产审批等待期间，其他已选择环境继续发布。
- 审批通过时重新解析并校验 Cluster、Registry 和 Namespace 上下文。
- 生产上下文失效只阻止生产环境，不影响其他环境。

## 前端交互

发布弹窗改为紧凑三段式：

1. 分支选择：默认 Application 当前分支，可切换并加载提交。
2. 提交选择：展示最近 20 条提交，默认选中最新提交，展示 SHA、消息、作者和时间。
3. 环境多选：展示环境、集群、Namespace、审批要求和当前状态。

提交后显示发布批次和环境执行状态：

- 构建中
- 构建失败
- 等待部署
- 等待审批
- 部署中
- 部分成功
- 全部成功

## 验收条件

- [x] 发布弹窗可以加载并切换公共仓库分支。
- [x] 切换分支后加载最近 20 条提交，默认选中最新提交。
- [x] 发布前必须选择一个提交和至少一个环境。
- [x] 一次发布请求只创建一个 Build PipelineRun。
- [x] Build Pipeline 按指定 commit 构建，而不是按提交时的 branch HEAD 构建。
- [x] 构建成功后所有目标环境复用同一个 BuildVersion 镜像 Tag。
- [x] 每个环境使用自身 Kubernetes 集群、context、Namespace 和环境变量。
- [x] 一个环境失败不阻断其他环境继续发布。
- [x] 构建失败时不创建 Deploy-only PipelineRun。
- [x] 生产审批记录具体 BuildVersion 和 Environment，审批等待不阻断其他环境。
- [x] Reconciler 重试和重复扫描不会重复创建环境部署任务。
- [x] 发布历史能关联 branch、commit、BuildVersion 和环境部署记录。
- [x] 资源越权、无效提交、无效环境和失效交付上下文均被服务端拒绝。
- [x] 相关后端测试、前端类型检查、生产构建和 `./scripts/verify.sh` 通过。

## 已知风险与后续

- 当前只支持公共仓库；私有仓库凭据作为独立规格处理。
- Reconciler 需要可靠的周期扫描或事件触发机制，并需要记录幂等游标或环境任务关联。
- 镜像 Digest、后台常驻 Reconciler 和审批期间完整上下文漂移校验延期，不纳入当前阶段验收。
