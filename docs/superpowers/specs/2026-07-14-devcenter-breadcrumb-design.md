# DevCenter 详情页 Breadcrumb 设计

## 背景

DevCenter 的 Project、Application 和 Pipeline 详情页存在多层进入路径。用户进入详情后，当前页面缺少明确的层级上下文和返回入口，尤其从项目概览或执行列表进入 Pipeline 详情时，需要依赖浏览器返回。

## 目标

- 为 DevCenter 下的详情页提供统一的层级导航。
- 让上级 Project、Application、Pipeline 列表可直接点击返回。
- 保持当前浅色后台视觉风格，不增加页面头部高度。
- 在窄屏下保持可读，并支持层级过长时截断当前项。

## 范围

### 包含

- Project 详情页：`/devcenter/projects/:id`
- Application 详情页：`/devcenter/projects/:projectId/applications/:id`
- PipelineRun 详情页：`/devcenter/projects/:projectId/pipelines/:name`
- 新增可复用的 `DetailBreadcrumb` 组件。

### 不包含

- 列表页、创建页和配置页的全量导航改造。
- 后端 API 变更。
- 自动根据路由名称推导业务名称；详情页提供已加载的业务名称。

## 交互设计

- 固定层级从 `DevCenter` 开始，后续显示 Project、Application、Pipeline 等业务上下文。
- 非当前层级使用链接，点击后跳转到对应列表或详情页。
- 当前层级使用强调色文本，不可点击。
- 分隔符使用轻量箭头，整体放在页面标题上方，字号 12–13px。
- 对缺少业务名称的情况使用 `Project {id}`、`Application {id}` 或路由参数作为兜底。

## 实现设计

- `DetailBreadcrumb.vue` 接收 `items` 数组，每项包含 `label`、可选 `to` 和 `current`。
- 各详情页在已有数据加载后构造 Breadcrumb；数据尚未加载时显示稳定的参数兜底名称。
- 组件只负责展示和路由跳转，业务数据仍由各页面现有 API 负责。
- 使用 scoped 样式和 CSS 变量，兼容当前主题与响应式布局。

## 验收条件

- 三类详情页均显示 Breadcrumb。
- 点击 Project、Application、Pipeline 列表层级可正确返回。
- 当前页面层级高亮且不可点击。
- 面包屑不造成标题区域明显膨胀，窄屏不出现横向溢出。
- 前端类型检查和生产构建通过。
