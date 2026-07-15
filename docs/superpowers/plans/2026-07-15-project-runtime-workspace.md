# Project Runtime Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Project-scoped Runtime workspace that aggregates Deployment and Pod health by environment and provides audited restart, Pod deletion, YAML/log viewing, and browser-based Pod exec.

**Architecture:** A new `ProjectRuntimeService` resolves every Application Environment through the existing delivery context and returns partial-success summaries. Mutating operations and exec sessions use the same context boundary, persist metadata-only audits, and keep Kubernetes access in `KubernetesService`; the Vue page consumes only APIs in `frontend/src/api` and uses focused components for inventory, resource detail, and terminal transport.

**Tech Stack:** Flask 3.1, Flask-SQLAlchemy, Alembic, Kubernetes Python client, Flask-Sock/simple-websocket, pytest/unittest, Vue 3, TypeScript, Element Plus, xterm.js, Vitest, Vite.

## Global Constraints

- `Project` remains the governance and workspace boundary; `Application` remains the delivery aggregate.
- Runtime resources must be resolved through Project → Application → Environment; clients cannot select arbitrary clusters or namespaces.
- All Kubernetes connections and resource operations remain in `KubernetesService`.
- HTTP handlers perform transport validation and delegate business behavior to Services.
- HTTP responses retain `success`, `message`, `data`, `timestamp`, and `trace_id`.
- Restart, Pod deletion, and terminal creation require explicit confirmation; terminal creation also requires a non-empty reason.
- Exec tickets are single-use and expire after 60 seconds; sessions idle for 15 minutes close automatically.
- A user may hold at most two exec sessions; a Pod/container may hold at most one.
- Audit records never contain kubeconfig, Secret values, resource YAML, terminal input, or terminal output.
- Unit tests must not depend on an online Kubernetes cluster.

---

### Task 1: Runtime audit persistence

**Files:**
- Create: `backend/app/models/runtime_operation_audit.py`
- Create: `backend/migrations/versions/i9d0e1f2a3b4_add_runtime_operation_audits.py`
- Create: `backend/tests/test_runtime_operation_audit_migration.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/__init__.py`

**Interfaces:**
- Produces: `RuntimeOperationAudit.start(...) -> RuntimeOperationAudit`, `audit.finish(status, error_message=None)`, and `audit.to_dict()`.
- Schema fields: `id`, `user_id`, `project_id`, `application_id`, `environment`, `cluster_id`, `namespace`, `resource_kind`, `resource_name`, `container`, `action`, `reason`, `status`, `error_message`, `started_at`, `finished_at`.

- [ ] **Step 1: Write the failing model and migration tests**

Create tests that stamp migration `h8c9d0e1f2a3`, upgrade to `i9d0e1f2a3b4`, assert the table and indexes exist, downgrade, and assert it is removed. Add a model test that calls:

```python
audit = RuntimeOperationAudit.start(
    user_id=user.id, project_id=project.id, application_id=app.id,
    environment="prod", cluster_id=cluster.id, namespace="payments",
    resource_kind="Pod", resource_name="payments-abc", container="api",
    action="exec", reason="investigate incident",
)
audit.finish("Succeeded")
assert audit.to_dict()["reason"] == "investigate incident"
assert "terminal_output" not in audit.to_dict()
```

- [ ] **Step 2: Run tests and verify RED**

Run: `cd backend && python -m pytest tests/test_runtime_operation_audit_migration.py -q`

Expected: collection fails because the migration/model does not exist.

- [ ] **Step 3: Add the model, migration, export, and local schema registration**

Implement the exact fields above with foreign keys to users/projects/applications/clusters, UTC timestamps, bounded strings, and a nullable sanitized error. `finish()` sets status, error, and `finished_at`; `to_dict()` returns metadata only.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `cd backend && python -m pytest tests/test_runtime_operation_audit_migration.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models backend/app/__init__.py backend/migrations/versions/i9d0e1f2a3b4_add_runtime_operation_audits.py backend/tests/test_runtime_operation_audit_migration.py
git commit -m "feat: add runtime operation audit model"
```

### Task 2: Project Runtime aggregation

**Files:**
- Create: `backend/app/services/project_runtime_service.py`
- Create: `backend/app/routes/runtime.py`
- Create: `backend/tests/test_project_runtime_service.py`
- Create: `backend/tests/test_runtime_routes.py`
- Modify: `backend/app/routes/__init__.py`
- Modify: `backend/app/__init__.py`
- Modify: `backend/app/services/kubernetes_service.py`

**Interfaces:**
- Produces: `ProjectRuntimeService.overview(project) -> {environments, summary, refreshed_at}`.
- Produces: `GET /api/projects/<project_id>/runtime` with partial-success environment/application items.
- Adds `KubernetesService.get_application_runtime_summary(app_name, namespace)` returning Deployment and Pod data including containers.

