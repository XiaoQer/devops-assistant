# Application 构建工作区复用设计

## 背景

Application 详情的 Pipeline Tab 仍维护一套简化“构建版本与发布批次”列表，而 CI/CD 构建浏览页
已经提供完整的历史、构建信息、实际 Task/Step、环境发布和日志。两处字段、状态摘要和“详情”入口
不同，用户会误以为它们代表不同的交付事实。

## 目标

Application Pipeline Tab 与 CI/CD 构建浏览页使用同一个构建工作区组件，展示完全一致的历史、
构建详情、交付执行标签、步骤与日志，不再维护第二套简化详情。

## 组件结构

- 新增路由无关的 `ApplicationBuildWorkspace.vue`，接收 `projectId`、`applicationId` 和可选的
  `selectedBuildId`，负责当前构建浏览页的全部数据加载、选择、日志请求、轮询、空状态和快速构建。
- 工作区通过事件报告 Application 上下文和构建选择，不直接读取或修改路由。
- `ApplicationBuildExplorer.vue` 仅负责 CI/CD 页面标题、返回按钮和构建版本深链接；把路由 buildId
  传入共享工作区，并在选择变化时更新 URL。
- `ApplicationDetail.vue` 的 Pipeline Tab 直接挂载共享工作区，不再渲染旧列表、独立刷新按钮或
  “构建新版本”按钮；未指定构建时由共享工作区选中最新构建。

## 数据与交互

- Application、构建版本、环境和发布批次只由共享工作区按既有 API 加载。
- Build/Deploy Pipeline 日志、请求代次保护、活跃状态轮询和执行标签选择沿用现有行为。
- CI/CD 深链接不存在时，共享工作区选择最新构建并通知宿主写入 URL；无效 buildId 显示既有无效态。
- Application Tab 内切换构建不改变 Application 路由，只更新组件本地选择。
- 两处的空状态、错误重试、快速构建抽屉、历史栏吸顶和移动端布局完全一致。

## 清理

- 删除 Application Pipeline Tab 的简化构建列表模板、专属样式和只为该列表服务的辅助函数。
- 如果 `ApplicationDetail` 的其他发布功能仍使用构建版本或发布批次，则保留其数据；否则移除重复请求。
- Pipeline Tab 标签可保留构建数量；数量由共享工作区通过事件回传，避免父页面重复加载构建列表。

## 错误处理

- 共享工作区加载失败仅显示自身错误态，不影响 Application 的其他 Tab。
- 组件卸载或切换宿主时停止轮询并使未完成请求失效。
- Application Tab 被缓存但隐藏时不新增额外行为；沿用 Vue 当前挂载语义。

## 验证

- 状态测试覆盖受控构建 ID 与最新构建选择的同步规则。
- 类型检查证明两个宿主的 props/emits 契约一致。
- 生产构建与 `./scripts/verify.sh` 通过。
- 审查确认旧 Pipeline 列表、按钮和专属样式已删除，HTTP 请求仍集中在 API 模块。

## 非目标

- 不改变后端 API、构建、发布、审批或 Pipeline 定义。
- 不合并 Application 其他 Tab，也不改变 CI/CD 或 Application 的路由结构。
- 不在 Pipeline Tab 保留独立工具栏或另一套详情摘要。
