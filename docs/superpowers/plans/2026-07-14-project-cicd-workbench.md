# Project CI/CD Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the Project pipelines page into an Application-first CI/CD workbench that can trigger exact-Commit builds with optional initial environments and append environments after a successful build.

**Architecture:** Keep `ApplicationReleaseBatch` as the durable record for an exact-Commit build and allow it to start with zero targets. Add a focused service for appending validated targets and a Project-level workbench query service that aggregates MySQL delivery history without per-card Kubernetes calls. Reuse the existing Git metadata, Delivery Reconciler, approval, Tekton, and Build once/Promote paths; the Vue page calls only `frontend/src/api` and delegates build/release forms to focused drawer components.

**Tech Stack:** Flask, Flask-SQLAlchemy, MySQL/SQLite tests, unittest, Vue 3 Composition API, TypeScript, Element Plus, Vite.

## Global Constraints

- `Project` remains the governance and workspace boundary; all Application, environment, batch, and PipelineRun lookups must verify Project ownership.
- HTTP routes perform transport validation and delegate business behavior to Services.
- Kubernetes access remains in `KubernetesService`; Tekton resource operations remain in `TektonService`.
- API responses retain `success`, `message`, `data`, `timestamp`, and `trace_id`.
- Production or destructive actions retain explicit confirmation or approval.
- API, logs, tests, and docs must not expose registry credentials, application Secrets, or kubeconfig.
- No multi-Application build, cross-Project workbench, Pipeline cancellation, scheduling, webhook triggers, Pipeline editor, background Reconciler, image Digest work, or new RBAC.

---

### Task 1: Optional Targets and Post-Build Target Append

**Files:**
- Modify: `backend/app/services/release_batch_service.py`
- Modify: `backend/app/routes/applications.py`
- Test: `backend/tests/test_release_batch_service.py`
- Test: `backend/tests/test_project_application_routes.py`

**Interfaces:**
- Consumes: `ReleaseBatchService.create(app, branch, git_commit, environment_ids, user)` and the existing `DeliveryReconciler.reconcile_batch(batch_id)`.
- Produces: `ReleaseBatchService.add_targets(app, batch_id, environment_ids) -> ApplicationReleaseBatch` and `POST /api/projects/<project_id>/applications/<app_id>/release-batches/<batch_id>/targets` with `{environment_ids: number[]}`.

- [ ] **Step 1: Write failing service tests for a build-only batch**

Create `backend/tests/test_release_batch_service.py` with an in-memory app fixture and patched Git/build services. Assert that `create(..., environment_ids=[])` returns a persisted batch with `targets == []`, calls `ApplicationService.build()` with the selected branch and Commit, and does not reject the empty list.

```python
@patch("app.services.release_batch_service.ApplicationService.build")
@patch("app.services.release_batch_service.GitMetadataService.list_commits")
def test_create_allows_build_only_batch(self, commits, build):
    commits.return_value = [{"sha": "abc123", "message": "build", "author": "Dev"}]
    build.return_value = ApplicationBuildVersion(
        application_id=self.application.id, project_id=self.project.id,
        version="abc123", git_repo=self.application.repo_url,
        git_branch="main", git_commit="abc123", image_name="registry/app",
        image_tag="abc123", status="Pending", created_by="admin",
    )
    batch = ReleaseBatchService().create(
        self.application, "main", "abc123", [], "admin"
    )
    self.assertEqual(batch.targets, [])
    self.assertEqual(batch.git_commit, "abc123")
```

- [ ] **Step 2: Run the build-only test and verify the current validation fails**

Run: `cd backend && pytest -q tests/test_release_batch_service.py::ReleaseBatchServiceTest::test_create_allows_build_only_batch`

Expected: FAIL with `RELEASE_ENVIRONMENTS_REQUIRED`.

- [ ] **Step 3: Relax only the non-empty requirement**

Change `ReleaseBatchService.create()` so `None` or a non-list remains invalid, while `[]` is valid. Keep integer coercion, ownership validation, Commit validation, transaction handling, and target creation unchanged for non-empty lists.

```python
if not isinstance(environment_ids, list):
    raise ApiError("发布环境选择无效", 400, "RELEASE_ENVIRONMENTS_INVALID")
unique_ids = list(dict.fromkeys(int(value) for value in environment_ids))
environments = []
if unique_ids:
    environments = ApplicationEnvironment.query.filter(
        ApplicationEnvironment.application_id == app.id,
        ApplicationEnvironment.id.in_(unique_ids),
    ).all()
```

