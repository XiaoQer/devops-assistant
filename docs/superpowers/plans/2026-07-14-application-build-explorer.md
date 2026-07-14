# Application Build Explorer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Project-scoped Application page that shows build history on the left and the selected build's metadata, Clone/Build/Push steps, and step logs on the right.

**Architecture:** Add a scoped single-build read endpoint to make deep links authoritative, then create a dedicated Vue route composed from a history list and detail panel. Keep selection, step normalization, and polling decisions in pure TypeScript helpers covered by Vitest; use existing Application and Pipeline APIs for business history and Tekton logs.

**Tech Stack:** Flask, SQLAlchemy, unittest, Vue 3, TypeScript, Vue Router, Element Plus, Vitest, Vite.

## Global Constraints

- `Project` remains the governance and workspace boundary; every build lookup must scope by Project and Application.
- Business history comes from MySQL `ApplicationBuildVersion`; execution steps and logs come from existing Tekton Pipeline endpoints.
- HTTP handlers validate transport inputs and delegate build lookup to `BuildVersionService`.
- Frontend requests remain in `frontend/src/api`; Views must not issue HTTP requests directly.
- Do not modify build, release, approval, retry, or Tekton execution behavior.
- Do not expose image registry credentials or Application Secrets in API responses, logs, tests, or documentation.
- Preserve the unified API response envelope.
- Desktop layout is left history/right detail; narrow layout is history above/detail below.

---

### Task 1: Scoped Single-Build Read API

**Files:**
- Modify: `backend/app/services/build_version_service.py`
- Modify: `backend/app/routes/applications.py`
- Modify: `backend/tests/test_project_application_routes.py`

**Interfaces:**
- Produces: `BuildVersionService.get(app: Application, build_id: int) -> dict`
- Produces: `GET /api/projects/:projectId/applications/:appId/build-versions/:buildId`
- Response data is an existing `BuildVersion` dictionary; missing or cross-Application IDs return 404.

- [ ] **Step 1: Write failing route tests for scoped lookup**

Add tests that create two Applications and build records, then assert the matching build returns 200 while an ID owned by the other Application returns 404:

```python
def test_get_build_version_is_scoped_to_application(self):
    own = self._create_build_version(self.application)
    response = self.client.get(
        f"/api/projects/{self.project.id}/applications/{self.application.id}/build-versions/{own.id}"
    )
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.get_json()["data"]["id"], own.id)

def test_get_build_version_rejects_other_application(self):
    other_app = self._create_application(name="other-build-app")
    foreign = self._create_build_version(other_app)
    response = self.client.get(
        f"/api/projects/{self.project.id}/applications/{self.application.id}/build-versions/{foreign.id}"
    )
    self.assertEqual(response.status_code, 404)
```

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```bash
cd backend && python -m unittest \
  tests.test_project_application_routes.ProjectApplicationRoutesTest.test_get_build_version_is_scoped_to_application \
  tests.test_project_application_routes.ProjectApplicationRoutesTest.test_get_build_version_rejects_other_application
```

Expected: FAIL because the nested build-version detail route does not exist.

- [ ] **Step 3: Implement scoped service and route**

Add to `BuildVersionService`:

```python
def get(self, app, build_id):
    item = ApplicationBuildVersion.query.filter_by(
        id=build_id,
        project_id=app.project_id,
        application_id=app.id,
    ).first()
    if item is None:
        raise NotFound("Build version not found")
    return item.to_dict()
```

Add to the Application routes beside the list route:

```python
@bp.get("/<int:app_id>/build-versions/<int:build_id>")
def get_build_version(project_id, app_id, build_id):
    app = get_application(project_id, app_id)
    return success(BuildVersionService().get(app, build_id))
```

- [ ] **Step 4: Run focused and related tests and verify GREEN**

Run:

```bash
cd backend && python -m unittest tests.test_project_application_routes
```

Expected: PASS with zero failures.

- [ ] **Step 5: Commit Task 1**

```bash
git add backend/app/services/build_version_service.py backend/app/routes/applications.py \
  backend/tests/test_project_application_routes.py
git commit -m "feat: add scoped build version detail api"
```

---

### Task 2: Tested Build Explorer State Helpers

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `frontend/src/types.ts`
- Create: `frontend/src/features/build-explorer/state.ts`
- Create: `frontend/src/features/build-explorer/state.test.ts`
- Modify: `frontend/src/api/application.ts`