- [ ] **Step 1: Write failing aggregation Service tests**

Cover two applications in two environments, deterministic environment/application ordering, counts for deployments/healthy pods/unhealthy pods/restarts, and one Kubernetes client raising an exception while the other result remains present. Assert the error item contains a stable code and sanitized message, not exception body or credentials.

- [ ] **Step 2: Verify Service tests fail for the missing Service**

Run: `cd backend && python -m pytest tests/test_project_runtime_service.py -q`

Expected: import fails for `ProjectRuntimeService`.

- [ ] **Step 3: Implement minimal aggregation**

List Project applications and their explicit environments, resolve each via `DeliveryContextService.resolve`, query through `ApplicationRuntimeService.status`, normalize the response to:

```python
{
  "summary": {"environments": 2, "deployments": 2, "healthy_pods": 3,
              "unhealthy_pods": 1, "restart_count": 4},
  "environments": [{
    "name": "prod", "display_name": "Production", "cluster_name": "ack-prod",
    "applications": [{"application_id": 7, "application_name": "payments",
      "namespace": "payments", "status": "Healthy", "deployment": {}, "pods": []}]
  }],
  "refreshed_at": "..."
}
```

Catch each environment target independently and sanitize failures to approved messages.

- [ ] **Step 4: Run Service tests and verify GREEN**

Run: `cd backend && python -m pytest tests/test_project_runtime_service.py -q`

Expected: all tests pass.

- [ ] **Step 5: Write failing route tests**

Assert authenticated Project access returns the unified envelope, missing Project returns 404, and no data crosses Project boundaries.

- [ ] **Step 6: Add and register the Runtime blueprint**

Expose only `GET /api/projects/<int:project_id>/runtime`; use `ProjectService().get(project_id)` and delegate to `ProjectRuntimeService`.

- [ ] **Step 7: Run route regression tests and commit**

Run: `cd backend && python -m pytest tests/test_project_runtime_service.py tests/test_runtime_routes.py tests/test_project_application_routes.py -q`

Expected: all tests pass.

```bash
git add backend/app/services/project_runtime_service.py backend/app/routes/runtime.py backend/app/routes/__init__.py backend/app/__init__.py backend/app/services/kubernetes_service.py backend/tests/test_project_runtime_service.py backend/tests/test_runtime_routes.py
git commit -m "feat: aggregate project runtime status"
```

### Task 3: Governed restart, delete, logs, and YAML operations

**Files:**
- Create: `backend/app/services/runtime_operation_service.py`
- Create: `backend/tests/test_runtime_operation_service.py`
- Modify: `backend/app/routes/runtime.py`
- Modify: `backend/app/services/kubernetes_service.py`
- Modify: `backend/tests/test_runtime_routes.py`

**Interfaces:**
- Produces: `RuntimeOperationService.deployment_manifest(context, name)`.
- Produces: `restart_deployment(context, name, actor, confirmed, reason=None)` and `delete_pod(context, pod, actor, confirmed, reason=None)`.
- Produces HTTP routes under `/api/projects/<project_id>/applications/<app_id>/environments/<environment>/runtime/...`.

- [ ] **Step 1: Write failing ownership and confirmation tests**

Tests must prove an unconfirmed mutation returns `CONFIRMATION_REQUIRED`, a Pod not controlled by the Application is rejected, a valid restart patches only the resolved Deployment, a valid delete targets only the resolved Namespace, and success/failure both finish an audit without raw Kubernetes exception bodies.

- [ ] **Step 2: Run tests and verify RED**

Run: `cd backend && python -m pytest tests/test_runtime_operation_service.py -q`

Expected: import or attribute failures for the new Service methods.

- [ ] **Step 3: Add minimal Kubernetes primitives**

Implement `get_deployment_manifest`, `restart_deployment`, `delete_application_pod`, and resource ownership checks. Restart patches only `spec.template.metadata.annotations["kubectl.kubernetes.io/restartedAt"]`; YAML serialization uses `ApiClient.sanitize_for_serialization` and never returns Secret resources.

- [ ] **Step 4: Implement the operation Service and routes**

Resolve context with `DeliveryContextService`, require JSON `confirmed: true`, use `g.current_user`, create/finish audits around mutations, and return “操作已提交” rather than “已健康”. Validate bounded resource names and reasons in the Route.

- [ ] **Step 5: Run focused and regression tests**