- [ ] **Step 4: Write failing tests for appending targets**

Add tests proving `add_targets()`:

- accepts a succeeded build batch and creates targets for environments belonging to the Application;
- rejects a batch whose build version is not `Succeeded` with `BUILD_VERSION_NOT_READY`;
- rejects an already-associated environment with `RELEASE_TARGET_EXISTS`;
- rejects cross-Application and cross-Project environments;
- treats an empty append request as `RELEASE_ENVIRONMENTS_REQUIRED`.

```python
batch = ReleaseBatchService().add_targets(
    self.application, self.batch.id, [self.environment.id]
)
self.assertEqual([target.environment_id for target in batch.targets], [self.environment.id])
self.assertEqual(batch.targets[0].status, "Pending")
```

- [ ] **Step 5: Run append tests and verify `add_targets` is absent**

Run: `cd backend && pytest -q tests/test_release_batch_service.py -k 'add_targets'`

Expected: FAIL with `AttributeError: 'ReleaseBatchService' object has no attribute 'add_targets'`.

- [ ] **Step 6: Implement `add_targets()` with durable state gates**

Implement the method using `self.get(app, batch_id)`, require `batch.build_version` and `batch.build_version.status == "Succeeded"`, coerce and deduplicate IDs, verify every environment belongs to `app.id`, reject IDs already present in `batch.targets`, create `ApplicationReleaseTarget(status="Pending", build_version_id=batch.build_version_id)`, commit, then call `DeliveryReconciler().reconcile_batch(batch.id)` from the route after the transaction.

Use exact errors:

```python
raise ApiError("构建版本尚未成功，不能追加发布环境", 409, "BUILD_VERSION_NOT_READY")
raise ApiError("发布环境已经关联到该构建版本", 409, "RELEASE_TARGET_EXISTS")
```

- [ ] **Step 7: Add the append-target route and route coverage**

Add:

```python
@bp.post("/<int:app_id>/release-batches/<int:batch_id>/targets")
def add_release_batch_targets(project_id, app_id, batch_id):
    payload = json_object(request.get_json(silent=True), required=True)
    app = get_application(project_id, app_id)
    batch = ReleaseBatchService().add_targets(
        app, batch_id, payload.get("environment_ids")
    )
    return success(
        DeliveryReconciler().reconcile_batch(batch.id),
        "发布环境已追加", 201,
    )
```

Test 201, unified response fields, CSRF enforcement through the existing authenticated test client, and cross-Project rejection before reconciliation.

- [ ] **Step 8: Run focused backend tests**

Run: `cd backend && pytest -q tests/test_release_batch_service.py tests/test_project_application_routes.py`

Expected: PASS.

- [ ] **Step 9: Commit Task 1**

```bash
git add backend/app/services/release_batch_service.py backend/app/routes/applications.py backend/tests/test_release_batch_service.py backend/tests/test_project_application_routes.py
git commit -m "feat: support build-only and promoted release batches"
```

### Task 2: Project Workbench Aggregate API

**Files:**
- Create: `backend/app/services/cicd_workbench_service.py`
- Modify: `backend/app/routes/pipelines.py`
- Test: `backend/tests/test_cicd_workbench_service.py`
- Test: `backend/tests/test_project_application_routes.py`

**Interfaces:**
- Consumes: Project-scoped `Application`, `ApplicationEnvironment`, `ApplicationBuildVersion`, `ApplicationReleaseBatch`, `ApplicationReleaseTarget`, and `PipelineExecution` rows.
- Produces: `CicdWorkbenchService.list_applications(project_id, query=None, status=None) -> list[dict]` and `GET /api/projects/<project_id>/pipelines/workbench`.

- [ ] **Step 1: Write failing aggregate-service tests**

Create fixtures for two Applications with different latest build/batch/target states and assert:

```python
items = CicdWorkbenchService().list_applications(self.project.id)
self.assertEqual([item["application"]["name"] for item in items], ["recent", "older"])
self.assertEqual(items[0]["latest_build"]["git_commit"], "abc123")
self.assertEqual(items[0]["latest_batch"]["targets"][0]["environment"], "dev")
self.assertEqual(items[0]["available_environments"][0]["environment_name"], "prod")
```

Also assert query matches Application name or repository, status filters the derived latest state, empty Applications are returned with `latest_build=None`, and rows from another Project never appear.