**Interfaces:**
- Produces: `BuildStepDetail { id, label, status, startedAt?, finishedAt?, logs }`
- Produces: `selectRequestedBuild(builds, requestedId) -> { build?, invalidRequestedId }`
- Produces: `normalizeBuildSteps(logDetails) -> BuildStepDetail[]`
- Produces: `defaultStepId(steps) -> string | undefined`
- Produces: `shouldPollBuild(status) -> boolean`
- Produces: `applicationApi.buildVersion(projectId, applicationId, buildId)`.

- [ ] **Step 1: Install and configure the minimal test runner**

Run:

```bash
cd frontend && npm install --save-dev vitest
```

Add the script:

```json
"test": "vitest run"
```

- [ ] **Step 2: Write failing pure-state tests**

Cover these exact behaviors:

```ts
it('selects the latest build when no id is requested', () => {
  expect(selectRequestedBuild([build(42), build(41)], undefined).build?.id).toBe(42)
})

it('rejects an id outside the application build list', () => {
  expect(selectRequestedBuild([build(42)], 99)).toEqual({ build: undefined, invalidRequestedId: true })
})

it('normalizes task steps into clone build and push order', () => {
  expect(normalizeBuildSteps(logDetails).map(step => step.id)).toEqual(['clone', 'build', 'push'])
})

it('selects the first failed step before build', () => {
  expect(defaultStepId([step('clone', 'Succeeded'), step('build', 'Failed')])).toBe('build')
})

it('polls only non-terminal build states', () => {
  expect(shouldPollBuild('Running')).toBe(true)
  expect(shouldPollBuild('Succeeded')).toBe(false)
  expect(shouldPollBuild('Failed')).toBe(false)
})
```

- [ ] **Step 3: Run tests and verify RED**

Run:

```bash
cd frontend && npm test -- src/features/build-explorer/state.test.ts
```

Expected: FAIL because `state.ts` and its exports do not exist.

- [ ] **Step 4: Implement minimal helpers and API typing**

Implement deterministic helpers without Vue or HTTP dependencies. Normalize task/step names case-insensitively by matching `clone`, `build`/`kaniko`, and `push`; preserve returned logs and timestamps. Extend the Pipeline log response types in `types.ts` rather than duplicating inline anonymous types, then add:

```ts
buildVersion: (projectId: number, id: number, buildId: number) =>
  client.get<never, BuildVersion>(
    `/projects/${projectId}/applications/${id}/build-versions/${buildId}`,
  ),
```

- [ ] **Step 5: Run tests and type check and verify GREEN**

Run:

```bash
cd frontend && npm test -- src/features/build-explorer/state.test.ts
cd frontend && ./node_modules/.bin/vue-tsc -b
```

Expected: all helper tests pass and type check exits 0.

- [ ] **Step 6: Commit Task 2**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/types.ts \
  frontend/src/features/build-explorer/state.ts \
  frontend/src/features/build-explorer/state.test.ts frontend/src/api/application.ts
git commit -m "test: define build explorer state behavior"
```

---

### Task 3: Build History and Detail Components

**Files:**
- Create: `frontend/src/components/pipeline/ApplicationBuildHistory.vue`
- Create: `frontend/src/components/pipeline/ApplicationBuildDetail.vue`
- Create: `frontend/src/views/ApplicationBuildExplorer.vue`
- Modify: `frontend/src/router/index.ts`

**Interfaces:**
- `ApplicationBuildHistory` consumes `builds`, `selectedId`, `loading`; emits `select(buildId)`.
- `ApplicationBuildDetail` consumes `build`, `steps`, `selectedStepId`, `loading`, `logsError`; emits `select-step(stepId)` and `retry-logs`.
- `ApplicationBuildExplorer` owns route selection, cancellation token, 15-second polling, API loading, and responsive scroll behavior.

- [ ] **Step 1: Add a failing route contract test to the helper suite**

Extract and test a route builder in `state.ts` whose first implementation requires `buildId`:

```ts
it('builds a stable deep link for an application build', () => {
  expect(buildExplorerPath(7, 12, 42)).toBe(
    '/devcenter/projects/7/pipelines/applications/12/builds/42',
  )
})
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
cd frontend && npm test -- src/features/build-explorer/state.test.ts
```

Expected: FAIL because `buildExplorerPath` is not exported.

- [ ] **Step 3: Implement route builder, route, and focused components**

Add the child route before `pipelines/:name` so the generic name route cannot capture `applications`:

```ts
{
  path: 'projects/:projectId/pipelines/applications/:applicationId/builds/:buildId?',
  component: () => import('../views/ApplicationBuildExplorer.vue'),
  meta: { title: 'Application builds' },
},
```

The View must:

1. Load `applicationApi.get` and `applicationApi.buildVersions` in parallel.
2. Resolve the route ID with `selectRequestedBuild`.
3. When no ID is present, call `router.replace(buildExplorerPath(...latest.id))`.
4. Fetch selected build through `applicationApi.buildVersion` and logs through `pipelineApi.logs` when a PipelineRun exists.
5. Use an incrementing request generation; apply responses only when the generation still matches.
6. Select `defaultStepId(normalizeBuildSteps(logs))` after each build change.
7. Poll every 15 seconds only while `shouldPollBuild(selectedBuild.status)` is true.
8. Clear timers on unmount and when the selected build reaches a terminal state.

The history component must render version/status/branch/short SHA/time/duration with semantic buttons. The detail component must render metadata, step buttons, selected logs in a `pre` block, loading skeletons, and truthful empty/error states.

- [ ] **Step 4: Run helper tests, type check, and production build**

Run:

```bash
cd frontend && npm test
cd frontend && ./node_modules/.bin/vue-tsc -b
cd frontend && npm run build
```

Expected: tests pass, type check exits 0, Vite production build succeeds.

- [ ] **Step 5: Commit Task 3**

```bash
git add frontend/src/features/build-explorer/state.ts \
  frontend/src/features/build-explorer/state.test.ts \
  frontend/src/components/pipeline/ApplicationBuildHistory.vue \
  frontend/src/components/pipeline/ApplicationBuildDetail.vue \
  frontend/src/views/ApplicationBuildExplorer.vue frontend/src/router/index.ts
