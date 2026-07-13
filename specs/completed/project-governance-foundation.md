# 功能：Project 治理元信息基础

- 状态：已验收
- 负责人：shaoqian.li
- 创建日期：2026-07-13
- 验收日期：2026-07-13

## 背景

Aegis 的 `Project` 应当是一个真实项目单位的顶层治理边界。一个 Project 会关联公司
人员、GitHub 代码组织边界、Aliyun 账号与资源组、Kubernetes 集群组、镜像仓库以及
后续 DevCenter 中的应用交付工作区。

当前实现已经有项目 CRUD、成员、Kubernetes 集群和镜像仓库等子资源，但 Project
本体只持久化 `key`、`name` 和 `description`。前端 Project Center 表单已经展示了
`status`、`cloud_provider`、`region`、`resource_group`、`billing_owner` 等字段，
但后端不会保存这些字段，导致用户看到的治理与云资源信息不是可信的平台事实。

本阶段先把 Project 本体打造成“治理边界 + 云资源/GitHub 绑定元信息”的可信记录。
成员、GitHub 初始化、Aliyun 资源初始化、Kubernetes 集群、镜像仓库仍作为 Project
下的独立子资源或后续工作流处理。

## 当前行为

- `backend/app/models/project.py` 的 `Project` 只保存 `key`、`name`、`description`
  和时间戳。
- `backend/app/services/project_service.py` 的创建和更新只处理基础字段；创建时可选
  初始化一个 owner 成员。
- `backend/app/routes/projects.py` 已提供 Project 的 list/get/create/update/delete，
  并提供成员与 Kubernetes 集群子资源路由。
- `backend/app/models/kubernetes_cluster.py` 已经把 Kubernetes 集群作为 Project
  子资源保存，支持同一 Project 下多个集群和默认集群。
- `frontend/src/views/ProjectCenter.vue` 的创建/编辑表单展示云厂商、区域、资源组、
  billing owner 等字段，但这些字段没有后端模型支撑，保存后不会落库。
- GitHub 当前主要体现在 Application 的 `repo_url`，没有 Project 级 GitHub 组织、
  team 或仓库组绑定模型。
- Aliyun 当前没有后端模型或服务；仓库内也没有 Aliyun 账号、资源组、RAM 或 ACK
  初始化工作流。

## 目标行为

Project 本体保存并返回项目治理和外部资源绑定元信息。用户在 Project Center 创建或
编辑 Project 时，表单中的字段应与后端真实字段一致，保存后可在列表和详情中恢复。

Project 的云资源字段以 Aliyun 为主要目标进行命名和边界设计：记录可公开展示的账号
与资源组元信息，不保存 AccessKey、Secret、Token 或任何应用 Secret。

本阶段不执行 GitHub、Aliyun 或 Kubernetes 的外部初始化动作，只为后续显式、可审计
的初始化工作流建立可信 Project 上下文。

## 范围

- 包含：扩展 Project 模型，保存 `status`、`business_owner`、`billing_owner`、
  `github_group`、`github_default_visibility`、`aliyun_account_id`、
  `aliyun_resource_group_id`、`aliyun_region`、`aliyun_vpc_id`、
  `aliyun_binding_status` 等元信息字段。
- 包含：新增 Alembic migration，保证本地和 CI 可验证 schema 演进。
- 包含：Project 创建、更新、查询和列表返回新增字段，并保持统一 API 响应结构。
- 包含：后端校验字段长度、状态枚举和 Aliyun 绑定状态枚举；错误使用稳定错误码。
- 包含：Project Center 创建/编辑表单按“基础信息、人员归属、GitHub 边界、Aliyun
  资源绑定”分区展示，并只提交后端真实支持的字段。
- 包含：Project 卡片或详情摘要展示 GitHub 边界、Aliyun 账号/资源组、区域和绑定
  状态。
- 包含：自动化检查覆盖新增字段的创建、更新、返回、校验和 migration。
- 包含：更新 `docs/current-state.md`，只记录本阶段实际实现能力。

## 非目标

- 不包含：调用 GitHub API 创建 organization、team、repo 或同步成员。
- 不包含：调用 Aliyun API 创建资源组、VPC、RAM 权限、ACK/Kubernetes 集群。
- 不包含：把 Project 成员自动同步到 GitHub、Aliyun RAM 或 Kubernetes RBAC。
- 不包含：把 Kubernetes 集群字段塞进 Project 本体；集群继续作为 Project 子资源。
- 不包含：保存 AccessKey Secret、GitHub Token、Kubernetes kubeconfig 或应用 Secret。
- 不包含：项目级 RBAC 强制授权；当前身份认证仍不做项目角色强制校验。

## 验收条件

