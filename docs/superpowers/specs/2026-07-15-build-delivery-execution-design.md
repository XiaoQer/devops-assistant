# 构建与环境发布执行详情设计

## 背景

Application 构建浏览页当前把 Tekton 日志归纳为固定的 Clone、Build、Push 三个逻辑步骤。
这种展示隐藏了 Maven、npm、Kaniko 等实际步骤，也没有显示同一构建版本随后发布到 DEV、QA、
PROD 等环境时创建的 Deploy-only PipelineRun、审批状态和部署日志。

## 目标

右侧构建详情展示该构建版本实际发生的完整交付流程：上方展示 Build Pipeline 的真实 Task/Step，
下方按环境分组展示发布目标的业务状态，以及存在时的 Deploy-only PipelineRun 实际步骤与日志。

## 页面结构

保留左侧历史构建和右侧详情布局。右侧分为：

1. 构建流程：按 Tekton 返回顺序展示真实 Task/Step 名称、状态、时间和日志，不再固定转换为
   Clone、Build、Push。
2. 环境发布：读取所选构建对应发布批次的 targets，按环境分别展示等待构建、等待审批、部署中、
   成功或失败状态。
3. 环境执行详情：选择已有 `pipeline_run_name` 的环境后，加载 Deploy-only PipelineRun 的真实
   Task/Step 和日志；没有 PipelineRun 时展示业务原因，不伪造步骤。

构建步骤和环境步骤使用同一套通用执行步骤组件，但各自维护当前选择。默认选择规则为：第一个失败
步骤，其次当前运行步骤，最后第一个步骤。

## 数据流

- Application 构建版本继续来自 MySQL `ApplicationBuildVersion`。
- 发布批次和目标来自 Application release-batches API，并按 `build_version_id` 关联所选构建。
- Build Pipeline 日志来自构建版本的 `pipeline_run_name`。
- Deploy Pipeline 日志来自每个 release target 的 `pipeline_run_name`。
- Tekton Task/Step 保留 API 返回顺序和原始名称；前端只生成可读标签，不改变步骤语义。
- 同一构建后续追加环境时，刷新发布批次即可显示新增目标。

页面请求使用代次保护。切换构建或环境后，旧日志响应不得覆盖新选择。构建或任一目标处于
Pending、Running、Building、Deploying、WaitingApproval 等活跃状态时，每 15 秒刷新业务状态和
当前可见日志；全部进入终态后停止轮询。

## 状态与错误

- 等待审批：显示审批状态和环境信息；不请求不存在的 PipelineRun。
- PipelineRun 尚未创建：显示当前业务状态和等待原因。
- PipelineRun 已清理或日志读取失败：保留发布目标状态，日志区域显示错误并允许重试。
- 没有发布批次：显示“此构建尚未发布到任何环境”，不影响构建步骤查看。
- 部分环境失败：只将对应环境标记失败，其他环境保持自己的真实状态。
- 生产环境审批只能通过既有审批流程处理，本页面不新增绕过入口。

## 组件边界

- `state.ts` 负责将原始 Task/Step 扁平化为保序的通用执行步骤，以及默认选择和活跃状态判断。
- 通用步骤日志组件负责步骤选择和单步骤日志，不知道 Build 或 Deploy 业务。
- 环境发布组件负责 target 卡片、审批/等待状态和环境选择。
- 路由 View 负责加载构建、批次、构建日志和所选环境日志，并管理轮询与请求代次。
- HTTP 请求继续集中在 `frontend/src/api`；不在 View 内直接使用 Axios。

## 非目标

- 不修改 Build once/Promote、审批、部署和 Tekton Pipeline 定义。
- 不合并不同环境为一条伪造的 Pipeline。
- 不把完整 Tekton 日志长期复制到 MySQL。
- 不在本页面批准生产发布。

## 验收

- Java、Node 和 Dockerfile Build Pipeline 均显示 API 返回的真实 Task/Step 顺序和名称。
- 所选构建关联的全部环境 targets 都可见，追加环境刷新后出现。
- 等待审批或尚无 PipelineRun 的环境显示真实业务状态。
- 已执行环境可选择实际部署步骤并查看日志，切换环境不存在旧响应覆盖。
- 默认步骤遵循失败、运行、首项优先级。
- 活跃构建或环境继续轮询，全部终态停止。
- 自动化测试、类型检查、生产构建和 `./scripts/verify.sh` 通过。

