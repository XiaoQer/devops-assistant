# 功能：Project 详情页分类展示与分类编辑

## 背景

Project 详情页已经从资源聚合页收敛为 Project 本体治理页，但当前页面默认直接展示编辑
控件，观感像一张大表单。Project 详情页应优先用于查看当前治理信息，只有用户明确选择
修改某一类信息时，才进入该分类的编辑状态。

## 目标

Project 详情页按照信息类别分开展示、分开修改。每个分类卡片默认展示字段值，点击该
分类的“修改”后只编辑该分类字段，保存时只提交该分类对应 payload。

## 范围

- 包含：Project 详情页默认展示态，不直接展示输入框。
- 包含：基础信息、Owner、GitHub、Aliyun 四类信息分开展示。
- 包含：每个分类有独立修改入口、保存和取消操作。
- 包含：每个分类保存时只提交该分类字段。
- 包含：Project Name 和 Project Key 始终只读，不允许修改。
- 包含：空字段展示为“未配置”。

## 非目标

- 不改变 Project 后端模型和 API。
- 不把 Kubernetes、Registry、Members 或 Applications 放回 Project 详情页。
- 不实现外部 GitHub 或 Aliyun API 同步。

## 验收条件

- [x] Project 详情页默认只展示分类信息卡片，不展示大面积输入表单。
- [x] 基础信息、Owner、GitHub、Aliyun 按类别分开展示。
- [x] 点击某一分类“修改”后，仅该分类进入编辑状态。
- [x] 保存基础信息时只提交 `description` 和 `status`。
- [x] 保存 Owner 时只提交 `business_owner` 和 `billing_owner`。
- [x] 保存 GitHub 时只提交 `github_group` 和 `github_default_visibility`。
- [x] 保存 Aliyun 时只提交 Aliyun 账号、资源组、区域、VPC 和绑定状态字段。
- [x] Project Name 和 Project Key 在所有状态下只读。
- [x] `./scripts/verify.sh` 通过。