Run: `cd backend && python -m pytest tests/test_runtime_operation_service.py tests/test_runtime_routes.py tests/test_project_application_routes.py -q`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/runtime_operation_service.py backend/app/services/kubernetes_service.py backend/app/routes/runtime.py backend/tests/test_runtime_operation_service.py backend/tests/test_runtime_routes.py
git commit -m "feat: govern runtime resource operations"
```

### Task 4: Single-use Pod exec sessions and WebSocket bridge

**Files:**
- Create: `backend/app/services/runtime_exec_service.py`
- Create: `backend/app/runtime_exec_registry.py`
- Create: `backend/tests/test_runtime_exec_service.py`
- Create: `backend/tests/test_runtime_exec_socket.py`
- Modify: `backend/app/routes/runtime.py`
- Modify: `backend/app/services/kubernetes_service.py`
- Modify: `backend/app/__init__.py`
- Modify: `backend/app/config.py`
- Modify: `backend/requirements.txt`

**Interfaces:**
- Produces: `RuntimeExecService.create(context, pod, container, actor, reason) -> {ticket, expires_at, websocket_url}`.
- Produces: `RuntimeExecRegistry.consume(ticket, actor_id)` with atomic single use, 60-second TTL, two-per-user and one-per-Pod/container limits.
- Produces: `WS /api/runtime/exec/<ticket>` using JSON control frames `{type:"stdin"|"resize", ...}` and `{type:"stdout"|"stderr"|"status", ...}`.

- [ ] **Step 1: Write failing registry and session tests**

Use a fake clock to assert 60-second expiration, one-time consumption, actor binding, two-session user limit, one-session target limit, release on disconnect, and required non-empty reason. Assert audit metadata contains no terminal frames.

- [ ] **Step 2: Verify RED**

Run: `cd backend && python -m pytest tests/test_runtime_exec_service.py -q`

Expected: missing registry/service imports.

- [ ] **Step 3: Implement in-memory ticket registry and session creation**

Use `secrets.token_urlsafe(32)`, a lock around registry state, stored actor/context snapshot, and explicit `consume`, `touch`, and `release`. Configuration values are `RUNTIME_EXEC_TICKET_TTL_SECONDS=60`, `RUNTIME_EXEC_IDLE_TIMEOUT_SECONDS=900`, `RUNTIME_EXEC_MAX_PER_USER=2`, and `RUNTIME_EXEC_MAX_PER_TARGET=1`.

- [ ] **Step 4: Run Service tests and verify GREEN**

Run: `cd backend && python -m pytest tests/test_runtime_exec_service.py -q`

Expected: all tests pass.

- [ ] **Step 5: Write failing WebSocket bridge tests**

Cover invalid/expired ticket closure, Origin mismatch, stdout/stderr forwarding, stdin and resize forwarding, idle timeout, Kubernetes disconnect, registry release, and audit completion. Use fake WebSocket and fake Kubernetes stream objects; no live cluster.

- [ ] **Step 6: Add Flask-Sock bridge and Kubernetes exec adapter**

Add pinned compatible dependencies, initialize the socket adapter in `create_app`, authenticate the ticket against the issuing user/session snapshot, validate configured Origin, and bridge frames without logging payloads. `KubernetesService.open_pod_exec` validates Pod/container ownership and calls Kubernetes stream with `stdin/stdout/stderr/tty=True`.

- [ ] **Step 7: Run exec tests and dependency/security regression**

Run: `cd backend && python -m pytest tests/test_runtime_exec_service.py tests/test_runtime_exec_socket.py tests/test_auth_routes.py -q`

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/runtime_exec_service.py backend/app/runtime_exec_registry.py backend/app/routes/runtime.py backend/app/services/kubernetes_service.py backend/app/__init__.py backend/app/config.py backend/requirements.txt backend/tests/test_runtime_exec_service.py backend/tests/test_runtime_exec_socket.py
git commit -m "feat: add audited pod exec sessions"
```

### Task 5: Runtime API client and data-state tests

**Files:**
- Create: `frontend/src/api/runtime.ts`
- Create: `frontend/src/api/runtime.test.ts`
- Create: `frontend/src/composables/useProjectRuntime.ts`
- Create: `frontend/src/composables/useProjectRuntime.test.ts`
- Modify: `frontend/src/types.ts`

**Interfaces:**
- Produces TypeScript types `ProjectRuntimeOverview`, `RuntimeEnvironmentGroup`, `RuntimeApplication`, `RuntimePod`, and `RuntimeExecSession`.
- Produces `runtimeApi.overview`, `deploymentYaml`, `restartDeployment`, `podLogs`, `podYaml`, `deletePod`, `containers`, and `createExecSession`.
- Produces `useProjectRuntime(projectId)` with `overview`, filters, `filteredEnvironments`, `refresh`, automatic 30-second refresh, and visibility pause.

- [ ] **Step 1: Write failing API and composable tests**

Assert exact Project-scoped URLs and payloads, filter behavior across environment/status/keyword, 30-second refresh, pause while `document.hidden`, preservation of last successful data after refresh failure, and cleanup on unmount.

- [ ] **Step 2: Verify RED**

