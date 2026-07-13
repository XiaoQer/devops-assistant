# 功能：Project 详情页信息架构精简

## 背景

Project 详情页当前同时承载 Project 本体治理信息、应用列表、成员、Kubernetes 集群和
Registry 管理。这个页面已经变成“所有东西都放一点”的聚合页，和当前架构边界不一致：
Project 本体应只承载治理和云资源元信息，成员、应用、Kubernetes 集群和 Registry 应
通过独立资源入口管理。

## 目标

Project 详情页改为清晰的 Project 本体治理页。Kubernetes 环境配置和 Registries 从详情
页拆出去，放到 Project Center 的独立菜单入口。Project 名称和 Project Key 作为身份字段
只读展示，不在详情页修改。

## 范围

- 包含：Project 详情页删除 Applications、Members、Kubernetes、Registries Tab。
- 包含：Project 详情页删除顶部 Applications / Members / Clusters / Registries 仪表卡。
- 包含：Project 详情页只展示和编辑 Project 本体治理元信息。
- 包含：Project Name 和 Project Key 在详情页只读展示，不允许修改。
- 包含：Project Center 项目级菜单新增 Kubernetes 和 Registries 独立入口。
- 包含：Kubernetes 集群管理迁移到独立页面。
- 包含：Registry 管理迁移到独立页面。
- 包含：详情页提供轻量跳转到 Kubernetes 和 Registries 配置页面。

## 非目标

- 不改变 Project 后端模型和 API。
- 不删除成员、应用、Kubernetes 集群或 Registry 的既有数据。
- 不在本次实现 DevCenter 应用交付流程调整。
- 不实现 GitHub 或 Aliyun 外部资源初始化。

## 验收条件

- [x] Project 详情页不再显示 Applications、Members、Clusters、Registries 四个仪表卡。
- [x] Project 详情页不再显示 Applications、Members、Kubernetes、Registries Tab。
- [x] Project 详情页中的 Project Name 和 Project Key 为只读展示字段，保存 Project
      治理信息时不会提交 `name` 或 `key`。
- [x] Project 详情页可编辑状态、描述、负责人、GitHub 边界和 Aliyun 资源绑定字段。
- [x] Project Center 项目级侧边栏包含 Kubernetes 和 Registries 独立菜单。
- [x] Kubernetes 独立页面支持项目内集群列表、新增、编辑、删除和设置默认集群。
- [x] Registries 独立页面支持项目内 Registry 列表、新增、编辑、删除和设置默认 Registry。
- [x] `./scripts/verify.sh` 通过。
