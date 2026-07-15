# Project Runtime 工作台设计

## 目标与原则

Runtime 是 Project 内的运行事实入口，不是通用 Kubernetes 资源浏览器。页面按照 Environment
组织 Application 的 Deployment 和 Pod，让开发者先看健康与异常，再按需进入资源细节和受治理
操作。所有目标资源都必须从服务端的 Project → Application → Environment 上下文解析，前端不能
通过传入 Cluster 或 Namespace 绕过治理边界。

## 页面设计

页面顶部提供环境筛选、健康状态筛选、Application/资源关键词搜索、手动刷新和自动刷新开关。
概览区域展示环境数、Deployment 数、健康 Pod、异常 Pod 和累计重启次数。自动刷新默认开启，
间隔为 30 秒，用户可以关闭；页面不可见时暂停刷新。

主体按环境折叠分组。每个环境显示集群、Namespace、总体健康和刷新错误；环境内每个 Application
以一行 Deployment 摘要呈现期望/就绪副本、镜像和状态，展开后显示 Pod、Ready、阶段、重启次数、
Node 与操作。日志、YAML 和终端使用右侧抽屉，终端抽屉使用较大宽度。Deployment 菜单提供 YAML
和滚动重启；Pod 菜单提供日志、YAML、进入终端和删除。

生产环境的变更操作使用危险样式与明确环境文案。重启和删除都要求二次确认。终端在选择 Container
后要求填写操作原因，再创建会话。空数据区分“Project 尚无 Application/Environment”“尚未部署”
和“连接失败”，避免把基础设施错误显示成空白成功。

## 后端边界与数据流

新增 Project Runtime 路由与 Service。Route 只解析筛选参数和调用 Service；Service 列出当前
Project 的 Application Environment，使用 Delivery Context 与 `KubernetesClusterService` 获取
客户端，并由 `KubernetesService` 查询运行资源。聚合响应包含环境/Application/Deployment/Pod 摘要
和逐项错误。单个目标查询失败被转换为脱敏的局部错误，不中止其他目标。

日志与现有 Pod YAML 接口继续复用。新增 Deployment YAML、滚动重启、Pod 删除、Pod Containers
和 Exec Session 创建接口。每个接口先解析 Application Environment，再验证 Kubernetes 返回资源
属于目标工作负载。资源名称不能单独决定授权。

前端只通过 `frontend/src/api` 请求 HTTP 接口。Project Runtime View 管理筛选和刷新，环境分组、
Deployment 行、Pod 列表和资源抽屉拆为职责单一的组件；Application 详情保留现有 Runtime 面板，
共享适合复用的日志/YAML抽屉能力，不复制请求逻辑。

## 运维操作与审计

Deployment 重启通过更新 Pod Template annotation 触发 Kubernetes rolling restart；Pod 删除依赖
Deployment/ReplicaSet 自愈。请求必须携带服务端可验证的确认标记；前端二次确认不是唯一保护。
操作结果使用统一 API 响应，并写入 Runtime Operation Audit。

审计至少记录可信登录用户、Project、Application、Environment、Cluster、Namespace、资源 Kind/
Name、动作、原因、开始/结束时间、状态和脱敏错误。数据库模型通过 Alembic migration 创建。审计
不得保存 kubeconfig、Secret、终端输入输出或资源 YAML 内容。

## 交互式终端

普通 HTTP 接口创建短期、单用途 Exec Session。创建时校验登录会话、Project/Application/
Environment、Pod、Container 和操作原因，保存审计起始记录，并返回短期随机会话票据。票据仅能
使用一次，60 秒后过期，不能作为通用 API 凭据。

WebSocket 连接携带该票据，服务端重新校验目标上下文和 Pod/Container 后，通过 Kubernetes Exec
stream 转发 stdin/stdout/stderr 和终端 resize。浏览器不接触 kubeconfig。会话空闲 15 分钟关闭；
每个用户最多同时保持 2 个会话，同一个 Pod/Container 最多 1 个会话。断线、超时、目标消失或
权限失败都关闭 Kubernetes stream 并完成审计。
终端流量只在内存中转发，不写数据库和应用日志。

后端使用与 Flask 应用集成的 WebSocket 适配层承载连接，但票据签发、会话状态和 Kubernetes stream
转发保持在独立 Service 中，避免 WebSocket 传输逻辑进入 HTTP Route 或 `KubernetesService` 之外。

WebSocket 身份建立沿用现有 Session Cookie，并对创建票据的 HTTP 请求执行 CSRF 防护。握手校验
Origin，拒绝跨站连接。日志和异常信息只记录会话元数据，避免意外包含命令或输出。

## 错误处理与刷新

聚合接口为每个 Application Environment 返回成功数据或标准化错误码与脱敏消息。认证、Project
不存在等顶层错误仍使整个请求失败。前端保留最近一次成功内容并标记刷新失败，自动刷新默认采用
保守间隔且页面不可见时暂停；终端打开时不因列表刷新而断开。

删除 Pod 或重启 Deployment 成功后立即更新操作反馈并触发目标环境刷新。Kubernetes 只接受请求
不代表资源已经恢复，因此 UI 显示“操作已提交”，不虚报为“已健康”。

## 测试与验收

后端 Service 测试覆盖多环境聚合、局部失败、状态归一化和 Secret 脱敏；Route 测试覆盖统一响应、
Project 隔离、跨环境资源拒绝、确认参数和审计。Kubernetes Service 使用 mock 验证 restart、delete、
YAML 与 Exec stream 参数，不依赖在线集群。

终端测试覆盖票据单次使用、过期、Origin、用户/Pod 并发限制、上下文漂移、空闲超时、断线清理和
审计结束状态。前端检查覆盖聚合数据转换、筛选、局部错误、危险确认和终端状态管理。最后运行完整
`./scripts/verify.sh`、前端生产构建，并在浏览器人工验证桌面和窄屏布局、抽屉、刷新与错误状态。

## 备选方案

前端并发调用每个 Application Environment 的现有接口虽然改动较小，但请求数量随规模增长，难以
表达局部失败和一致刷新，因此不采用。直接按 Cluster/Namespace 浏览最接近 Kubernetes Dashboard，
但会展示 Project 外资源并弱化 Application 边界，也不采用。
