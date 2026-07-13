# Project 详情页后台化外壳

## 背景

Project 详情页的核心设置面板已经改为单列设置行，但顶部 Project Identity 仍是偏
Portal/Hero 的展示区，底部 Kubernetes environments 与 Container registries 仍是大卡片入口。
这些区域和后台详情页的信息密度、视觉语气不一致。

## 范围

- 将顶部 Project Identity Hero 改为紧凑的后台详情摘要栏。
- 将 Project Key、状态、Owner、GitHub、Aliyun 摘要作为小型字段块展示。
- 移除顶部大标题、渐变背景、胶囊式 Kubernetes/Registries 快捷按钮。
- 将底部 Kubernetes 和 Registry 入口改为关联资源管理列表。
- 保留刷新、Kubernetes 配置、Registries 配置按钮和路由跳转能力。

## 非目标

- 不修改 Project 列表页。
- 不修改 Project 本体字段、后端 API 或保存逻辑。
- 不把 Kubernetes 和 Registry 管理重新嵌回详情页；它们仍走独立菜单。

## 验收条件

- 顶部区域看起来像后台详情页摘要，而不是营销 Hero。
- 底部入口看起来像关联资源列表，而不是宣传卡片。
- Kubernetes 与 Registry 入口仍可点击进入对应配置页。
- Project 设置面板的分类编辑能力不受影响。
- 前端构建和仓库验证通过。
