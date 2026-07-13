# 功能：Project Registry 配置与连通性测试

- 状态：已验收
- 负责人：Aegis Team
- 创建日期：2026-07-13

## 背景

Aegis 已经支持 Project 级 Container Registry 列表、新增、编辑、删除、默认项和
加密凭据，但当前无法证明 Registry 地址可达或用户名与 Token 有效。页面只能展示
“已配置凭据”，不能区分未测试、连接成功和连接失败，也没有保存前预检入口。

项目负责人和平台工程师需要在 Project 治理边界内配置 Registry，并通过 OCI
Distribution API 验证地址、TLS 和认证，避免无效配置直到构建或部署时才暴露。

## 当前行为

- `ContainerRegistry` 保存 Provider、Server、Namespace、用户名、加密密码、Pull
  Secret 名称、默认项和启用状态。
- `RegistryService` 负责配置校验、默认项维护和基于 `SECRET_KEY` 派生 Fernet 密钥的
  凭据加解密。
- API 不返回加密密码，仅返回 `has_credentials`。
- Project Registries 页面支持列表、新增、编辑、删除和设置默认 Registry。
- Registry 写操作仍使用 `/api/registries` 资源路由，读取可通过 `projectId` 过滤；没有
  连通性测试 API，也没有连接状态字段。
- 当前支持 ACR、Harbor、Docker Hub、ECR、GCR 和 Generic OCI Provider。

## 目标行为

用户可以在 Project Registries 页面配置需要用户名和 Token 的 OCI Registry。用户可以
在保存前使用当前表单内容测试连接，也可以对已保存 Registry 随时复测。测试访问
Registry 的 `/v2/` 端点，完成 Basic 或 Bearer Challenge 认证，并返回脱敏结果。

测试失败不阻止保存。已保存 Registry 记录最近一次测试状态、时间和脱敏消息。用户可以
显式跳过 TLS 证书校验以适配自签名 Harbor，但系统必须持续展示风险，且仍只允许 HTTPS。

## 范围

- 包含：ACR、Harbor、Docker Hub、ECR、GCR、Generic OCI 和 GHCR Provider。
- 包含：用户名和 Token 必填；不支持匿名 Registry。
- 包含：OCI `/v2/` Basic 与 Bearer Challenge 认证测试。
- 包含：新增/编辑表单的未保存配置预检。
- 包含：已保存配置复测和最近结果持久化。
- 包含：显式、默认关闭的 `跳过 TLS 证书校验` 配置。
- 包含：项目级 Registry 读取、写入和测试的作用域保护。
- 包含：模型、Alembic migration、后端服务与路由、前端 API/类型/页面和自动化测试。
- 包含：连接能力变化后更新 `docs/current-state.md`。

## 非目标

- 不执行镜像 Push、Pull、Manifest、Catalog 或仓库权限测试。
- 不创建或同步 Kubernetes ImagePullSecret。
- 不自动轮换、刷新或申请 ECR、GCR、ACR、GHCR 等云厂商 Token。
- 不支持匿名 Registry。
- 不支持 HTTP Registry。
- 不支持上传或托管自定义 CA 证书。
- 不引入后台定时健康检查、告警或 Registry 可用性历史。
- 不重构与 Registry 配置和测试无关的部署流程。

## 验收条件

- [x] 给定完整的新 Registry 表单，当用户点击“测试连接”时，后端使用尚未保存的
      Server、用户名、Token 和 TLS 设置执行测试，并且不创建或修改数据库记录。
- [x] 给定已保存 Registry，当用户在资源卡片点击“测试连接”时，后端使用解密后的
      Token 测试连接，并保存 `connected` 或 `failed`、最近测试时间和脱敏消息。
- [x] 给定编辑中的 Registry 且 Token 留空，当用户测试或保存时，后端沿用已保存 Token，
      API 不向前端回显 Token。
- [x] 给定 Registry 返回 Basic 认证挑战，当凭据有效时测试成功；凭据无效时返回
      `authentication_failed`。
- [x] 给定 Registry 返回 Bearer Challenge，当授权端点接受凭据并签发 Token 时，后端用
      Bearer Token 再次请求 `/v2/` 并确认成功。
- [x] 给定 ACR、Harbor、Docker Hub、ECR、GCR、Generic OCI 或 GHCR，当配置合法时
      Provider 校验接受该类型，并使用统一 OCI 流程测试。