- [x] 给定 Project 创建请求包含基础信息、GitHub 边界和 Aliyun 绑定元信息，当创建
      成功时，则响应和后续查询都返回这些字段。
- [x] 给定 Project 更新请求修改 GitHub 边界、Aliyun 资源组、区域、VPC 或状态，当
      更新成功时，则旧值被替换，列表和详情保持一致。
- [x] 给定未知 `status` 或 `aliyun_binding_status`，当创建或更新 Project 时，则
      返回 `400` 和稳定错误码，不写入数据库。
- [x] 给定 AccessKey、Secret、Token、password 等敏感字段出现在 Project payload 中，
      当创建或更新 Project 时，则请求被拒绝或字段被明确忽略，响应中不回显敏感值。
- [x] 给定 Project 下已有成员、应用、Kubernetes 集群或 Registry，当删除 Project
      时，则仍返回 `409 / PROJECT_NOT_EMPTY`。
- [x] 给定 Project Center 创建或编辑 Project，当保存成功并重新加载页面时，则表单
      中的 GitHub 和 Aliyun 元信息可恢复显示。
- [x] 前端 Project 表单不再展示后端不支持的“伪字段”；默认 Kubernetes 集群创建
      入口不放在 Project CRUD 表单里。
- [x] 相关后端自动化检查覆盖新增字段、校验和 migration；前端类型检查和生产构建通过。
- [x] `./scripts/verify.sh` 通过，`docs/current-state.md` 准确记录已实现能力和已知缺口。

## 设计说明

### Project 边界

Project 是治理根对象，保存项目身份、业务归属和外部系统绑定的元信息。它不直接承载
成员列表、集群列表、Registry 列表或应用列表的内部字段；这些继续通过已有子资源和
后续专门模型管理。

### GitHub 边界

本阶段只记录 Project 计划关联的 GitHub 组边界，例如 organization/team/repo group
标识和默认仓库可见性。真正的 GitHub 初始化和项目成员同步需要后续独立工作流，并且
必须可审计、可重试、可展示部分失败。

### Aliyun 边界

Aliyun 是主要云目标。Project 可保存账号 ID、资源组 ID、区域、VPC ID 和绑定状态。
这些字段用于说明 Project 后续初始化云资源和 Kubernetes 集群时的云资源边界。

敏感凭据不得进入 Project 表、API 响应、测试数据或日志。后续 Aliyun API 凭据应由
专门的凭据管理或 Secret 边界承载。

### Kubernetes 边界

Kubernetes 集群可能按环境存在多个，例如 dev、test、staging、prod。当前已有
`KubernetesCluster` Project 子资源可登记多个集群和默认集群。本阶段不改变该边界。
DevCenter 中的 Application 后续应通过 Project 下的环境与集群绑定判断部署目标。

### 备选方案

- 通用 `cloud_provider` 字段可同时表达 Azure/AWS/Aliyun，但会弱化当前产品主目标，
  也容易把 Aliyun 资源组、账号和 VPC 设计成含混字符串。本阶段不采用。
- 在创建 Project 时立即初始化 GitHub、Aliyun 和 Kubernetes 资源看似顺手，但会让
  CRUD 请求承担大量外部副作用，失败后难以重试和审计。本阶段不采用。
- 把 Kubernetes 集群字段放进 Project 本体只适合单集群项目，无法表达多环境多集群。
  继续使用 Project 子资源模型。

## 差距分析

当前代码与目标模型的主要差距如下：

- Project 本体缺少治理归属、GitHub 边界和 Aliyun 资源绑定字段。
- Project Center 表单存在后端不保存的字段，造成“看起来能填，实际没有平台事实”的
  体验断层。
- GitHub 尚无 Project 级绑定概念；Application 只保存单个仓库 URL。
- Aliyun 尚无账号、资源组、区域、VPC 或绑定状态模型。
- Kubernetes 集群已经是 Project 子资源，但尚未按环境绑定到 DevCenter 的部署目标
  体验中；这是后续工作，不应混入本次 Project CRUD。

## 验证证据

- `../backend/.venv/bin/python -m pytest tests/test_project_routes.py -q`：
  8 passed，覆盖 Project 元信息创建、更新、非法枚举、敏感字段拒绝和原有子资源行为。
- `../backend/.venv/bin/python -m pytest tests/test_project_governance_migration.py -q`：
  1 passed，覆盖 `a7c8d9e0f1a2` 到 `c3d4e5f6a7b8` 的升级和降级。
- `npm run build`：Vue TypeScript 检查和 Vite 生产构建通过。
- `./scripts/verify.sh`：后端 83 个测试通过；前端类型检查和生产构建通过；验证命令
  输出 `Verification passed`。

## 完成

已于 2026-07-13 验收，归档到 `specs/completed/`。
