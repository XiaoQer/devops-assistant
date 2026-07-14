# Build Once, Promote Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Application 发布流程拆分为一次构建、多环境复用同一构建版本的 Build → Promote 模式。

**Architecture:** 新增 ApplicationBuildVersion 作为不可变构建产物记录，Build Pipeline 只负责源码构建和镜像推送；Release/Deploy Pipeline 只接收构建版本与目标环境参数并部署。ReleaseRecord 和 ApprovalRecord 通过 build_version_id 关联构建产物，生产审批针对具体构建版本和目标环境。

**Tech Stack:** Flask、SQLAlchemy、Alembic、Vue 3、TypeScript、Element Plus、Tekton Pipeline、Kaniko。

## Global Constraints

- 构建版本必须绑定 Application、源码分支、提交（若可得）、镜像名称和不可变镜像 Tag。
- Deploy-only Pipeline 不得包含 Git clone、项目编译或 Kaniko build 步骤。
- 同一构建版本允许部署到多个 Application Environment。
- 生产环境仍必须通过现有审批流程，审批单必须展示构建版本和镜像信息。
- 不在 API、日志或测试输出中暴露 Registry 凭据、kubeconfig 或 Application Secret。
- 每次数据库模型变更必须包含 Alembic migration。

## 文件边界

- `backend/app/models/build_version.py`：构建版本持久化和序列化。
- `backend/app/models/release_record.py`、`pipeline_execution.py`、`approval_record.py`：增加构建版本关联。
- `backend/migrations/versions/`：新增构建版本及关联字段迁移。
- `backend/app/services/build_version_service.py`：构建版本创建、列表和可发布校验。
- `backend/app/services/application_service.py`：拆出 build 和 deploy-only 两类执行。
- `backend/app/services/approval_service.py`：审批具体构建版本。
- `backend/app/routes/applications.py`、`approvals.py`：新增构建版本与发布接口。
- `backend/app/services/tekton_service.py`：新增 build/deploy-only PipelineRun 参数构造。
- `deploy/tekton/pipelines/*-kaniko-build.yaml`：只构建推送镜像。
- `deploy/tekton/pipelines/*-deploy-only.yaml`：只执行 Kubernetes 部署。
- `frontend/src/api/application.ts`、`types.ts`：构建版本和发布请求类型。
- `frontend/src/views/ApplicationDetail.vue`：构建版本列表、构建操作和版本发布弹窗。
- `frontend/src/components/application/BuildVersionList.vue`：构建版本列表和发布入口。

### Task 1: 建立构建版本数据模型

**Files:**
- Create: `backend/app/models/build_version.py`
- Modify: `backend/app/models/__init__.py`, `backend/app/models/application.py`, `backend/app/models/pipeline_execution.py`, `backend/app/models/release_record.py`, `backend/app/models/approval_record.py`
- Create: `backend/migrations/versions/<revision>_add_application_build_versions.py`
- Test: `backend/tests/test_build_version_model.py`

- [ ] 创建 `ApplicationBuildVersion` 字段：`id`、`application_id`、`project_id`、`version`、`git_repo`、`git_branch`、`git_commit`、`image_name`、`image_tag`、`image_digest`、`pipeline_run_name`、`status`、`created_by`、`created_at`、`finished_at`、`error_message`。
- [ ] 为 `PipelineExecution`、`ReleaseRecord`、`ApprovalRecord` 增加 nullable `build_version_id` 外键和序列化字段；保留旧字段以兼容历史数据。
- [ ] 添加 migration，包含索引 `(application_id, created_at)`、`(project_id, status)` 和外键。
- [ ] 添加模型和迁移测试，验证构建版本可创建、序列化、删除 Application 时级联删除，历史执行记录允许为空。

### Task 2: 拆分 Tekton Pipeline 模板

**Files:**
- Modify: `backend/app/services/tekton_service.py`
- Create: `deploy/tekton/pipelines/java-maven-kaniko-build.yaml`, `node-npm-kaniko-build.yaml`, `dockerfile-kaniko-build.yaml`
- Create: `deploy/tekton/pipelines/java-maven-deploy-only.yaml`, `node-npm-deploy-only.yaml`, `dockerfile-deploy-only.yaml`
- Test: `backend/tests/test_tekton_service.py`

