# 功能：Project 详情页视觉优化

## 背景

Project 详情页已经支持分类展示和分类编辑，但当前视觉仍偏工程表单：卡片边框较重、
字段块过多、页面层级不够清晰。用户需要的是一个默认可读、按需编辑的 Project 治理
详情页，而不是后台 CRUD 表格页。

## 目标

在不改变业务字段和 API 的前提下，优化 Project 详情页视觉层级和分类卡片交互，使页面
更像治理设置页：先展示摘要和关键信息，再按基础信息、Owner、GitHub、Aliyun 分类维护。

## 范围

- 包含：优化 Project Hero 区域，突出名称、Key、状态、描述和治理摘要。
- 包含：优化分类卡片展示态，减少重边框和表格感。
- 包含：优化分类卡片编辑态，让保存/取消操作只影响当前分类。
- 包含：保持 Project Name 和 Project Key 只读。
- 包含：保持 Kubernetes 和 Registries 作为独立菜单入口。

## 非目标

- 不改变 Project 后端模型或 API。
- 不改变分类保存 payload。
- 不把 Members、Applications、Kubernetes 或 Registries 放回详情页主体。

## 验收条件

- [x] Project 详情页默认不是大面积表单，而是 Hero + 分类详情卡片。
- [x] 基础信息、Owner、GitHub、Aliyun 卡片视觉上有清晰分组和摘要。
- [x] 每个分类只在点击“修改”后显示输入控件。
- [x] Project Name 和 Project Key 只读。
- [x] `./scripts/verify.sh` 通过。
