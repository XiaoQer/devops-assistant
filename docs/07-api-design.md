# 07. API Design

## 1. Purpose

本文件描述 Aegis 后端 API 的设计方式、资源划分、响应规范与当前主要��口能力。

它面向：
- 前端研发
- 后端研发
- 外部集成方
- AI / 智能代理

---

## 2. API Style

Aegis 当前主要采用：
- REST 风格资源接口
- JSON 作为数据交换格式
- 统一响应包装

接口前缀主要为：
- `/api/...`

---

## 3. Response Contract

当前平台统一返回结构中包含：

```json
{
  "success": true,
  "message": "Human-readable message",
  "data": {},
  "timestamp": "2026-07-02T12:00:00Z",
  "trace_id": "uuid"
}
```

### 3.1 Why It Matters

这个统一格式的价值在于：
- 前端处理成本降低
- 错误与成功结果更一致
- 对 AI 而言更容易建立稳定的上下文模式

---

## 4. Error Design

平台定义了统一错误码体系，例如：
- `APPLICATION_NOT_FOUND`
- `APPLICATION_EXISTS`
- `KUBERNETES_CONFIG_ERROR`
- `KUBERNETES_API_ERROR`
- `UNSUPPORTED_BUILD_TYPE`
- `RELEASE_NOT_FOUND`
- `NOT_FOUND`

建议前端和 AI 在消费 API 时，优先依据：
1. `success`
2. `error code`
3. `message`

进行处理。

---

## 5. Resource Groups

当前 API 可以按以下资源分组理解：

1. Applications
2. Environments
3. Configs
4. Releases
5. Pipelines
6. Approvals
7. Registries
8. Health

---

## 6. Applications API

## 6.1 Create Application
`POST /api/applications`

用途：
- 创建应用
- 触发仓库分析
- 生成 Application Spec
- 初始化默认环境

典型输入：
- `name`
- `repo_url`
- `branch`
- `namespace`

典型输出：
- `Application`
- `application_spec`

## 6.2 List Applications
`GET /api/applications`

用途：
- 获取应用列表
- 为首页、应用目录和命令系统提供数据

## 6.3 Get Application
`GET /api/applications/:id`

用途：
- 获取应用详情
- 为应用工作区提供主上下文

## 6.4 Deploy Application
`POST /api/applications/:id/deploy`

用途：
- 触发部署动作
- 根据目标环境决定直接执行还是提交审批

典型参数：
- `environment`
- `image_tag`（可选）
- `git_commit`（可选）

返回可能包括：
- `pipeline_run_name`
- `approval_required`
- `approval`

## 6.5 List Executions
`GET /api/applications/:id/executions`

用途：
- 获取该应用的 Pipeline 执行记录

## 6.6 List Releases
`GET /api/applications/:id/releases`

用途：
- 获取该应用的发布历史
- 支持按环境筛选

## 6.7 Rollback
`POST /api/applications/:id/rollback`

用途：
- 回滚到某条历史发布记录

输入典型包括：
- `release_id`
- `environment`

## 6.8 Runtime Status
`GET /api/applications/:id/status?environment=dev`

用途：
- 获取某应用在某环境下的运行态汇总

返回内容通常包括：
- deployment
- pods
- service
- ingress
- events
- replica sets
- PVC / ConfigMap / Secret 资源摘要

---

## 7. Environment API

## 7.1 List / Create Environment
`GET /api/applications/:id/environments`
`POST /api/applications/:id/environments`

用途：
- 查看环境
- 新建环境

## 7.2 Update / Delete Environment
`PATCH /api/applications/:id/environments/:environmentId`
`DELETE /api/applications/:id/environments/:environmentId`

用途：
- 更新环境参数
- 删除环境定义

## 7.3 Clone Environment
`POST /api/applications/:id/environments/:environmentId/clone`

用途：
- 从已有环境复制出新的环境配置

## 7.4 Compare Environments
`GET /api/applications/:id/environments/compare`

用途：
- 对比两个环境的配置差异

---

## 8. Configuration API

## 8.1 List Configs
`GET /api/applications/:id/configs`

用途：
- 查看指定环境、指定类型的配置项

参数常见包括：
- `environmentId`
- `type`

## 8.2 Create Config Version
`POST /api/applications/:id/configs`

用途：
- 新增配置项或配置版本

