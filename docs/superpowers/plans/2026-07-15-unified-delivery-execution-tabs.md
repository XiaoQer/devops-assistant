# Unified Delivery Execution Tabs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace separate build and environment delivery sections with one compact execution selector and one shared Task/Step log panel.

**Architecture:** Keep API loading and request-generation guards in `ApplicationBuildExplorer.vue`. Add pure selection helpers to the existing build-explorer state module, then replace `BuildDeliveryTargets` composition with a focused unified execution component that renders build/environment tabs and delegates actual step/log rendering to `PipelineStepLogPanel`.

**Tech Stack:** Vue 3 Composition API, TypeScript, Element Plus, Vitest, scoped CSS.

## Global Constraints

- Frontend HTTP requests remain in `frontend/src/api`; views only call existing API clients.
- Build and deploy execution data remain separate; only their selection and display container are unified.
- Waiting approval or missing PipelineRun states must not create steps or trigger log requests.
- A stale build or target log response must never replace the current selection.
- Production or destructive behavior is unchanged.

---

### Task 1: Unified Execution Selection State

**Files:**
- Modify: `frontend/src/features/build-explorer/state.ts`
- Test: `frontend/src/features/build-explorer/state.test.ts`

**Interfaces:**
- Consumes: `ReleaseBatch`, current selected target ID.
- Produces: `type DeliveryExecutionKey = 'build' | \`target:${number}\``, `targetIdFromExecutionKey(key)`, and `preserveExecutionKey(key, batch)`.

- [ ] **Step 1: Write failing selection tests**

Add tests proving `build` is the default, `target:7` resolves to target 7, an existing selected target is preserved after refresh, and a removed target falls back to `build`.

- [ ] **Step 2: Verify RED**

Run: `npm --prefix frontend test -- --run`

Expected: FAIL because the unified execution helpers do not exist.

- [ ] **Step 3: Implement minimal pure helpers**

Implement exact key parsing and batch membership checks without introducing UI or API dependencies.

- [ ] **Step 4: Verify GREEN**

Run: `npm --prefix frontend test -- --run`

Expected: all state tests pass.

- [ ] **Step 5: Commit**

Commit message: `feat: model unified delivery execution selection`.

### Task 2: Shared Execution Panel

**Files:**
- Create: `frontend/src/components/pipeline/DeliveryExecutionPanel.vue`
- Modify: `frontend/src/components/pipeline/PipelineStepLogPanel.vue`
- Modify: `frontend/src/components/pipeline/ApplicationBuildDetail.vue`
- Delete: `frontend/src/components/pipeline/BuildDeliveryTargets.vue`
- Test: `frontend/src/features/build-explorer/state.test.ts`

**Interfaces:**
- Consumes: build status/PipelineRun presence, optional `ReleaseBatch`, selected execution key, current `ExecutionStepDetail[]`, loading and error state.
- Emits: `select-execution`, `select-step`, and `retry`.
- Produces: one execution-tab row followed by exactly one step/log display or one truthful waiting state.

- [ ] **Step 1: Add a failing presentation-model test**

Add a pure `deliveryExecutionOptions(build, batch)` expectation with build first, environments in target order, and each option carrying its real status and PipelineRun availability.

- [ ] **Step 2: Verify RED**

Run: `npm --prefix frontend test -- --run`

Expected: FAIL because `deliveryExecutionOptions` is missing.

- [ ] **Step 3: Implement the presentation model and component**

Create compact build/environment buttons. Render `PipelineStepLogPanel` once for runnable selections; render the existing truthful build/target empty description otherwise. Add a `compact`/header configuration to avoid duplicate section headings while retaining step names and log header.

- [ ] **Step 4: Replace the old composition**

Make `ApplicationBuildDetail.vue` render only `DeliveryExecutionPanel` after build facts. Remove unused legacy step/log CSS and delete `BuildDeliveryTargets.vue`.

- [ ] **Step 5: Verify component compilation and production output**

Run: `npm --prefix frontend test -- --run && frontend/node_modules/.bin/vue-tsc --noEmit -p frontend/tsconfig.app.json && npm --prefix frontend run build`

Expected: tests, type checking, and Vite build pass.

- [ ] **Step 6: Commit**

Commit message: `feat: unify build and environment execution layout`.

### Task 3: Explorer Data Flow and Refresh Preservation

**Files:**
- Modify: `frontend/src/views/ApplicationBuildExplorer.vue`
- Modify: `frontend/src/features/build-explorer/state.ts`
- Test: `frontend/src/features/build-explorer/state.test.ts`

**Interfaces:**
- Consumes: unified execution key helpers from Task 1 and the panel events from Task 2.
- Produces: default build selection, on-demand environment log loading, refresh preservation, and target removal fallback.

- [ ] **Step 1: Add failing transition tests**

Test that selecting `build` never maps to a target request, selecting `target:7` maps to target 7, a refresh keeps `target:7` while present, and falls back to `build` when absent.

- [ ] **Step 2: Verify RED**

Run: `npm --prefix frontend test -- --run`

Expected: FAIL until the transition helper is complete.

- [ ] **Step 3: Replace separate build/target selection state**

Use one `selectedExecutionKey`. On build load select `build`; on polling refresh preserve an existing selected target. Load build logs for `build`, target logs only for a parsed target key with a PipelineRun, and retain both request-generation guards.

- [ ] **Step 4: Verify GREEN and stale-response protection**

Run: `npm --prefix frontend test -- --run && frontend/node_modules/.bin/vue-tsc --noEmit -p frontend/tsconfig.app.json`

Expected: all tests and type checks pass.

- [ ] **Step 5: Commit**

Commit message: `refactor: drive delivery detail from one execution selection`.

### Task 4: Responsive Polish, Documentation, and Final Verification

**Files:**
- Modify: `frontend/src/components/pipeline/DeliveryExecutionPanel.vue`
- Modify: `docs/current-state.md`
- Modify then move: `specs/active/unified-delivery-execution-tabs.md` to `specs/completed/unified-delivery-execution-tabs.md`

**Interfaces:**
- Consumes: completed unified panel.
- Produces: compact desktop layout, horizontally scrollable mobile tabs, final capability documentation and verification evidence.

- [ ] **Step 1: Add responsive styling**

Use a single flex row with `overflow-x: auto`, fixed minimum tab widths, compact padding, and no separate environment section border or large cards.

- [ ] **Step 2: Run full verification**

Run: `./scripts/verify.sh`

Expected: backend tests, frontend tests, Vue type checking, and production build pass.

- [ ] **Step 3: Update project memory and acceptance evidence**

Document the unified execution selector in `docs/current-state.md`, check every acceptance condition, record exact test counts, set the spec to accepted, and move it to `specs/completed/`.

- [ ] **Step 4: Review the complete diff**

Check for duplicate log panels, stale selection races, invented waiting steps, unused CSS/components, and unrelated changes. Run `git diff --check`.

- [ ] **Step 5: Commit**

Commit message: `docs: complete unified delivery execution tabs`.
