# Aegis Agent 工作指南

本仓库使用编码 Agent 协作开发。项目事实以仓库为准，不以某次聊天记录为准。

## 每次任务开始前

1. 阅读 `docs/product.md`、`docs/architecture.md` 和 `docs/current-state.md`。
2. 阅读 `specs/active/` 中对应的需求规格。如果行为变更尚无规格，先根据
   `specs/template.md` 创建规格，再开始实现。
3. 检查 `git status` 并保留用户已有修改，不恢复、丢弃或重写无关工作。
4. 根据当前代码验证文档中的说法。文档表达意图，代码和可执行检查证明当前行为。

## 产品与架构约束

- `Project` 是治理和工作空间边界。
- `Application` 是项目内部的交付聚合。
- 业务状态存储在 MySQL，执行状态来自 Kubernetes/Tekton。
- 后端 HTTP 处理器负责传输层校验，业务行为委托给 Service。
- Kubernetes 连接集中在 `KubernetesService`；Tekton 资源操作集中在
  `TektonService`。
- 前端 HTTP 请求集中在 `frontend/src/api`，不直接写在 View 中。
- 保持统一 API 响应结构：`success`、`message`、`data`、`timestamp`、
  `trace_id`。
- 影响生产或具有破坏性的操作必须显式确认或审批。
- API、日志、测试数据和文档中不得暴露镜像仓库凭据或应用 Secret。

## 变更流程

1. 在活跃规格中记录背景、范围、非目标和验收条件。
2. 实现满足规格的最小完整改动。
3. 为行为变化补充或更新自动化检查。
4. 运行 `./scripts/verify.sh`。
5. 能力状态变化时更新 `docs/current-state.md`。
6. 出现长期架构选择时，在 `docs/decisions/` 中新增 ADR。
7. 验收后将规格从 `specs/active/` 移至 `specs/completed/`。

## 完成定义

- 每条验收条件都有证据。
- 相关自动化测试存在且通过。
- 修改前端时，类型检查和生产构建通过。
- 修改数据库模型时，包含 Alembic migration。
- 文档反映最终状态，不把计划中的能力写成已实现。
- 明确记录已知缺口，不保留未说明的占位实现或虚假成功。

## 验证方式

运行：

```bash
./scripts/verify.sh
```

验证命令必须保持非交互，并能安全地在本地和 CI 中运行。单元检查不得依赖在线
Kubernetes 集群。
