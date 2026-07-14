# Application 构建历史与详情页设计

## 背景

Project CI/CD 工作台以 Application 卡片汇总构建和发布状态。当前卡片的详情入口跳转到通用
Application 工作区，用户无法在 CI/CD 上下文中连续查看某个服务的历史构建和单次构建日志。

## 目标

为每个 Application 提供 CI/CD 专用构建页面，在同一页面中使用左侧历史列表和右侧构建详情。
进入页面时自动选中最新构建；用户切换历史记录后，右侧原地更新构建信息、步骤和所选步骤日志。

## 页面与路由

新增项目级路由：

```text
/devcenter/projects/:projectId/pipelines/applications/:applicationId/builds/:buildId?
```

`buildId` 可选。未提供时自动选择最新构建，并用替换历史记录的方式补齐 URL；提供时只允许选择
当前 Project、当前 Application 下存在的构建。CI/CD 工作台卡片的详情图标进入此路由，不再进入
通用 Application 详情页。

页面标题展示 Application 名称和仓库，并提供返回 CI/CD 工作台的入口。

## 布局与交互

桌面端使用双栏：

- 左侧为固定宽度的构建历史列表，显示构建序号或版本标识、状态、分支、短 Commit、触发时间和
  可用时的耗时。选中项具有明确高亮。
- 右侧展示所选构建的镜像 Tag、完整 Commit 信息、Commit message、PipelineRun 名称、开始和
  结束时间、耗时及失败原因。
- Clone、Build、Push 作为可选择步骤展示。存在失败步骤时默认选择第一个失败步骤；否则优先选择
  Build；缺少 Build 时选择第一个步骤。
- 点击步骤后，仅更新下方日志查看区，不发生页面跳转。

窄屏下切换为历史列表在上、详情在下。选择历史记录后页面滚动到详情区域。

## 数据流

页面并行加载 Application 基础信息和构建版本列表。选择构建后，根据该构建保存的
`pipeline_run_name` 请求现有 Pipeline 状态和日志接口，并把 TaskRun/Step 日志标准化为页面所需的
Clone、Build、Push 步骤。

构建列表继续以 MySQL 中的 `ApplicationBuildVersion` 作为业务历史来源。Tekton 日志不可用时，
构建基本信息仍可展示，日志区域显示明确的不可用状态，不伪造成功或空日志。

运行中或待处理的构建每 15 秒刷新当前构建详情和历史列表；终态构建停止轮询。切换构建时忽略旧
请求结果，避免较慢响应覆盖当前选择。

## 空状态与错误处理

- 没有构建记录：展示空状态和“发起构建”操作，打开该 Application 的快速构建抽屉。
- 构建不存在或不属于当前 Application：显示未找到提示，并允许返回最新构建。
- 构建没有 `pipeline_run_name`：展示构建元数据，步骤与日志区域说明执行详情尚不可用。
- PipelineRun 已被集群清理或日志读取失败：保留业务历史，日志区域展示错误并提供重试加载。
- API 继续使用统一的 `success`、`message`、`data`、`timestamp`、`trace_id` 响应结构。

## 组件边界

- 新路由级 View 负责加载状态、URL 选择和响应式布局。
- 构建历史列表组件只负责呈现和选择构建。
- 构建详情组件负责元数据、步骤选择和日志展示。
- 所有 HTTP 调用继续集中在 `frontend/src/api`。
- 后端若需补充单构建查询，由 Application Service 提供业务行为，HTTP Handler 只负责参数校验。

## 非目标

- 不修改构建、发布、审批、重试或 Tekton 执行行为。
- 不在此页面展示环境发布历史、运行态资源或 Application 配置。
- 不提供跨 Application 的构建比较或批量操作。
- 不长期复制 Tekton 完整日志到 MySQL。

## 测试与验收

- 路由和工作台详情入口指向专用构建页面。
- 无 `buildId` 时选择最新构建；有效 `buildId` 可刷新恢复；越界构建被拒绝。
- 历史列表切换会更新详情、步骤和日志，旧请求不会覆盖新选择。
- 运行中构建轮询，终态构建不轮询。
- 无构建、无 PipelineRun、日志丢失和请求失败均有真实空态或错误态。
- 桌面双栏和移动端上下布局通过前端生产构建与人工视觉验收。
- `./scripts/verify.sh` 通过，能力状态同步更新到 `docs/current-state.md`。