- [ ] **Step 2: Run service tests and verify the module is absent**

Run: `cd backend && pytest -q tests/test_cicd_workbench_service.py`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement the focused aggregate service**

Load all Project Applications with eager loading for environments, build versions, release batches/targets, and executions. Derive one item per Application:

```python
{
    "application": app.to_dict(include_spec=False),
    "latest_build": latest_build.to_dict() if latest_build else None,
    "latest_batch": latest_batch.to_dict() if latest_batch else None,
    "latest_execution": latest_execution.to_dict() if latest_execution else None,
    "available_environments": [environment.to_dict() for environment in app.environments],
    "activity_status": derived_status,
    "last_activity_at": latest_timestamp.isoformat() if latest_timestamp else None,
}
```

Sort in Python by `last_activity_at` descending after deriving the summary. Do not query Kubernetes or expose configuration values.

- [ ] **Step 4: Add the Project-scoped endpoint**

Add a static route before `/<pipeline_run_name>/...`:

```python
@bp.get("/workbench")
def workbench(project_id):
    ProjectService().get(project_id)
    return success({
        "items": CicdWorkbenchService().list_applications(
            project_id,
            query=request.args.get("query", "").strip() or None,
            status=request.args.get("status", "").strip() or None,
        )
    })
```

Route tests assert authentication, Project existence, query/status forwarding, response envelope, and cross-Project isolation.

- [ ] **Step 5: Run focused aggregate and route tests**

Run: `cd backend && pytest -q tests/test_cicd_workbench_service.py tests/test_project_application_routes.py`

Expected: PASS.

- [ ] **Step 6: Commit Task 2**

```bash
git add backend/app/services/cicd_workbench_service.py backend/app/routes/pipelines.py backend/tests/test_cicd_workbench_service.py backend/tests/test_project_application_routes.py
git commit -m "feat: expose project CI/CD workbench summary"
```

### Task 3: Typed Frontend API and Focused Drawers

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api/pipeline.ts`
- Modify: `frontend/src/api/application.ts`
- Create: `frontend/src/components/pipeline/QuickBuildDrawer.vue`
- Create: `frontend/src/components/pipeline/PromoteBuildDrawer.vue`

**Interfaces:**
- Consumes: `GET /pipelines/workbench`, existing branch/Commit/environment endpoints, existing create-batch endpoint, and new append-target endpoint.
- Produces: `CicdWorkbenchItem`, `pipelineApi.workbench()`, `applicationApi.addReleaseBatchTargets()`, and drawer events `submitted(batch)`.

- [ ] **Step 1: Add exact frontend types and API methods**

Define:

```ts
export interface CicdWorkbenchItem {
  application: Application
  latest_build?: BuildVersion
  latest_batch?: ReleaseBatch
  latest_execution?: Execution
  available_environments: ApplicationEnvironment[]
  activity_status: string
  last_activity_at?: string
}
```

Add `pipelineApi.workbench(projectId, { query?, status? })`, allow `createReleaseBatch.environment_ids` to remain an array that may be empty, and add:

```ts
addReleaseBatchTargets: (projectId, applicationId, batchId, environmentIds) =>
  client.post<never, ReleaseBatch>(
    `/projects/${projectId}/applications/${applicationId}/release-batches/${batchId}/targets`,
    { environment_ids: environmentIds },
  )
