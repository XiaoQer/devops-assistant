# Project Runtime Deployment–Pod 层级修正设计

## 背景

Runtime V2 将 Deployment 和 Pod 设计成平级 Tab。这不符合当前产品围绕 Application
工作负载排障的心智模型，也丢失了 Kubernetes 中 Deployment 管理 Pod 的父子关系。
主页面需要以 Deployment 为工作负载入口，Pod 作为展开后的实例集合出现，再下钻到独立详情。

## 信息架构

页面保持单 Environment 上下文和顶部运行指标。主内容区域只包含一个可分页的 Deployment
列表，不再显示 Pods Tab。每一行包含展开控制、Application/Deployment、健康状态、Ready/Desired
副本、Pod 数、累计重启、镜像、YAML 和重启操作。

用户展开一行后，页面懒加载该 Deployment 所属 Pod，并在该行下方展示紧凑子表。子表包含 Pod
名称、状态、Ready、Container 数、重启数、Node 和创建时间。Pod 名称链接到现有独立详情路由：

`/devcenter/projects/:projectId/runtime/environments/:environment/applications/:applicationId/pods/:podName`

Deployment 整行都是展开/收起触发区，鼠标悬停时显示浅色反馈和手型光标；左侧箭头保留为层级
提示，但不是唯一入口。YAML、重启以及 Pod 名称等交互控件阻止行点击冒泡，避免误切换展开状态。

Pod 展开区不嵌套第二张完整表格，也不重复深色表头。它使用浅灰背景、左侧层级线和紧凑网格行，
通过对齐的轻量字段标签展示 Pod 信息。多个 Pod 纵向排列；窄屏下字段允许换行，不产生页面级
横向溢出。

Runtime 主表同样不使用黑色表头。表头采用浅灰蓝背景、深灰文字和细分隔线；Deployment 行保持
白色，悬停时使用浅蓝灰反馈。展开区使用更弱的浅灰蓝底色，Pod 行为白色卡片式条目。绿色只用于
健康状态，蓝色用于链接和层级提示，橙色只用于风险操作，避免大面积高对比色压过资源内容。

## 数据与接口

Deployment 主列表继续使用单环境、服务端搜索与 20/50/100 条分页接口。请求不再接受前端的
`resource=pods` 工作流，响应中的每个 Deployment 只携带汇总信息，不以内嵌方式返回 Pod 列表。

新增 Deployment Pods 查询接口：

`GET /api/projects/:projectId/applications/:applicationId/environments/:environment/runtime/deployments/:deploymentName/pods`

后端通过 Delivery Context 解析目标集群和 Namespace，并在 KubernetesService 中同时验证
Deployment 名称与 Application 归属。返回标准化 Pod 摘要，不包含环境变量、Secret 或其他敏感值。

前端仅在首次展开时请求。成功结果缓存在当前页面生命周期内；再次展开不重复请求。环境、搜索、
状态、页码、页容量变化或手动刷新主列表时清空缓存，避免显示过期或跨上下文 Pod。

## 状态与错误

展开区域拥有独立的 loading、empty 和 error 状态。某个 Deployment 的 Pod 请求失败时，只在该行
展示错误及“重试”操作，不替换主页面数据，也不阻止其他 Deployment 展开。Deployment 本身无法
读取时仍沿用主列表的 Unknown 状态与局部错误呈现。

## 运维与安全

Deployment YAML 和滚动重启仍在父行操作区。Pod 日志、YAML、终端和删除操作继续位于 Pod 详情页。
现有显式确认、生产环境强化文案、终端原因、短时单次票据、Origin 校验、超时、并发限制和审计
约束保持不变。

## 测试

- Service 测试验证 Deployment Pod 查询使用目标集群、Namespace 和 Application 归属。
- 路由测试验证统一响应及 Project/Application/Environment 上下文。
- 前端测试验证主页面没有 Pods Tab，首次展开触发请求、重复展开使用缓存、刷新清空缓存。
- 组件测试验证整行展开、操作控件不冒泡、轻量 Pod 列表、空状态、局部错误、重试及详情路由参数。
- 完成后运行 `./scripts/verify.sh`，并在已登录浏览器中检查桌面与窄屏布局。