- [ ] 保留现有 Pipeline 名称用于历史执行，新增 `create_build_pipeline_run(...)`，参数只包含 repo、branch、image 和 Registry Secret。
- [ ] 新增 `create_deploy_pipeline_run(...)`，参数包含 `image`、环境部署参数、kubeconfig Secret 和 context，不包含 repo、branch、Kaniko 或 workspace clone。
- [ ] build 模板只执行源码准备和 Kaniko 推送，并将 image tag 作为输出记录输入；deploy-only 模板直接用 `kubectl` 更新 Deployment、Service、ConfigMap/Secret 和副本资源。
- [ ] 为两类 PipelineRun 增加明确 labels：`aegis.dev/pipeline-type=build|deploy`、`aegis.dev/build-version-id`。
- [ ] 用模拟 Kubernetes Custom API 测试两类 PipelineRun 的 params 和 PipelineRef，断言 deploy-only 不含 build 参数。

### Task 3: 构建版本 Service 与 API

**Files:**
- Create: `backend/app/services/build_version_service.py`
- Modify: `backend/app/routes/applications.py`, `backend/app/services/application_service.py`
- Modify: `backend/app/routes/pipelines.py`
- Test: `backend/tests/test_build_version_routes.py`

- [ ] 新增 `GET /api/projects/<project_id>/applications/<app_id>/build-versions`，按创建时间倒序返回构建版本。
- [ ] 新增 `POST /api/projects/<project_id>/applications/<app_id>/build-versions`，校验 Application 和 Project 归属，创建 Build PipelineRun 并保存 Pending 构建版本。
- [ ] 构建请求默认使用 Application 当前 branch/image_tag 规则；同一提交已有成功版本时允许复用，不自动重复创建。
- [ ] Pipeline 状态同步或查询时将构建 PipelineRun 状态更新到构建版本，成功时保存 image digest（若 Tekton/Kaniko 可提供），失败时保存脱敏错误。
- [ ] 新增 `build_version_service.require_publishable(id)`，只允许 `Succeeded` 且有镜像地址的构建版本发布。

### Task 4: 发布与审批改为引用构建版本

**Files:**
- Modify: `backend/app/services/application_service.py`, `backend/app/services/approval_service.py`, `backend/app/routes/applications.py`, `backend/app/routes/approvals.py`
- Modify: `backend/app/models/release_record.py`, `backend/app/models/pipeline_execution.py`
- Test: `backend/tests/test_build_promote_routes.py`, `backend/tests/test_approval_routes.py`

- [ ] 将 `POST /deploy/plan` 请求改为接收 `build_version_id` 和 `environment`，计划返回构建版本、镜像、目标环境和风险检查。
- [ ] 将 `POST /deploy` 改为创建 Deploy-only PipelineRun，写入 `PipelineExecution.build_version_id` 和 `ReleaseRecord.build_version_id`，不触发构建。
- [ ] 允许同一个 `build_version_id` 创建多个不同环境的部署执行；同一环境存在 Running/Pending 发布时返回冲突。
- [ ] 审批提交保存 `build_version_id`、镜像和目标环境；批准时调用 Deploy-only 流程，不重新构建。
- [ ] 保持旧历史 Release/Execution/Approval 可读取；缺少 `build_version_id` 时显示 Legacy Build。

### Task 5: 改造 Application 发布体验

**Files:**
- Create: `frontend/src/components/application/BuildVersionList.vue`
- Modify: `frontend/src/api/application.ts`, `frontend/src/types.ts`, `frontend/src/views/ApplicationDetail.vue`
- Test: `frontend/src/components/application/BuildVersionList.spec.ts`（若当前测试基础设施可用）

- [ ] 在 Application Pipeline/构建区域增加“构建新版本”操作和构建版本列表，展示版本、提交、镜像、状态、创建时间。
- [ ] 发布弹窗先选择成功构建版本，再选择一个目标环境；移除“选择环境后自动生成构建计划”的文案。
- [ ] 发布计划明确显示“本次只部署，不重新构建”，并展示镜像 Tag/Digest、目标 Namespace、Cluster 和审批提示。
- [ ] 成功构建版本可连续发布到多个环境；已发布环境显示最近部署状态和入口。
- [ ] 生产环境按钮继续显示“提交审批”，审批详情展示构建版本和镜像信息。

### Task 6: 验证、文档与兼容性

**Files:**
- Modify: `docs/current-state.md`, `specs/active/project-scoped-application-delivery.md`
- Test: existing backend/frontend verification suite

- [ ] 补充 API、迁移、Tekton 参数和前端类型测试。
- [ ] 运行 `./scripts/verify.sh`，确认后端测试、前端类型检查和生产构建通过。
- [ ] 更新 current-state，记录 Build once/Promote 能力和 Legacy 执行兼容边界。
- [ ] 将规格中的验收条件更新为构建与部署分离，并在所有条件有证据后迁移到 `specs/completed/`。
