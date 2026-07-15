# Project Runtime V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the all-environment accordion Runtime page with a single-environment, server-paginated Deployment/Pod inventory and a dedicated Pod detail page.

**Architecture:** `ProjectRuntimeService` accepts one validated environment plus resource, filter, and pagination inputs, returning only the current page. `ApplicationRuntimeService` adds a Project-scoped Pod detail use case backed by standardized Kubernetes data; Vue keeps environment and resource state in the URL and routes Pod names to a dedicated detail workspace.

**Tech Stack:** Flask 3.1, Flask-SQLAlchemy, Kubernetes Python client, Vue 3, TypeScript, Element Plus, xterm.js, Vitest.

## Global Constraints

- Exactly one Environment is active on the Runtime page.
- Default page size is 20; allowed page sizes are 20, 50, and 100; the server rejects larger values.
- Project → Application → Environment remains the authorization and Kubernetes context boundary.
- HTTP requests remain in `frontend/src/api`; Kubernetes access remains in `KubernetesService`.
- No CPU/Memory usage is displayed without a Metrics API source.
- Existing confirmation, audit, ticket, Origin, timeout, concurrency, and Secret-redaction protections remain unchanged.
- Unit tests do not require an online Kubernetes cluster.

---

### Task 1: Single-environment paginated Runtime API

**Files:**
- Modify: `backend/app/services/project_runtime_service.py`
- Modify: `backend/app/routes/runtime.py`
- Modify: `backend/tests/test_project_runtime_service.py`
- Modify: `backend/tests/test_runtime_routes.py`

**Interfaces:**
- Produces `ProjectRuntimeService.environments(project) -> list[dict]`.
- Produces `ProjectRuntimeService.inventory(project, environment, resource, page, page_size, query=None, status=None) -> dict`.
- Produces `GET /api/projects/<project_id>/runtime/environments`.
- Changes `GET /api/projects/<project_id>/runtime` to require `environment`, with `resource=deployments|pods`, `page`, `page_size`, `query`, and `status`.

- [ ] Write failing Service tests proving only the requested environment is queried, same-name environment targets cannot mix clusters, filters apply before pagination, page metadata is correct, and page size above 100 is rejected.
- [ ] Run `cd backend && ./.venv/bin/python -m pytest tests/test_project_runtime_service.py -q`; expect failures against the all-environment `overview()` API.
- [ ] Implement environment discovery, context-consistency validation, normalized Deployment/Pod rows, summary calculation, filtering, and slicing.
- [ ] Write failing route tests for required environment, resource validation, page bounds, unified response, and environment directory.
- [ ] Implement query validation in the Route and delegate to the Service.
- [ ] Run `cd backend && ./.venv/bin/python -m pytest tests/test_project_runtime_service.py tests/test_runtime_routes.py -q`; expect all tests to pass.
- [ ] Commit with `git commit -m "refactor: scope runtime inventory to one environment"`.