- [x] 给定未填写用户名或 Token 的新配置，当测试或保存时，后端拒绝请求，不执行匿名测试。
- [x] 给定连接测试失败，当用户保存配置时，保存仍可完成，新配置状态为 `untested`，
      失败结果不会被客户端伪装成已持久化的成功状态。
- [x] 给定 Server、用户名、Token 或 TLS 设置发生变化，当保存后，历史连接状态、时间和
      消息被重置；只修改名称或 Namespace 不重置状态。
- [x] 给定有效证书，当正常测试成功时，结果包含 `tls_verified: true`。
- [x] 给定无效或自签名证书且未跳过校验，当测试时返回 `tls_failed`；开启跳过校验后允许
      继续认证，但结果包含 `tls_verified: false`，页面持续显示风险警告。
- [x] 给定 HTTP 地址、loopback、link-local、云元数据地址或其他明确危险目标，当测试时
      后端拒绝连接；企业私网 Registry 地址仍允许测试。
- [x] 给定跨 Project 的 Registry ID，当读取、修改、删除、设为默认或测试时，接口返回
      资源不存在，不泄露另一 Project 的 Registry 信息。
- [x] API、日志、异常、测试数据和响应中不出现明文 Token、Authorization Header、Bearer
      Token、加密凭据或未脱敏的远端响应正文。
- [x] 页面卡片展示未测试、已连接或连接失败、最近测试时间、脱敏消息以及 TLS 风险状态。
- [x] 所有新增接口保持 `success`、`message`、`data`、`timestamp`、`trace_id` 响应结构。
- [x] 后端相关自动化测试、前端类型检查和生产构建通过，`./scripts/verify.sh` 成功。
- [x] `docs/current-state.md` 只在实现和验证完成后记录 Registry 连通性能力。

## 设计说明

### 组件边界

新增独立的 `OCIRegistryClient` 外部系统适配器。它只负责构造 HTTPS 请求、执行 OCI
`/v2/` 探测、解析 Basic/Bearer Challenge、获取 Bearer Token、校验安全目标、处理超时
和归类错误。它不访问数据库，也不决定 Project 作用域或状态持久化。

`RegistryService` 继续负责 Registry 用例：校验配置、维护默认项、加解密凭据、调用
`OCIRegistryClient`、重置或持久化连接状态。HTTP 路由只负责请求解析、必填字段校验和
统一响应。

### 数据模型

`ContainerRegistry` 新增：

- `skip_tls_verify`：Boolean，非空，默认 `false`；
- `connection_status`：String，非空，默认 `untested`，只允许 `untested`、`connected`、
  `failed`；
- `last_checked_at`：可空带时区时间；
- `last_connection_message`：可空字符串，仅保存后端生成的脱敏消息。

模型变化必须通过新的 Alembic migration 完成，并验证既有 Registry 数据保留且默认值
正确。

### API 与数据流

Project Registry API 统一为项目子资源：

- `GET /api/projects/<project_id>/registries`：列出当前 Project 的 Registry；
- `POST /api/projects/<project_id>/registries`：在当前 Project 新增 Registry；
- `PATCH /api/projects/<project_id>/registries/<registry_id>`：更新当前 Project 的 Registry；
- `DELETE /api/projects/<project_id>/registries/<registry_id>`：删除当前 Project 的 Registry；
- `POST /api/projects/<project_id>/registries/<registry_id>/default`：设置当前 Project 的默认
  Registry；
- `POST /api/projects/<project_id>/registries/test-connection`：使用未保存表单内容测试，
  不落库；
- `POST /api/projects/<project_id>/registries/<registry_id>/test-connection`：默认使用已保存
  配置和解密 Token；编辑弹窗可传连接字段覆盖值，空 Token 沿用已保存 Token。只有不带
  覆盖值的已保存配置复测会持久化结果，避免把尚未保存的编辑内容写成 Registry 当前状态。

Project 页面和旧设置页都切换到项目子资源 API，所有 Registry CRUD、默认项和测试操作
都通过 Project + Registry ID 定位资源。现有 `/api/registries` 路由在前端迁移后删除，
不保留可绕过 Project 作用域的兼容写入口；本功能不扩大平台级无 Project Registry 能力。

