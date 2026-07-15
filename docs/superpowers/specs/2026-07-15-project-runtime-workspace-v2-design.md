# Project Runtime V2 设计

## 纠正目标

首版把 Environment 当成纵向内容分组、把 Pod 当成 Deployment 的附属折叠内容，导致当前上下文不明确、
列表不能扩展、Pod 详情需求缺失。V2 将 Environment 提升为整个页面的唯一作用域，将 Deployment 和
Pod 还原为可分页资源清单，并为 Pod 建立稳定的独立详情路由。

## Runtime 主页面

页面顶部使用环境选择器。当前环境写入 `?environment=<name>`；有效 URL 优先，其次恢复当前会话最近
选择，最后选择排序后的第一个有效环境。不存在或不属于当前 Project 的环境参数会被替换为有效值。

指标只统计当前环境：Deployment、健康 Pod、异常 Pod和累计重启。资源区使用 `Deployments` 与
`Pods` Tab。两个 Tab 都保留关键词、状态、页码和每页数量；切换环境或筛选条件时回到第一页。
默认每页 20 条，可选 20/50/100。表格只渲染当前页，空状态和当前环境连接失败分别显示。

Deployment 表包含 Application、Deployment 状态、Ready/Desired、Pod 数、重启数、镜像与 YAML/
滚动重启操作。Pod 表包含 Pod、Application、状态、Ready、Container 数、重启数、Node、创建时间；
Pod 名称进入独立详情页，日志、YAML、终端和删除不再挤在主表行内。

## API 与查询边界

新增环境目录接口供页面选择。Runtime 资源接口要求 `environment`、`resource`、`page`、`page_size`，
可选 `query` 和 `status`，响应 `{environment, summary, items, pagination, refreshed_at}`。后端只解析
当前 Project 中匹配该 Environment 名称的 Application Environment，逐个使用 Delivery Context
读取目标；同名 Environment 若错误绑定到不同 Cluster，返回上下文冲突错误而不是混合数据。

分页发生在返回前，搜索和状态筛选发生在 Service。Kubernetes 查询仍会访问当前环境下匹配的
Application 工作负载；本次不引入缓存或后台索引。接口形状允许以后用缓存或批量查询替换内部实现，
而无需改动页面。

## Pod 详情页

路由为：

`/devcenter/projects/:projectId/runtime/environments/:environment/applications/:applicationId/pods/:podName`

页面顶部提供返回当前环境 Pods 列表的面包屑、状态、Application、Namespace、Node、Pod IP、创建时间
和刷新。Overview 展示 Phase、Ready、QoS、Restart 与 Conditions；Containers 展示名称、镜像、状态、
Ready、Restart、启动时间以及 waiting/terminated 原因；Events 展示时间、类型、Reason、次数和消息。

Logs、YAML 和 Terminal 使用页面 Tab，而不是临时折叠行。Logs 选择 Container 与 100/500/1000/5000
Tail 行数；Terminal 延用现有票据与 WebSocket，实现只搬迁入口。删除 Pod 位于页面危险操作区。

Pod 详情 API 再次解析 Project/Application/Environment，并通过 `KubernetesService` 验证 Pod 标签归属；
返回标准化详情，不包含 Secret 或 kubeconfig。日志/YAML和终端继续使用已加固接口。

## 前端组件边界

- `ProjectRuntime.vue`：环境、资源 Tab、查询参数和分页编排。
- `RuntimeResourceTable.vue`：Deployment/Pod 表格展示和行事件，不发 HTTP 请求。
- `PodDetail.vue`：详情数据与 Tab 编排。
- `PodOverview.vue`：基础信息、Conditions、Containers、Events 纯展示。
- `RuntimeTerminalDrawer.vue`：保留现有终端传输职责。
- `frontend/src/api/runtime.ts`：统一 Runtime HTTP 请求。

删除 `RuntimeEnvironmentGroup.vue`，避免保留第二套入口和折叠交互。

## 错误、安全与测试

环境无效、跨 Project/Application 访问、Pod 标签不匹配分别返回稳定错误。单个工作负载查询失败时资源项
保留脱敏错误；环境上下文本身无效则整个请求失败。变更操作继续要求服务端 `confirmed: true`。

Service 测试覆盖单环境隔离、分页边界、搜索/状态筛选和环境冲突；Route 测试覆盖统一响应与资源归属。
Pod 详情测试覆盖 Conditions、Container 状态、Events 和脱敏。前端测试覆盖 URL 环境恢复、分页状态和
Tab 映射。浏览器验收验证大列表当前页 DOM 数、独立 Pod 路由、主要详情 Tab 与 390px 窄屏。