## 8.3 Update Config
`PATCH /api/configs/:configId`

用途：
- 更新已有配置内容

## 8.4 Delete Config
`DELETE /api/configs/:configId`

用途：
- 删除某个配置记录

## 8.5 Config History
`GET /api/configs/:configGroupId/history`

用途：
- 查询配置历史版本（未来可进一步强化）

---

## 9. Release API

## 9.1 Global Release List
`GET /api/releases?page=1&pageSize=20`

用途：
- 获取跨应用的发布活动流
- 支持分页、环境筛选、状态筛选

典型查询参数：
- `page`
- `pageSize`
- `environment`
- `status`

---

## 10. Pipeline API

## 10.1 Pipeline Status
`GET /api/pipelines/:name/status`

用途：
- 获取某个 PipelineRun 的状态概览

## 10.2 Pipeline Logs
`GET /api/pipelines/:name/logs`

用途：
- 获取结构化流水线日志
- 返回 Pipeline、Task、Step 多层级信息

这也是前端日志工作区与 AI 分析入口的重要数据源。

---

## 11. Approval API

## 11.1 List Approvals
`GET /api/approvals`

用途：
- 获取审批记录
- 支持状态与环境筛选

## 11.2 Submit Approval
`POST /api/approvals`

用途：
- 提交审批请求（通常由部署流程内部驱动）

## 11.3 Approve
`POST /api/approvals/:id/approve`

用途：
- 批准生产发布申请

## 11.4 Reject
`POST /api/approvals/:id/reject`

用途：
- 拒绝生产发布申请

---

## 12. Registry API

## 12.1 List Registries
`GET /api/registries`

## 12.2 Create Registry
`POST /api/registries`

## 12.3 Update Registry
`PATCH /api/registries/:id`

## 12.4 Delete Registry
`DELETE /api/registries/:id`

## 12.5 Set Default Registry
`POST /api/registries/:id/default`

用途：
- 管理平台级镜像仓库连接
- 控制默认镜像推送目标

---

## 13. Health API

## 13.1 Kubernetes Health
`GET /api/health/kubernetes`

用途：
- 快速验证后端是否能访问 Kubernetes 集群

这对本地开发与部署前自检非常重要。

---

## 14. Runtime Inspection API

除了应用级状态外，平台还提供更细的运行态接口：

### 14.1 Pod Logs
`GET /api/applications/:id/runtime/pods/:pod/logs`

### 14.2 Pod YAML
`GET /api/applications/:id/runtime/pods/:pod/yaml`

这些接口帮助前端构建：
- Pod 诊断视图
- 运行态排障工作区

---

## 15. API Design Characteristics

当前 API 设计具有以下特征：

### 15.1 Resource-Oriented
大多数接口都围绕明确的业务资源组织，而不是纯动作型 RPC。

### 15.2 Application-Centric
绝大多数 API 都与 `Application` 有强关联，这符合平台的核心建模。

### 15.3 Workflow-Aware
虽然是 REST 风格，但接口已经体现了完整工作流，例如：
- deploy
- rollback
- approve
- clone environment
- compare environments

### 15.4 Frontend-Friendly
当前 API 已较适合前端工作区式界面使用，返回结构也相对直接。

---

## 16. Improvement Suggestions

未来可以继续加强：

### 16.1 Explicit Request / Response Schemas
建议引入更明确的 schema 层，例如：
- Pydantic models
- OpenAPI 文档

### 16.2 Consistent Pagination Contract
当前部分接口已有分页，未来应统一分页协议。

### 16.3 Better Async Action Semantics
像 deploy / rollback / approval 这类动作，未来可进一步标准化返回：
- action id
- job id
- next step
- async status url

### 16.4 AI-First APIs
未来可增加面向 AI 的接口，例如：
- `/api/ai/intent/resolve`
- `/api/ai/recommendations`
- `/api/ai/analyze/pipeline/:name`
- `/api/ai/analyze/application/:id`

---

## 17. Summary

Aegis 当前 API 已经形成了一个清晰的平台资源体系：

- Applications 作为中心资源
- Environments / Configs 作为交付上下文资源
- Releases / Approvals / Pipelines 作为交付流程资源
- Registries / Health 作为平台基础设施资源

这种设计既利于前端构建工作区界面，也利于 AI 在明确上下文下参与平台交互。

