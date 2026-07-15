# 功能：统一交付执行标签

- 状态：已验收
- 负责人：Codex
- 创建日期：2026-07-15

## 背景

构建步骤日志和环境发布步骤日志上下分区展示，造成标题、步骤区和日志框重复，页面过长。

## 当前行为

`ApplicationBuildDetail.vue` 先渲染构建 `PipelineStepLogPanel`，再渲染
`BuildDeliveryTargets.vue`；选中环境后在下方创建第二套步骤与日志区域。

## 目标行为

构建与各环境成为同级执行标签，所选执行对象共用下方唯一的步骤与日志区域。

## 范围

- 包含：构建、环境 target 统一标签和紧凑响应式布局。
- 包含：共用步骤日志面板、等待态、错误态、选择保持和竞态保护。
- 包含：自动化测试、项目状态文档和规格归档。

## 非目标

- 不包含：后端 API、Pipeline、发布或审批行为变更。
- 不包含：新增发布、审批或重试操作。

## 验收条件

- [x] “构建”与发布环境按同级标签展示，构建固定在首位。
- [x] 页面只显示一套步骤选择和日志面板，不再上下重复。
- [x] 默认选中构建；选择环境后原位展示其 Deploy-only Pipeline 实际步骤和日志。
- [x] 等待审批或没有 PipelineRun 的环境显示真实状态且不请求日志。
- [x] 切换构建时回到构建标签，切换环境时旧日志不能覆盖新选择。
- [x] 轮询刷新后尽量保持当前环境选择，target 不存在时回到构建。
- [x] 没有环境发布时不展示多余空区块。
- [x] 窄屏执行标签可横向滚动，日志区域不发生额外上下跳动。
- [x] 自动化测试、类型检查、生产构建和 `./scripts/verify.sh` 通过。
- [x] `docs/current-state.md` 更新为最终能力。

## 设计说明

详细设计见 `docs/superpowers/specs/2026-07-15-unified-delivery-execution-tabs-design.md`。

## 验证证据

- `frontend/src/features/build-explorer/state.test.ts` 覆盖构建优先顺序、环境 target 顺序、
  执行 key 解析、刷新选择保持及 target 消失后的构建回退。
- 2026-07-15 运行 `./scripts/verify.sh`：后端 210 项测试通过，前端 21 项测试通过，Vue 类型检查
  和 Vite 生产构建通过。
- 代码审查未发现 Critical、Important 或阻塞性 Minor 问题。

## 完成

验收日期：2026-07-15。
