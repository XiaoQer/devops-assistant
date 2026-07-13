# 功能：Project 下接入已有 Kubernetes 集群

- 状态：已确认，待实现
- 负责人：Aegis Agent
- 创建日期：2026-07-13

## 背景

项目负责人需要在 Project 治理边界内登记可用的 Kubernetes 集群，并在把集群用于
Application Environment 前确认控制面能够访问该集群。产品同时需要展示未来通过
Project 的 Aliyun 绑定自动初始化 ACK 集群的方向，但本期不调用 Aliyun API，也不创建
任何云资源。

## 当前行为

- `frontend/src/views/ProjectKubernetesSettings.vue` 已提供项目级集群列表、新增、编辑、
  删除和设置默认集群。
- `backend/app/models/kubernetes_cluster.py` 仅保存名称、kube context、Namespace 前缀、
  API Server、默认和启用状态，不保存可供该集群独立连接的凭据。
- `backend/app/services/kubernetes_service.py` 只加载控制面运行环境的默认 kubeconfig 或
  in-cluster 配置，无法按项目中登记的集群创建客户端。
- 现有集群登记没有环境标签、保存前测试、保存后重测或最近测试状态。

## 目标行为

用户点击“添加集群”后可看到“初始化新 Kubernetes 集群”和“添加已有集群”两个入口。
初始化入口仅说明未来会使用 Project 的 Aliyun 能力自动创建集群，并明确标记为即将支持。
添加已有集群允许用户粘贴完整 kubeconfig、选择其中的 context、设置单个环境标签并测试
Kubernetes API 连通性。kubeconfig 只以密文持久化，任何 API 响应和日志均不得暴露明文、
密文、Token、证书或私钥。

## 范围

- 包含：添加入口选择界面，以及不可提交的 Aliyun 初始化能力展示。
- 包含：已有集群的名称、环境标签、kubeconfig、context、Namespace Prefix、描述、默认
  和启用状态配置。
- 包含：内置 `development`、`testing`、`staging`、`production` 环境标签并允许自定义
  单值标签。
- 包含：解析 kubeconfig 中的 contexts，默认选中 `current-context` 并允许改选。
- 包含：保存前测试未持久化配置，以及保存后对已登记集群重测。
- 包含：保存最近一次测试状态、时间、Kubernetes 版本和测试成功时的实际 API Server。
- 包含：既有集群数据的兼容迁移、后端自动化检查、前端类型检查和生产构建。

## 非目标

- 不包含：调用 Aliyun API、创建 ACK 集群、轮询云资源创建进度或产生云资源费用。
- 不包含：要求 Tekton 已安装，或验证 Namespace、部署和集群管理员权限。
- 不包含：多个环境标签、键值标签或环境到多集群调度策略。
- 不包含：外部 Vault/KMS、独立集群凭据表、凭据版本历史或自动轮换。
- 不包含：把 kubeconfig 明文或密文返回前端。

## 验收条件

- [ ] 给定用户进入 Project 的 Kubernetes 页面，当点击“添加集群”时，则同时看到“初始化
  新 Kubernetes 集群”和“添加已有集群”入口，且前者明确不可用并说明依赖 Aliyun 能力。
- [ ] 给定合法 kubeconfig 包含多个 contexts，当用户粘贴配置时，则默认选中
  `current-context`，并可选择其他 context。
- [ ] 给定内置或自定义环境标签，当用户保存已有集群时，则标签随集群持久化并在列表展示。
- [ ] 给定合法 kubeconfig，当用户保存集群时，则数据库只保存 Fernet 密文，序列化只返回
  `has_kubeconfig`，不返回 kubeconfig 明文或密文。
- [ ] 给定编辑已有集群，当页面打开编辑表单时，则 kubeconfig 不回显；留空保存会保留原凭据，
  提交新 kubeconfig 会替换凭据并把连接状态重置为 `untested`。
- [ ] 给定尚未保存的合法配置，当用户点击“测试连接”时，则系统使用表单 kubeconfig 和所选
  context 请求 Kubernetes Version API，并返回连接状态、API Server 和 Kubernetes 版本，
  不写入集群记录。
- [ ] 给定已保存集群，当用户点击“测试连接”时，则系统解密该集群的 kubeconfig 完成同样测试，
  并更新 `connection_status`、`last_checked_at`、`kubernetes_version`；成功时更新实际
  `api_server`。
- [ ] 给定网络、认证或证书错误，当执行连通性测试时，则接口返回 `connected: false` 和脱敏的
  分类消息，不要求测试成功才允许保存，也不长期保存失败详情。
- [ ] 给定包含 `exec` 认证、本地证书/密钥/Token/CA 文件引用、非 HTTPS Server、缺失所选
  context 或超过 1 MiB 的 kubeconfig，当测试或保存时，则请求以明确的 400 错误被拒绝。
- [ ] 给定其他 Project 的 cluster id，当请求重测时，则返回项目作用域内的不存在响应，不能
  使用或泄露该集群配置。
- [ ] 给定迁移前已有集群，当升级数据库后，则记录保留，环境标签可为空、状态为 `untested`、
  `has_kubeconfig` 为 false，并可通过编辑补充新字段。
- [ ] 所有新增 API 继续使用 `success`、`message`、`data`、`timestamp`、`trace_id` 统一结构。
- [ ] 相关迁移、Service 和路由自动化检查通过，前端类型检查、生产构建和
  `./scripts/verify.sh` 通过。
- [ ] `docs/current-state.md` 只在验证完成后记录该能力已实现，并保留 Aliyun 初始化尚未实现
  的边界。

## 设计说明

- 扩展现有 `KubernetesCluster`，不新增业务聚合。新增字段包括 `environment_label`、
  `encrypted_kubeconfig`、`connection_status`、`last_checked_at` 和
  `kubernetes_version`。
- 加解密沿用 Registry 和 Application Config 已采用的 Fernet 方式，由 Flask
  `SECRET_KEY` 派生密钥。模型序列化仅暴露布尔型 `has_kubeconfig`。
- `KubernetesClusterService` 负责输入校验、凭据加解密、默认集群规则和测试结果持久化；
  `KubernetesService` 集中负责从指定 kubeconfig/context 构建 Kubernetes 客户端和请求
  Version API。
- 未保存测试使用 `POST /api/projects/:projectId/clusters/test-connection`；已保存重测使用
  `POST /api/projects/:projectId/clusters/:clusterId/test-connection`。
- kubeconfig 明文只存在于请求生命周期、前端表单内存和 Kubernetes 客户端构造过程。关闭
  表单后前端清空明文，后端不记录原始异常文本。
- 连接测试设置较短超时。配置结构错误是 400；合法配置的网络、认证或证书失败是正常测试结果，
  以 `connected: false` 返回。

## 验证证据

- 2026-07-13：用户逐项确认认证方式、环境标签形式、连通性测试规则、context 选择、
  数据设计、页面/API 流程、安全边界、测试范围和验收条件。
- 2026-07-13：规格自审未发现未定项、内部矛盾或超出本期范围的实现要求。

## 完成

全部验收条件有证据后，将状态改为“已验收”，记录日期，并把本文件移至
`specs/completed/`。
