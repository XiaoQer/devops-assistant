# 功能：Project 表单提交体验优化

- 状态：已验收
- 负责人：shaoqian.li
- 创建日期：2026-07-13
- 验收日期：2026-07-13

## 背景

Project Center 的创建/编辑表单已经承载 Project 治理、GitHub 边界和 Aliyun 资源绑定
元信息。当前提交体验只有按钮 loading、toast 和简单手写校验；用户在提交失败、字段
缺失或保存中关闭弹窗时缺少明确反馈。

## 当前行为

- `frontend/src/views/ProjectCenter.vue` 使用 `saving` 控制保存按钮 loading。
- 必填项校验由 `save()` 内部手写 warning 完成，字段本身没有错误态。
- 保存失败只显示 toast，表单内没有错误摘要。
- 保存过程中仍可点击取消或关闭弹窗。

## 目标行为

Project 创建/编辑表单在提交时提供清晰、稳定的状态反馈：字段级校验、提交中说明、
防重复提交、错误摘要和更明确的成功提示。后端 API、数据模型和字段范围不变。

## 范围

- 包含：Project Center 表单使用 Element Plus 表单模型和规则校验。
- 包含：Project Name 和 Project Key 的字段级必填校验。
- 包含：保存中禁用取消、关闭和重复提交。
- 包含：表单底部展示提交中状态和 API 错误摘要。
- 包含：创建和更新使用不同成功提示。

## 非目标

- 不包含：新增后端字段或 API 行为。
- 不包含：抽取通用表单提交组件。
- 不包含：实现后端字段级错误定位协议。

## 验收条件

- [x] 给定 Project Name 或创建时 Project Key 为空，当用户提交时，则对应字段显示错误，
      且不发起 API 请求。
- [x] 给定表单正在保存，当用户点击保存、取消、遮罩或 ESC 时，则不会重复提交或关闭。
- [x] 给定 API 保存失败，当请求返回错误时，则表单内展示错误摘要，并保留用户输入。
- [x] 给定保存成功，当创建或更新完成时，则展示明确成功提示、关闭表单并刷新列表。
- [x] 前端类型检查和生产构建通过；`./scripts/verify.sh` 通过。

## 设计说明

本次只增强 `ProjectCenter.vue` 内部状态，不抽象公共组件。若后续多个表单需要相同提交
模式，再提炼 `FormSubmitBar` 或类似组件。

## 验证证据

- `npm run build`：Vue TypeScript 检查和 Vite 生产构建通过。
- `./scripts/verify.sh`：后端 83 个测试通过；前端类型检查和生产构建通过；验证命令
  输出 `Verification passed`。

## 完成

已于 2026-07-13 验收，归档到 `specs/completed/`。