### Task 2: URL-driven Runtime resource tables

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api/runtime.ts`
- Modify: `frontend/src/api/runtime.test.ts`
- Replace: `frontend/src/composables/useProjectRuntime.ts`
- Modify: `frontend/src/composables/useProjectRuntime.test.ts`
- Create: `frontend/src/components/runtime/RuntimeResourceTable.vue`
- Modify: `frontend/src/views/ProjectRuntime.vue`
- Delete: `frontend/src/components/runtime/RuntimeEnvironmentGroup.vue`

**Interfaces:**
- Produces `RuntimeInventory` with `environment`, `summary`, `items`, and `pagination`.
- Produces `runtimeApi.environments(projectId)` and `runtimeApi.inventory(projectId, params)`.
- `useProjectRuntime(projectId, route, router)` owns environment/resource/filter/page URL synchronization and 30-second refresh.

- [ ] Rewrite failing API/composable tests for exact query parameters, valid environment restoration, Tab/page URL state, filter page reset, current-page-only items, refresh preservation, and hidden-page pause.
- [ ] Run the two focused Vitest files and confirm failures against the old overview shape.
- [ ] Implement new types, API functions, and URL-driven composable.
- [ ] Build `RuntimeResourceTable.vue`: Deployment and Pod columns, current-page rows only, row actions emitted to the parent, Pod name navigation event.
- [ ] Replace environment cards/accordion in `ProjectRuntime.vue` with environment selector, four current-environment metrics, Deployments/Pods tabs, filters, table, and server pagination.
- [ ] Delete `RuntimeEnvironmentGroup.vue` and remove all references.
- [ ] Run `cd frontend && npm test && npm run build`; expect all tests, type check, and build to pass.
- [ ] Commit with `git commit -m "refactor: build paginated runtime inventory"`.

### Task 3: Standardized Pod detail API

**Files:**
- Modify: `backend/app/services/kubernetes_service.py`
- Modify: `backend/app/services/application_runtime_service.py`
- Modify: `backend/app/routes/runtime.py`
- Modify: `backend/tests/test_application_runtime_service.py`
- Modify: `backend/tests/test_runtime_routes.py`

**Interfaces:**
- Produces `KubernetesService.get_application_pod_detail(pod_name, namespace, app_name) -> dict`.
- Produces `ApplicationRuntimeService.pod_detail(context, pod_name) -> dict`.
- Produces `GET /api/projects/<project_id>/applications/<app_id>/environments/<environment>/runtime/pods/<pod_name>`.

- [ ] Write a failing Kubernetes normalization test using a fake Pod/Event object and asserting identity, phase, ready, QoS, Pod IP, node, timestamps, conditions, containers, waiting/terminated reasons, and sorted events.
- [ ] Write failing Service/Route tests proving Delivery Context and label ownership are enforced and the response uses the unified envelope.
- [ ] Implement Pod detail serialization without managed fields, Secret data, environment variables, or raw exception bodies.
- [ ] Run focused backend tests plus `test_project_application_routes.py`; expect all to pass.
- [ ] Commit with `git commit -m "feat: add project-scoped pod details"`.

### Task 4: Dedicated Pod detail page

**Files:**
- Create: `frontend/src/views/PodDetail.vue`
- Create: `frontend/src/components/runtime/PodOverview.vue`
- Create: `frontend/src/components/runtime/pod-detail-view-model.ts`
- Create: `frontend/src/components/runtime/pod-detail-view-model.test.ts`
- Modify: `frontend/src/api/runtime.ts`
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/views/ProjectRuntime.vue`
- Reuse: `frontend/src/components/runtime/RuntimeTerminalDrawer.vue`

**Interfaces:**
- Produces route `/devcenter/projects/:projectId/runtime/environments/:environment/applications/:applicationId/pods/:podName`.
- Produces Pod detail tabs `overview`, `containers`, `events`, `logs`, `yaml`, and `terminal`.

- [ ] Write failing view-model tests for status/condition mapping, container state labels, event ordering, log tail options, and route construction back to the current environment Pods list.
- [ ] Implement Pod detail types/API/view model and make Pod table names navigate to the dedicated route.
- [ ] Build `PodOverview.vue` for identity, Conditions, Containers, and Events without invented metrics.
- [ ] Build `PodDetail.vue` with breadcrumb, refresh, stable URL, overview/containers/events/logs/YAML/terminal tabs, Container and tail selection, copy, existing exec session flow, and production-aware delete confirmation.
- [ ] Run `cd frontend && npm test && npm run build`; expect all tests and build to pass.
- [ ] Commit with `git commit -m "feat: add dedicated pod runtime details"`.

### Task 5: Acceptance and documentation

**Files:**
- Modify only the Runtime section of `docs/current-state.md`
- Move: `specs/active/project-runtime-workspace-v2.md` → `specs/completed/project-runtime-workspace-v2.md`

- [ ] Run `./scripts/verify.sh`; expect complete backend/frontend verification to pass.
- [ ] Browser-test one selected environment, Deployment/Pod tabs, search, pagination with more than 20 mock rows, Pod detail direct refresh, all detail tabs, terminal confirmation, and 390px layout.
- [ ] Confirm the old environment cards and `.el-collapse` Runtime interaction are absent and current-page DOM rows do not exceed page size.
- [ ] Record evidence, update only the Runtime capability paragraph while preserving unrelated dirty changes, archive the accepted spec, and run `git diff --check` plus `./scripts/verify.sh` again.
- [ ] Commit with `git commit -m "docs: accept project runtime v2"`.
