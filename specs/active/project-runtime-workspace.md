# 功能：Project Runtime 工作台

- 状态：已确认
- 负责人：Codex
- 创建日期：2026-07-15

## 背景

DevCenter 的 Runtime 菜单当前复用 Application 列表，无法从 Project 视角判断不同环境中
Deployment 和 Pod 的实际运行情况。用户需要一个接近 Kubernetes Dashboard 信息密度、但仍以
Project、Application 和 Environment 为边界的运行工作台，并需要在明确治理下执行常用运维操作。

## 当前行为

- `/devcenter/projects/:projectId/runtime` 指向 `ApplicationList.vue`，没有独立 Runtime 页面。
- Application 详情能够按单个环境读取 Deployment、Pod、Service、Ingress、Event 和附属资源，
  并支持查看 Pod 日志与 YAML。
- Kubernetes 访问集中在 `KubernetesService`，Application 的目标集群由 Delivery Context 解析。
- 当前没有 Project 级运行态聚合、Deployment 重启、Pod 删除、交互式 Pod Exec 或相应审计能力。

## 目标行为

Runtime 页面按环境分组汇总当前 Project 下所有 Application 的 Deployment 与 Pod 状态。用户可以
从汇总行展开 Pod、查看日志和 YAML，并在二次确认后滚动重启 Deployment、删除 Pod；用户还可以
填写操作原因后进入受控的浏览器交互式 Pod 终端。

## 范围

- 包含：Project 级 Runtime 聚合 API，按 Application Environment 解析实际 Kubernetes 目标。
- 包含：环境、状态和关键词筛选，手动刷新与可控自动刷新，环境级局部错误展示。
- 包含：Deployment/Pod 状态与 YAML、Pod 日志、Deployment 滚动重启和 Pod 删除。
- 包含：选择 Container 后建立浏览器交互式终端、会话授权、超时和并发限制。
- 包含：生产环境风险提示、所有变更操作二次确认、终端操作原因和运维审计。
- 包含：相关后端、前端和安全边界自动化检查以及用户文档更新。

## 非目标

- 不按 Cluster/Namespace 任意浏览非 Aegis Application 资源。
- 不提供节点级资源管理、文件上传下载、端口转发或终端内容回放。
- 不在本功能中引入完整 RBAC；继续使用现有登录用户与 Project/Application 资源边界。
- 不持久化终端输入输出，避免命令或输出中的 Secret 进入审计数据。
- 不实现监控指标、告警规则或 Kubernetes Event 生命周期管理。

## 验收条件

- [ ] 给定当前 Project 有多个 Application Environment，当打开 Runtime 时，则按环境展示各
      Application 的 Deployment 和 Pod 摘要，并显示 Deployment、健康/异常 Pod 和重启次数指标。
- [ ] 给定某个环境或集群不可达，当刷新 Runtime 时，则该环境显示脱敏错误，其他环境仍正常展示。
- [ ] 用户能够按环境、健康状态和关键词筛选，能够手动刷新并开启或关闭自动刷新。
- [ ] 用户能够查看已归属当前 Application Environment 的 Deployment/Pod YAML 和 Pod 日志；
      跨 Project、跨 Application、跨环境或不存在的资源请求被拒绝。
- [ ] 用户二次确认后能够滚动重启 Deployment 或删除 Pod；生产环境显示明确风险提示。
- [ ] 用户选择 Container、填写操作原因并确认后能够进入交互式终端；未授权、过期、超出并发限制
      或目标上下文漂移的会话被拒绝，空闲 15 分钟的会话自动关闭。
- [ ] 重启、删除和终端会话记录操作者、Project、Application、环境、集群、Namespace、目标、
      原因、开始/结束时间与结果，但不记录终端输入输出或 Secret。
- [ ] HTTP API 继续使用统一响应结构；WebSocket 在握手失败和会话关闭时返回可识别的安全错误。
- [ ] 后端测试、前端类型检查和生产构建通过，`./scripts/verify.sh` 通过，并完成人工浏览器验收。
- [ ] `docs/current-state.md` 只在能力通过验收后更新为已实现。

## 设计说明

详细设计见 `docs/superpowers/specs/2026-07-15-project-runtime-workspace-design.md`。

## 验证证据

实现过程中补充。

## 完成

验收后将状态改为“已验收”，记录日期，并把文件移至 `specs/completed/`。
