# 领域模型

## 聚合层级

```text
Project
├── ProjectMember
├── KubernetesCluster
├── ContainerRegistry
└── Application
    ├── ApplicationEnvironment
    │   └── ApplicationConfig
    ├── PipelineExecution
    ├── ReleaseRecord
    └── ApprovalRecord
```

## Project（项目）

项目是治理和工作空间边界，包含稳定标识和显示名称。成员、集群、镜像仓库和应用
归属于项目或受项目范围约束。

当前成员角色包括 `owner`、`admin`、`developer` 和 `viewer`。这些角色已经存储并
校验，但尚未实现完整的请求鉴权。

## Application（应用）

应用表示源自代码仓库的可部署软件单元，保存检测到的构建元数据和应用规格。应用
属于项目，并拥有交付相关记录。

## ApplicationEnvironment 与配置

环境定义应用的目标集群、Namespace、资源策略、部署策略、Ingress 和审批要求。
配置记录支持版本化，并关联应用以及适用的环境。

## 执行与发布

`PipelineExecution` 表示技术执行状态，`ReleaseRecord` 表示部署或回滚的业务历史。
二者分离，避免 Tekton 资源生命周期成为平台唯一的交付记录。

## Approval（审批）

审批记录受治理的交付请求、审核决定以及批准后启动的执行。标记为需要审批的环境
不得绕过该流程。

## 镜像仓库与集群

镜像仓库提供镜像目标和凭据；Kubernetes 集群提供项目级执行目标；应用环境可以
选择具体集群。

## 领域不变量

- Project Key 唯一。
- 成员邮箱在同一项目内唯一。
- 环境名称在同一应用内唯一。
- 非空项目不能删除。
- 同一作用域内最多只能有一个默认镜像仓库或默认集群。
- 受治理的环境在审批前不能部署。
- 回滚目标必须来自有效发布历史。
- Secret 值不得以明文越过 API 或日志边界。
