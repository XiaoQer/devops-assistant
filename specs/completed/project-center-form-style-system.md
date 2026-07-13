# 功能：Project Center 统一表单样式

## 背景

Project Center 中多个新增/编辑弹窗仍使用默认或残留的深色 Dialog 样式，输入框巨大、
对比突兀，Kubernetes 集群和 Registry 表单尤其明显。此前只局部修了 Project 创建表单，
没有形成统一样式基座，导致后续表单继续复发。

## 目标

建立 Project Center 范围内统一的 Dialog/Form 样式基座。新增和编辑资源时，弹窗使用
浅色、紧凑、可读的表单布局，避免深色大背景配巨大白色输入框的观感。

## 范围

- 包含：在 Project Center 布局内提供统一弹窗表单样式。
- 包含：Kubernetes 集群新增/编辑弹窗接入统一样式。
- 包含：Registry 新增/编辑弹窗接入统一样式。
- 包含：按钮、标题、Label、Input、Textarea、Select、Switch 在弹窗中保持一致。

## 非目标

- 不改变 Kubernetes 集群或 Registry 后端 API。
- 不改变表单字段含义和保存 payload。
- 不处理 Project Center 以外模块的全部表单。

## 验收条件

- [x] Kubernetes 集群弹窗不再使用深色大背景和巨大输入框。
- [x] Registry 弹窗不再使用深色大背景和巨大输入框。
- [x] Project Center 弹窗标题、内容、footer、label、input、textarea、select、button
      使用统一浅色紧凑样式。
- [x] `./scripts/verify.sh` 通过。