Run: `cd frontend && npm test -- src/api/runtime.test.ts src/composables/useProjectRuntime.test.ts`

Expected: missing module failures.

- [ ] **Step 3: Add types, API module, and composable**

Keep all HTTP calls in `frontend/src/api/runtime.ts`. The composable owns timers and filter derivation but no Element Plus UI; expose a sanitized `refreshError` for the View.

- [ ] **Step 4: Run tests and commit**

Run: `cd frontend && npm test -- src/api/runtime.test.ts src/composables/useProjectRuntime.test.ts`

Expected: all tests pass.

```bash
git add frontend/src/types.ts frontend/src/api/runtime.ts frontend/src/api/runtime.test.ts frontend/src/composables/useProjectRuntime.ts frontend/src/composables/useProjectRuntime.test.ts
git commit -m "feat: add project runtime frontend state"
```

### Task 6: Project Runtime page and interactive terminal

**Files:**
- Create: `frontend/src/views/ProjectRuntime.vue`
- Create: `frontend/src/components/runtime/RuntimeEnvironmentGroup.vue`
- Create: `frontend/src/components/runtime/RuntimeResourceDrawer.vue`
- Create: `frontend/src/components/runtime/RuntimeTerminalDrawer.vue`
- Create: `frontend/src/components/runtime/runtime-view-model.ts`
- Create: `frontend/src/components/runtime/runtime-view-model.test.ts`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/package.json`

**Interfaces:**
- Consumes: Task 5 runtime API, types, and composable.
- Produces: `/devcenter/projects/:projectId/runtime` as the dedicated responsive Runtime workspace.
- Terminal component consumes `RuntimeExecSession.websocket_url` and sends/receives the Task 4 frame protocol.

- [ ] **Step 1: Write failing view-model tests**

Test status tone/label mapping, production detection, aggregate metric formatting, restart/delete confirmation copy, and terminal frame encode/decode without mounting a browser UI.

- [ ] **Step 2: Verify RED**

Run: `cd frontend && npm test -- src/components/runtime/runtime-view-model.test.ts`

Expected: missing module failure.

- [ ] **Step 3: Implement the view model and verify GREEN**

Run the same test and expect all tests to pass.

- [ ] **Step 4: Build the Runtime inventory UI**

Implement header filters/actions, five metric cards, per-environment partial errors, expandable Application Deployment rows, Pod table/cards, empty states, and 30-second automatic refresh. Route Runtime to `ProjectRuntime.vue`; do not place HTTP requests directly in the View.

- [ ] **Step 5: Add governed drawers and terminal**

Resource drawer renders logs or JSON YAML. Restart/delete actions use `ElMessageBox.confirm` with stronger production copy and send `confirmed: true`. Terminal flow selects a container, requires a reason, creates a session, mounts xterm.js with fit support, bridges WebSocket frames, handles resize/close/status, and disposes terminal/socket listeners on drawer close.

- [ ] **Step 6: Run frontend tests, type check, and production build**

Run: `cd frontend && npm test && npm run build`

Expected: all Vitest tests pass; `vue-tsc` and Vite build succeed.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/views/ProjectRuntime.vue frontend/src/components/runtime frontend/src/router/index.ts frontend/package.json frontend/package-lock.json
git commit -m "feat: build project runtime workspace"
```

### Task 7: Documentation, full verification, and acceptance evidence

**Files:**
- Modify: `docs/current-state.md`
- Modify: `specs/active/project-runtime-workspace.md`
- Move after acceptance: `specs/active/project-runtime-workspace.md` → `specs/completed/project-runtime-workspace.md`

**Interfaces:**
- Consumes all preceding tasks.
- Produces repository-level verification evidence and an accepted completed spec.

- [ ] **Step 1: Run the complete verification harness**

Run: `./scripts/verify.sh`

Expected: backend tests, migration checks, frontend tests/type checks, and production build all pass without interactive or online-cluster dependencies.

- [ ] **Step 2: Perform browser acceptance**

Verify desktop and narrow widths, environment grouping, filters, partial errors, refresh pause/resume, logs/YAML drawers, production warnings, restart/delete submitted state, terminal open/resize/close, and no terminal payload in server logs. Record concrete results in the spec.

- [ ] **Step 3: Update current state and acceptance checklist**

Document only verified capabilities and any known gaps. Check every acceptance item only when evidence exists; move the spec to completed only after all are satisfied.

- [ ] **Step 4: Re-run doc and repository checks**

Run: `git diff --check && ./scripts/verify.sh`

Expected: no whitespace errors and the full harness passes again after documentation changes.

- [ ] **Step 5: Commit**

```bash
git add docs/current-state.md specs/active/project-runtime-workspace.md specs/completed/project-runtime-workspace.md
git commit -m "docs: accept project runtime workspace"
```
