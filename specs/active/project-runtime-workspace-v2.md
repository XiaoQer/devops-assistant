# 功能：Project Runtime 单环境资源工作台与 Pod 详情

- 状态：已确认
- 负责人：Codex
- 创建日期：2026-07-15

## 背景

首版 Project Runtime 同时纵向展示所有 Environment，并把 Pod 放在 Deployment 折叠行内。
这种信息架构无法形成明确的当前运行上下文；Application 数量增加后页面无限增长，也没有提供用户
要求的独立 Pod 详情页面。

## 当前行为

- Runtime 一次查询并显示当前 Project 的全部 Application Environment。
- 每个环境都是一个卡片，Application Deployment 使用折叠行展示 Pod。
- Pod 日志、YAML、删除和终端从折叠行触发，没有独立详情路由。
- 搜索和状态筛选在前端对一次性返回的全部聚合数据执行，不适合大量服务。

## 目标行为

Runtime 每次只展示一个显式选择的 Environment，并通过服务端分页呈现当前环境的 Deployment
资源表。Deployment 是主列表层级；用户展开某个 Deployment 后按需加载其 Pod，点击 Pod 名称
进入独立详情页面，在同一上下文查看基础状态、Conditions、
Containers、Events、Logs、YAML，并执行受治理的终端和删除操作。

## 范围

- 包含：URL 查询参数保存当前环境，页面始终只统计和显示一个环境。
- 包含：Deployment 服务端分页、关键词搜索和状态筛选。
- 包含：Deployment 行展开后懒加载归属 Pod，收起时保留当前页面内的加载缓存。
- 包含：独立 Pod 详情路由和 Overview、Containers、Events、Logs、YAML、Terminal 能力。
- 包含：Pod 详情所需的 Kubernetes 基础信息、Container 状态、Conditions 和 Events 标准化接口。
- 包含：沿用 Project/Application/Environment 归属校验、生产风险确认、审计和 Exec 安全约束。
- 包含：删除首版 Runtime 的环境纵向分组；保留 Deployment 到 Pod 的正确父子层级。

## 非目标

- 不浏览非 Aegis Application 管理的 Kubernetes 资源。
- 不新增在线监控指标、节点管理、文件传输、端口转发或终端内容回放。
- 不伪造 CPU/Memory 指标；没有 Metrics API 数据时不展示资源使用率。
- 不在本次返工中新增 Deployment 独立详情页。

## 验收条件

- [x] Runtime 首次进入选择一个有效环境，切换环境时 URL、指标和资源表同步更新，页面不同时铺开多个环境。
- [x] Runtime 主页面只存在 Deployment 列表，不把 Deployment 与 Pod 作为平级 Tab。
- [x] Deployment 搜索、状态筛选和分页由服务端执行，每页默认 20 条、最多 100 条。
- [x] 给定大量 Application，页面 DOM 只渲染当前页资源，不随 Project 全量服务数无限增长。
- [x] Deployment 表显示 Application、状态、副本、Pod 数、重启数、镜像和操作。
- [x] 展开 Deployment 后懒加载其 Pod，并显示 Pod、状态、Ready、Container 数、重启数、Node
      和创建时间；Pod 不在主列表独立分页。
- [x] 点击 Deployment 行任意非操作区域均可展开或收起；箭头不是唯一入口，YAML、重启和 Pod
      详情点击不会误触发展开状态。
- [x] Pod 展开区使用浅色紧凑子列表，不重复主表深色表头，并通过缩进或层级线表达父子关系。
- [x] Deployment 主表使用浅灰蓝表头和白色资源行，不出现大面积黑色背景；颜色强调仅用于状态、
      链接和风险操作。
- [x] Deployment 操作收纳在单一更多菜单中；查看 YAML 与警示色重启操作分组展示，不在资源行
      末尾平铺多个按钮。
- [x] 单个 Deployment 的 Pod 加载失败只显示在该展开区域，不阻断其他 Deployment。
- [x] 点击 Pod 名称进入独立详情路由，刷新后仍能从 URL 恢复 Project、Environment、Application 和 Pod。
- [x] Pod 详情展示基础信息、Conditions、Containers 和 Events，错误与空状态可区分。
- [x] Pod 详情采用 Container-first 工作区：紧凑资源头、Container 快捷日志/终端、右侧 Pod 信息栏，
      Conditions 与 Events 使用浅色紧凑表格；删除 Pod 收进更多操作菜单。
- [x] Logs 支持 Container 和 Tail 行数选择、刷新与复制；YAML 为只读完整资源内容。
- [x] Terminal 要求 Container 和二次确认；需审批环境要求具备 owner/admin 终端权限并填写原因，免审批环境无需填写原因；继续满足单次票据、Origin、超时、并发和元数据审计约束。
- [x] 删除 Pod 必须二次确认；生产环境使用强化风险文案；成功只显示“操作已提交”。
- [x] 旧的多环境卡片和 Pods 平级 Tab 不再出现在 Runtime 主页面。
- [x] 后端自动化测试、前端测试、类型检查、生产构建和 `./scripts/verify.sh` 通过。
- [ ] 浏览器验收覆盖桌面、窄屏、环境切换、Deployment 分页与展开，以及 Pod 详情主要 Tab；当前浏览器会话无开发环境登录状态，保留人工验收。

## 设计说明

详细设计见 `docs/superpowers/specs/2026-07-15-project-runtime-deployment-hierarchy-design.md`。

Pod 详情视觉返工见 `docs/superpowers/specs/2026-07-15-pod-detail-container-first-design.md`。

## 验证证据

- `./scripts/verify.sh`：后端 242 项、前端 37 项通过，前端类型检查与生产构建成功。
- Runtime API/Composable/View Model 自动化检查覆盖单环境、URL 状态、服务端分页、Pod 详情标准化、
  Deployment Pod 归属、懒加载缓存、局部错误重试、Container/Tail 日志参数以及 30 秒刷新行为。
- Runtime 相关 17 项前端测试通过，生产构建成功；全量前端测试当前被用户未提交的 Portal 布局
  契约变更阻断（`PortalHome.layout.test.ts` 禁止当前 `PortalHome.vue` 中的高度媒体查询）。
- 浏览器已能打开本地构建，但当前浏览器没有开发环境登录会话，桌面与窄屏交互验收保留为待人工项。

## 完成

验收后记录日期并移至 `specs/completed/`。
