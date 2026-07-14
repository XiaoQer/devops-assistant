# 功能：构建与环境发布执行详情

- 状态：已确认
- 负责人：Codex
- 创建日期：2026-07-15

## 背景

Application 构建浏览页只显示固定归纳的 Clone、Build、Push，没有反映 Tekton 实际步骤，也没有
展示同一构建版本发布到多个环境时的审批、Deploy-only PipelineRun 和部署日志。

## 当前行为

`frontend/src/features/build-explorer/state.ts` 把日志归纳为三个固定步骤；
`ApplicationBuildExplorer.vue` 只加载构建 Pipeline 日志，不读取该构建关联的发布批次与 targets。

## 目标行为

构建详情上方按实际顺序显示 Build Pipeline 的 Task/Step；下方按环境分组显示发布目标状态，选择
已执行环境后展示其 Deploy-only PipelineRun 的实际步骤和日志。

## 范围

- 包含：保序展示实际 Tekton Task/Step 名称、状态、时间和日志。
- 包含：按构建版本加载发布批次和全部环境 targets。
- 包含：等待审批、等待 PipelineRun、部署中、成功、失败和日志不可用状态。
- 包含：环境选择、部署步骤日志、请求代次保护和活跃状态轮询。
- 包含：相关自动化测试、项目状态文档和规格归档。

## 非目标

- 不包含：修改构建、Promote、审批、部署或 Tekton Pipeline 定义。
- 不包含：跨环境合并执行记录或长期保存完整 Tekton 日志。
- 不包含：在详情页批准或绕过生产审批。

## 验收条件

- [ ] Build Pipeline 按 API 返回顺序展示真实 Task/Step，不再固定为 Clone/Build/Push。
- [ ] Java、Node 和 Dockerfile 构建的实际步骤名称和日志均被保留。
- [ ] 所选构建关联的全部发布环境均按 target 独立展示，追加环境刷新后出现。
- [ ] 等待审批和没有 PipelineRun 的环境展示真实业务状态，不生成执行步骤。
- [ ] 选择已有 PipelineRun 的环境后展示实际 Deploy Task/Step 和单步骤日志。
- [ ] 切换构建或环境时，旧日志响应不能覆盖当前选择。
- [ ] 默认选择第一个失败步骤，其次运行步骤，否则第一个步骤。
- [ ] 构建或任一环境处于活跃状态时自动刷新，全部终态后停止轮询。
- [ ] 部分环境失败不改变其他环境的展示状态。
- [ ] 自动化测试、类型检查、生产构建和 `./scripts/verify.sh` 通过。
- [ ] `docs/current-state.md` 更新为最终能力。

## 设计说明

详细设计见
`docs/superpowers/specs/2026-07-15-build-delivery-execution-design.md`。业务状态来自 MySQL 发布批次，
执行步骤与日志来自 Tekton；任一来源暂时不可用时不伪造另一来源的结果。

## 验证证据

实现过程中补充。

## 完成

验收后改为“已验收”，记录日期，并移至 `specs/completed/`。
