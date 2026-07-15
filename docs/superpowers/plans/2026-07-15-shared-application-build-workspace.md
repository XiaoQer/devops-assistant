# Shared Application Build Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render one shared build-history and execution-detail workspace in both the CI/CD build route and the Application Pipeline tab.

**Architecture:** Extract all route-neutral loading, selection, logging, polling, empty-state, and quick-build behavior from `ApplicationBuildExplorer.vue` into `ApplicationBuildWorkspace.vue`. Keep URL synchronization in the CI/CD route host; keep local selection in the Application tab host. Report application context and build count through component events so neither host duplicates build-history API calls.

**Tech Stack:** Vue 3 Composition API, TypeScript, Vue Router, Element Plus, Vitest, Vite.

## Global Constraints

- Frontend HTTP remains in `frontend/src/api`; no request is written directly in a component or view.
- Application Pipeline Tab and CI/CD page must render the same shared workspace component.
- Application Pipeline Tab must not keep its old list, toolbar, or duplicate build/release-batch requests.
- CI/CD build deep links must remain valid and invalid build IDs must retain the existing error state.
- Existing request gates, polling cleanup, approval waiting states, quick build, responsive layout, and sticky history behavior must be preserved.

---

### Task 1: Controlled Build Selection Contract

**Files:**
- Modify: `frontend/src/features/build-explorer/state.ts`
- Test: `frontend/src/features/build-explorer/state.test.ts`

**Interfaces:**
- Consumes: build list and optional host-selected build ID.
- Produces: `resolveWorkspaceBuild(builds, selectedBuildId)` returning the selected build, whether the requested ID is invalid, and whether the host needs selection synchronization.

- [ ] **Step 1: Write failing tests**

Cover explicit valid ID, explicit invalid ID, no ID selecting latest with synchronization, and empty list.

- [ ] **Step 2: Verify RED**

Run: `npm --prefix frontend test -- --run`

Expected: FAIL because `resolveWorkspaceBuild` is missing.

- [ ] **Step 3: Implement the pure helper**

Return `{ build, invalidRequestedId, shouldSyncSelection }` without Vue or router dependencies.

- [ ] **Step 4: Verify GREEN and commit**

Run: `npm --prefix frontend test -- --run`

Commit: `feat: define shared build workspace selection`.

### Task 2: Extract Route-Neutral Shared Workspace

**Files:**
- Create: `frontend/src/components/pipeline/ApplicationBuildWorkspace.vue`
- Modify: `frontend/src/views/ApplicationBuildExplorer.vue`
- Modify: `frontend/src/features/build-explorer/state.ts`
- Test: `frontend/src/features/build-explorer/state.test.ts`

**Interfaces:**
- Props: `projectId: number`, `applicationId: number`, `selectedBuildId?: number`.
- Emits: `application-loaded(application)`, `build-count(count)`, `select-build(buildId)`.
- Produces: the existing two-column workspace, context/error/invalid/empty states, unified execution detail, QuickBuildDrawer, route-neutral selection, refresh, logs, and polling cleanup.

- [ ] **Step 1: Move existing workspace template and state**

Move `ApplicationBuildHistory`, `ApplicationBuildDetail`, empty/error states, QuickBuildDrawer, API loading, request gates and polling from the route view into the shared component. Replace route reads with props and route writes with emitted `select-build` events.

- [ ] **Step 2: Preserve controlled and uncontrolled selection**

When a host ID exists, resolve it exactly; without one select the latest and emit its ID. Watch prop changes, reject stale requests, and avoid emitting selection loops.

- [ ] **Step 3: Reduce the route view to a host**

Keep PageHeader, return action, application context received from the workspace, and router push/replace behavior. Mount `ApplicationBuildWorkspace` once.

- [ ] **Step 4: Verify**

Run: `npm --prefix frontend test -- --run && frontend/node_modules/.bin/vue-tsc --noEmit -p frontend/tsconfig.app.json && npm --prefix frontend run build`

Expected: tests, type checking, production build and deep-link compilation pass.

- [ ] **Step 5: Commit**

Commit: `refactor: extract shared application build workspace`.

### Task 3: Replace Application Pipeline Tab

**Files:**
- Modify: `frontend/src/views/ApplicationDetail.vue`
- Modify: `frontend/src/components/pipeline/ApplicationBuildWorkspace.vue`

**Interfaces:**
- Consumes: shared workspace props and `build-count` event.
- Produces: Pipeline tab with identical workspace content and local build selection that does not modify the Application route.

- [ ] **Step 1: Mount the shared workspace**

Replace the old Pipeline panel template with `ApplicationBuildWorkspace`, bind project/application IDs and a local selected build ID, and update the tab count from `build-count`.

- [ ] **Step 2: Remove duplicate state and requests**

Remove `buildVersions`, `releaseBatches`, their load calls, `buildReleaseBatch`, `refreshReleaseBatches`, old Pipeline buttons and all build-list-only CSS.

- [ ] **Step 3: Verify local selection and compilation**

Run: `npm --prefix frontend test -- --run && frontend/node_modules/.bin/vue-tsc --noEmit -p frontend/tsconfig.app.json && npm --prefix frontend run build`

Expected: Pipeline tab compiles with the shared component and has no old-list references.

- [ ] **Step 4: Commit**

Commit: `feat: reuse build workspace in application pipeline tab`.

### Task 4: Review, Verification, and Documentation

**Files:**
- Modify: `docs/current-state.md`
- Modify then move: `specs/active/shared-application-build-workspace.md` to `specs/completed/shared-application-build-workspace.md`

- [ ] **Step 1: Review the complete diff**

Confirm both hosts render the same component, route writes exist only in the CI/CD host, the Application host keeps local selection, duplicate build/release-batch requests are gone, and component unmount invalidates polling and requests.

- [ ] **Step 2: Run full verification**

Run: `./scripts/verify.sh`

Expected: backend tests, frontend tests, Vue type checking, and production build pass.

- [ ] **Step 3: Update and archive documentation**

Record exact evidence, update `docs/current-state.md`, mark every acceptance item complete and move the spec to `specs/completed/`.

- [ ] **Step 4: Commit**

Commit: `docs: complete shared application build workspace`.