git commit -m "feat: add application build explorer page"
```

---

### Task 4: Workbench Integration, Empty Build Action, and Completion

**Files:**
- Modify: `frontend/src/views/PipelineRuns.vue`
- Modify: `frontend/src/views/ApplicationBuildExplorer.vue`
- Modify: `docs/current-state.md`
- Modify then move: `specs/active/application-build-explorer.md` to `specs/completed/application-build-explorer.md`

**Interfaces:**
- Workbench detail icon navigates with `buildExplorerPath(projectId, applicationId, latestBuildId?)`.
- Empty explorer state opens `QuickBuildDrawer` for the loaded Application and reloads history after submission.

- [ ] **Step 1: Write a failing route-builder regression test for missing build ID**

```ts
it('builds the application build history path without a build id', () => {
  expect(buildExplorerPath(7, 12)).toBe(
    '/devcenter/projects/7/pipelines/applications/12/builds',
  )
})
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
cd frontend && npm test -- src/features/build-explorer/state.test.ts
```

Expected: FAIL until the route builder handles an omitted build ID without appending `undefined`.

- [ ] **Step 3: Wire the workbench and empty state**

Extend `buildExplorerPath` so `buildId` is optional, then replace `openApplication` navigation in
`PipelineRuns.vue` with the route builder. In the explorer, render `QuickBuildDrawer` when no builds exist;
after `submitted`, close the drawer, reload builds, select the newly latest build, and replace the URL.

- [ ] **Step 4: Update project memory and acceptance evidence**

Update `docs/current-state.md` to state that the Project CI/CD workbench links to a dedicated Application build explorer with history, metadata, steps, and selected-step logs. Mark every acceptance condition in the active spec only when supported by evidence; record test commands and known visual-verification gaps. Move the accepted spec to `specs/completed/`.

- [ ] **Step 5: Run full verification**

Run:

```bash
./scripts/verify.sh
```

Expected: all backend tests, frontend Vitest tests, type check, and production build pass. If `verify.sh` does not yet run `npm test`, update it to run the non-interactive frontend test command before the build and rerun the complete script.

- [ ] **Step 6: Manually verify the key UX**

Verify at desktop and narrow viewport widths:

1. Workbench detail icon opens the dedicated build page.
2. Latest build is selected automatically and URL is canonicalized.
3. Selecting history changes metadata, steps, and logs without leaving the page.
4. Failed step is selected by default; otherwise Build is selected.
5. Missing logs retain build metadata and show a retryable error.
6. Empty history can open quick build.

- [ ] **Step 7: Commit Task 4**

```bash
git add frontend/src/views/PipelineRuns.vue frontend/src/views/ApplicationBuildExplorer.vue \
  frontend/src/features/build-explorer/state.ts frontend/src/features/build-explorer/state.test.ts \
  frontend/package.json frontend/package-lock.json scripts/verify.sh docs/current-state.md \
  specs/completed/application-build-explorer.md
git commit -m "feat: link workbench to application build history"
```
