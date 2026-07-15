# 功能：复用 Application 构建工作区

- 状态：已确认
- 负责人：Codex
- 创建日期：2026-07-15

## 背景

Application Pipeline Tab 与 CI/CD 构建浏览页分别展示构建详情，字段和交互不同，容易产生歧义。

## 当前行为

Application Pipeline Tab 只显示最多四条简化构建记录和独立按钮；CI/CD 页面显示完整历史、执行步骤
和环境日志。

## 目标行为

两处使用同一个构建工作区组件，内容与交互一致，仅宿主路由和外层导航不同。

## 范围

- 包含：抽取路由无关共享工作区并复用既有构建浏览能力。
- 包含：CI/CD 深链接适配、Application Tab 本地选择和构建数量回传。
- 包含：删除旧 Pipeline Tab 列表、工具栏、辅助逻辑和专属样式。
- 包含：自动化测试、项目状态文档和规格归档。

## 非目标

- 不包含：后端 API、Pipeline、构建、发布或审批行为变化。
- 不包含：Application 其他 Tab 或现有路由结构调整。

## 验收条件

- [ ] Application Pipeline Tab 与 CI/CD 页面渲染同一个构建工作区组件。
- [ ] 两处的历史、构建元数据、交付执行、步骤日志、空态和错误态完全一致。
- [ ] Application Pipeline Tab 不再显示旧简化列表、独立刷新或构建按钮。
- [ ] CI/CD 构建版本深链接继续工作，无 buildId 时自动选择最新版本并更新 URL。
- [ ] Application Tab 默认选中最新版本，切换构建不修改 Application 路由。
- [ ] 共享工作区卸载时停止轮询并拒绝旧请求。
- [ ] 父页面不为共享工作区重复发起构建历史和发布批次请求。
- [ ] 前端测试、类型检查、生产构建和 `./scripts/verify.sh` 通过。
- [ ] `docs/current-state.md` 更新为最终能力。

## 设计说明

详细设计见 `docs/superpowers/specs/2026-07-15-shared-application-build-workspace-design.md`。

## 验证证据

实现过程中补充。

## 完成

验收后记录日期并移至 `specs/completed/`。
