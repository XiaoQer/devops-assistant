# 功能：嵌入式构建工作区顶部对齐

- 状态：已确认
- 负责人：Codex
- 创建日期：2026-07-15

## 背景

共享构建工作区嵌入 Application Pipeline Tab 后，历史栏的 80px sticky 偏移相对 Tab 容器生效，
造成左栏顶部留白并与右侧详情错位。

## 目标行为

Application Pipeline Tab 内左右两列顶边对齐；独立 CI/CD 页面仍避开全局导航吸顶。

## 范围

- 包含：Application 宿主级 sticky top 覆盖和编译验证。
- 不包含：共享内容、数据、路由、日志或轮询行为变化。

## 验收条件

- [ ] Application Pipeline Tab 的历史栏与构建详情顶部对齐，不再出现标记区域留白。
- [ ] 独立 CI/CD 页面仍使用 80px sticky 顶部偏移。
- [ ] 历史栏内部滚动和移动端复位行为保持不变。
- [ ] 前端测试、类型检查、生产构建和 `./scripts/verify.sh` 通过。

## 设计说明

详细设计见 `docs/superpowers/specs/2026-07-15-embedded-build-workspace-alignment-design.md`。

## 验证证据

实现过程中补充。

## 完成

验收后记录日期并移至 `specs/completed/`。
