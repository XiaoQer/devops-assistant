# 功能：Application 构建历史与详情页

- 状态：已确认
- 负责人：Codex
- 创建日期：2026-07-14

## 背景

CI/CD 工作台的 Application 详情入口当前进入通用 Application 工作区。用户需要一个专用页面，
在 CI/CD 上下文中同时查看该服务的历史构建列表和某次构建的步骤日志。

## 当前行为

`frontend/src/views/PipelineRuns.vue` 的 `openApplication` 跳转到
`/devcenter/projects/:projectId/applications/:id`。构建版本摘要位于通用 Application 详情页，单次
Pipeline 日志则位于独立 Pipeline 详情页，用户需要在多个页面间切换。

## 目标行为

工作台详情入口进入 Application 专用构建页面。页面左侧展示历史构建，右侧展示所选构建信息、
Clone/Build/Push 步骤及所选步骤日志，并默认选中最新构建。

## 范围

- 包含：新增 Project/Application 范围的构建历史与详情路由和页面。
- 包含：历史列表选择、URL 恢复、步骤选择、日志加载、运行态轮询和响应式布局。
- 包含：工作台详情入口改为新页面。
- 包含：必要的数据读取 API、自动化检查和项目状态文档更新。

## 非目标

- 不包含：修改构建、发布、审批、重试或 Tekton 执行逻辑。
- 不包含：环境发布历史、运行态资源和 Application 配置。
- 不包含：跨 Application 比较、批量操作或长期持久化完整 Tekton 日志。

## 验收条件

- [ ] 给定一个存在构建历史的 Application，当从 CI/CD 工作台点击详情时，则进入专用构建页面，
      不再进入通用 Application 详情页。
- [ ] 给定 URL 未指定构建，当页面加载时，则自动选择最新构建并展示详情。
- [ ] 给定 URL 指定属于当前 Application 的构建，当刷新页面时，则恢复该构建选择。
- [ ] 给定不属于当前 Project/Application 的构建 ID，则页面不展示越界数据并提供恢复入口。
- [ ] 给定用户选择另一条历史构建，则右侧原地更新构建信息、步骤和日志。
- [ ] 给定步骤列表，则失败时默认选择第一个失败步骤，否则优先选择 Build；点击步骤切换日志。
- [ ] 给定运行中构建，则每 15 秒刷新；给定终态构建，则停止轮询。
- [ ] 无构建、无 PipelineRun、PipelineRun 已清理和日志请求失败均展示真实空态或错误态。
- [ ] 桌面端为左侧历史、右侧详情；窄屏为上方历史、下方详情。
- [ ] 相关自动化检查、前端类型检查、生产构建和 `./scripts/verify.sh` 通过。
- [ ] `docs/current-state.md` 反映最终能力和已知缺口。

## 设计说明

详细设计见
`docs/superpowers/specs/2026-07-14-application-build-explorer-design.md`。构建业务历史来自 MySQL，
执行步骤和日志来自现有 Tekton/Pipeline 接口；日志不可用不影响构建业务信息展示。

## 验证证据

实现过程中补充。

## 完成

验收后将状态改为“已验收”，记录日期，并把文件移至 `specs/completed/`。
