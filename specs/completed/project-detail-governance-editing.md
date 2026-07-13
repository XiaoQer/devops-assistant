# 功能：Project 列表去默认项与详情页治理信息编辑

## 背景

Project 是 Aegis 的顶层治理和工作空间边界。当前系统为了兼容历史数据，会自动维护
`key = default` 的系统默认 Project，并在应用缺少项目归属时作为兜底项目使用。

这个系统默认 Project 不代表真实业务项目，不应出现在用户默认进入的 Projects 页面中，
否则用户会把它误认为可治理的真实项目。同时，创建 Project 时保存的治理和 Aliyun /
GitHub 元信息已经进入后端模型，但 Project 详情页主要展示成员、应用、Kubernetes
集群和 Registry，缺少对 Project 本体元信息的集中展示和编辑入口。

## 目标

用户在 Project Center 中只看到真实业务 Project。创建 Project 时由系统生成或用户填写
的默认治理信息，应在 Project 详情页清晰展示，并可在详情页修改。

## 范围

- 包含：`GET /api/projects` 默认不返回 `key = default` 的系统默认 Project。
- 包含：Project 创建时保留默认元信息：`status = active`、
  `github_default_visibility = private`、`aliyun_region = cn-hangzhou`、
  `aliyun_binding_status = unbound`。
- 包含：Project 详情页展示 Project 本体治理信息，包括基础信息、负责人、GitHub 边界
  和 Aliyun 资源绑定。
- 包含：Project 详情页支持编辑 Project 本体字段：`name`、`description`、`status`、
  `business_owner`、`billing_owner`、`github_group`、
  `github_default_visibility`、`aliyun_account_id`、
  `aliyun_resource_group_id`、`aliyun_region`、`aliyun_vpc_id`、
  `aliyun_binding_status`。
- 包含：Project Center 列表和旧 ProjectList 都不展示系统默认 Project。
- 包含：更新文档，记录当前 Project 详情页已支持治理元信息编辑。

## 非目标

- 不删除数据库中的系统默认 Project。
- 不改变默认 Project 作为历史应用兜底归属的后端兼容职责。
- 不把成员、Kubernetes 集群、Registry 并入 Project 本体编辑表单。
- 不调用 GitHub 或 Aliyun API 初始化外部资源。
- 不存储 AccessKey、Secret、Token、密码、kubeconfig 等敏感凭据。

## 验收条件

- [x] 给定数据库中存在 `key = default` 的系统默认 Project，当调用 `GET /api/projects`
      时，则响应列表不包含该系统默认 Project。
- [x] 给定调用 `ProjectService.ensure_default_project()` 创建或返回系统默认 Project，
      当按 ID 查询详情时，仍可正常返回该 Project，用于兼容历史引用。
- [x] 给定只提交 `key` 和 `name` 创建真实 Project，当创建成功后，详情返回
      `status = active`、`github_default_visibility = private`、
      `aliyun_region = cn-hangzhou`、`aliyun_binding_status = unbound`。
- [x] 给定用户进入 Project 详情页，当 Project 存在治理元信息时，则页面展示基础信息、
      负责人、GitHub 边界和 Aliyun 绑定摘要；空字段显示为“未配置”。
- [x] 给定用户在 Project 详情页修改 Project 本体治理元信息，当保存成功并刷新详情时，
      修改后的字段保持一致。
- [x] 给定用户进入 Project 详情页，成员、Kubernetes 集群和 Registry 仍通过各自 Tab
      管理，不出现在 Project 本体编辑表单中。
- [x] `./scripts/verify.sh` 通过。