```

- [ ] **Step 2: Build `QuickBuildDrawer.vue`**

Props: `modelValue`, `projectId`, `application`, `environments`. On open, load branches, select `application.branch` if present, load 20 Commits, and select the first Commit. Render branch, Commit, optional environment multi-select, Commit author/time/message, image Tag preview, loading/error states, cancel, and “确认并开始构建”. Emit `update:modelValue` and `submitted` only after `createReleaseBatch()` succeeds.

- [ ] **Step 3: Build `PromoteBuildDrawer.vue`**

Props: `modelValue`, `projectId`, `application`, `batch`, `environments`. Require `batch.build_version_id` and successful latest build before enabling submit. Exclude every environment ID already found in `batch.targets`; submit selected IDs through `addReleaseBatchTargets()` and emit the returned batch.

- [ ] **Step 4: Run frontend type checking**

Run: `cd frontend && npm run type-check`

Expected: PASS with no TypeScript errors.

- [ ] **Step 5: Commit Task 3**

```bash
git add frontend/src/types.ts frontend/src/api/pipeline.ts frontend/src/api/application.ts frontend/src/components/pipeline/QuickBuildDrawer.vue frontend/src/components/pipeline/PromoteBuildDrawer.vue
git commit -m "feat: add typed CI/CD workbench actions"
```

### Task 4: Application-First CI/CD Workbench Page

**Files:**
- Modify: `frontend/src/views/PipelineRuns.vue`
- Modify: `frontend/src/layouts/DevCenterLayout.vue`

**Interfaces:**
- Consumes: `pipelineApi.workbench()`, `pipelineApi.list()`, both new drawer components, and existing Pipeline detail/Application routes.
- Produces: the final `/devcenter/projects/:projectId/pipelines` workbench UI.

- [ ] **Step 1: Replace the page header and primary controls**

Use title `CI/CD 工作台`, description `跨 Application 快速构建、发布和跟踪交付状态。`, a search field, status select, recent-activity ordering, refresh, and a quick-build action that first asks for an Application when not invoked from a card.

- [ ] **Step 2: Render the responsive compact Application grid**

Render 3 columns on wide screens, 2 on medium screens, and 1 on narrow screens. Each card shows Application name, latest status, branch, short Commit, last activity, compact build/target state labels, and context-sensitive actions:

- `构建` when idle or after terminal build;
- `查看进度` for running builds;
- `查看日志` and `重试` for failed PipelineRuns;
- `发布此版本` only for a successful build with unassociated environments;
- detail links to Application and Pipeline views.

- [ ] **Step 3: Integrate build and promote drawers**

Opening from a card preselects the Application. A successful submission closes the drawer, shows an Element Plus success message, and reloads both workbench summaries and recent PipelineRuns. Keep user selections stable during periodic refresh.

- [ ] **Step 4: Preserve the PipelineRun list as “最近执行”**

Keep existing query/status-aware pagination and detail navigation below the Application grid. Do not duplicate the four old metric cards; derive concise counts inside the workbench toolbar so Application cards remain primary.

- [ ] **Step 5: Expose the CI/CD navigation item**

Add `{ name: 'CI/CD', path: `${base.value}/pipelines`, icon: '↯' }` to the Project-scoped `DevCenterLayout.vue` menu between Applications and Releases. Do not add a cross-Project route.

- [ ] **Step 6: Run production frontend checks**

Run: `cd frontend && npm run type-check && npm run build`

Expected: both commands PASS; existing Rollup size/comment warnings are allowed.

- [ ] **Step 7: Commit Task 4**

```bash
git add frontend/src/views/PipelineRuns.vue frontend/src/layouts/DevCenterLayout.vue
git commit -m "feat: build project CI/CD workbench"
```

### Task 5: Full Verification, Documentation, and Spec Completion

**Files:**
- Modify: `docs/current-state.md`
- Move: `specs/active/project-cicd-workbench.md` to `specs/completed/project-cicd-workbench.md`
- Modify: `specs/completed/project-cicd-workbench.md`

**Interfaces:**
- Consumes: all completed backend and frontend behavior.
- Produces: verified repository state and durable capability documentation.

- [ ] **Step 1: Run the focused backend suite**

Run: `cd backend && pytest -q tests/test_release_batch_service.py tests/test_cicd_workbench_service.py tests/test_project_application_routes.py`

Expected: PASS.

- [ ] **Step 2: Run the repository verification script**

Run: `./scripts/verify.sh`

Expected: backend tests, frontend type checking, frontend production build, and migration checks all PASS. Existing SQLAlchemy deprecation and Rollup bundle/comment warnings may remain warnings.

- [ ] **Step 3: Perform browser acceptance**

Open `/devcenter/projects/<projectId>/pipelines` with local test data and verify: 10–30-card responsive layout, default branch/latest Commit, zero-environment build submission, multi-environment submission, successful build promotion, approval label, filters, recent runs, and detail navigation. Record the exact checked behaviors in the spec Verification Evidence section; do not record credentials or Secret values.

- [ ] **Step 4: Update durable docs only after verification**

Add the implemented CI/CD workbench capability to `docs/current-state.md`. Change the spec status to `已验收`, add completion date `2026-07-14`, fill verification evidence with actual commands/results, and move it to `specs/completed/`.

- [ ] **Step 5: Commit Task 5**

```bash
git add docs/current-state.md specs/active/project-cicd-workbench.md specs/completed/project-cicd-workbench.md
git commit -m "docs: complete project CI/CD workbench"
```