连接成功响应至少包含 `connected`、`message`、`tls_verified` 和 `auth_method`。失败响应
至少包含 `connected: false`、`message`、`failure_reason` 和 `tls_verified`。
`failure_reason` 取值为 `authentication_failed`、`tls_failed`、`timeout`、`unreachable`
或 `protocol_error`。可预期的连接失败使用成功的 HTTP 调用响应包络表达；请求格式和配置
校验错误使用 4xx，未处理的服务端错误使用 5xx。

### OCI 认证流程

客户端仅使用 `https://<server>/v2/`：

1. 使用配置的 Basic 凭据请求 `/v2/`。
2. 2xx 表示 Registry 接受该请求，记录认证方式为 Basic。
3. 401 且为 Basic Challenge 时，凭据无效。
4. 401 且为 Bearer Challenge 时，解析并校验 HTTPS `realm`、`service` 和可选 `scope`，
   使用 Basic 凭据请求授权端点。
5. 从受限大小的 JSON 响应读取 `token` 或 `access_token`，不得记录该值。
6. 使用 Bearer Token 再次请求 `/v2/`；2xx 才算连接成功。
7. 其他状态、无效 Challenge、非 JSON Token 响应或缺失 Token 归为协议或认证失败。

请求设置有限的连接和读取超时，不无限重试，不跟随任意重定向。Registry 和授权端点在
连接前校验 scheme、主机和解析地址，拒绝 loopback、link-local、云元数据地址、multicast
和 unspecified 地址，同时允许企业 RFC1918 私网地址。Bearer `realm` 可以与 Registry
不同域，以兼容 Docker Hub 等标准授权服务，但必须经过相同安全校验。

`skip_tls_verify` 同时作用于 Registry 和其声明的 Bearer 授权端点；它只关闭证书验证，
不允许 HTTP。开启时前端展示持续风险提示，返回结果的 `tls_verified` 固定为 `false`。

### 页面交互

Project Registries 页面继续使用资源卡片。卡片展示 Provider、Server、Namespace、默认与
启用状态、凭据状态、连接状态、最近测试时间、脱敏消息和 TLS 风险，并提供测试、编辑、
设为默认和删除操作。

新增/编辑弹窗使用 Provider 下拉框并加入 GHCR。Server、用户名和 Token 是新配置必填项；
编辑时 Token 留空表示沿用。`跳过 TLS 证书校验` 默认关闭，开启时展示高风险说明。底部
提供独立的“测试连接”和“保存配置”按钮，测试结果显示在弹窗内，失败不关闭弹窗、不阻止
保存。预检结果不随保存请求由客户端写入数据库；新记录保存后为 `untested`，用户可从卡片
执行持久化复测。

### 测试策略

后端使用模拟 HTTP 传输覆盖 Basic、Bearer、GHCR、认证失败、TLS、跳过校验、超时、网络
不可达、危险目标、异常 Challenge 和敏感信息边界，不依赖在线 Registry。Service 测试覆盖
加密、Token 沿用、状态持久化、连接字段变化重置和默认项不变量。路由测试覆盖临时测试不
落库、已保存测试、Project 隔离、CSRF、校验错误和统一响应。

前端通过类型检查和生产构建验证 API 类型与页面模板。完整验收运行
`./scripts/verify.sh`；单元测试不得访问互联网或真实 Registry。

## 验证证据

- `cd backend && .venv/bin/python -m pytest tests/test_oci_registry_client.py
  tests/test_registry_service.py tests/test_deployment_plan_service.py tests/test_project_routes.py
  tests/test_validation_routes.py tests/test_registry_migration.py -q`：58 项通过。
- 独立代码复审确认 DNS 固定连接、hostname:port、流式响应上限、HTTP 拒绝、TLS 布尔校验
  和 Project Registry 选择问题已解决；复审聚焦验证 32 项通过，无剩余 Critical 或
  Important 问题。
- `./scripts/verify.sh`：2026-07-13 运行成功；后端 127 项测试通过，前端 TypeScript 检查和
  Vite 生产构建通过，Registry migration 升级/降级与既有数据保留测试通过。
- `rg -n "registryApi|['\"]/registries" frontend/src/api frontend/src/views` 无匹配，证明
  前端不再使用无 Project 作用域的 Registry API。
- 未连接真实在线 Registry，所有协议与失败场景使用本地模拟传输验证；未在测试中使用生产
  凭据，也未执行镜像 Push 或 Pull。

## 完成

验收日期：2026-07-13。全部验收条件已有自动化或构建证据，本规格移至
`specs/completed/`。
