# Build Delivery Execution Details Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show actual Build Pipeline Task/Steps and per-environment Deploy-only Pipeline steps and logs for the selected Application build.

**Architecture:** Replace the fixed Clone/Build/Push mapper with a generic order-preserving Tekton Task/Step flattener. Load release batches with build history, associate the selected build by `build_version_id`, and independently load the selected environment target's PipelineRun logs with request-generation protection.

**Tech Stack:** Vue 3, TypeScript, Vue Router, Element Plus, Vitest, existing Flask release-batch and Pipeline log APIs.

## Global Constraints

- Business state comes from MySQL release batches and targets; execution steps and logs come from Tekton.
- Preserve Project/Application scoping through existing APIs.
- Do not modify Build once/Promote, approval, deployment, or Tekton Pipeline behavior.
- Do not invent steps for targets without a PipelineRun.
- Production approval remains in the existing approval workflow.
- Frontend HTTP calls stay in `frontend/src/api`.

---

### Task 1: Generic Actual-Step State Model

**Files:**
- Modify: `frontend/src/features/build-explorer/state.ts`
- Modify: `frontend/src/features/build-explorer/state.test.ts`

**Interfaces:**
- Produces: `ExecutionStepDetail { id, taskName, name, label, status, startedAt?, finishedAt?, logs }`.
- Produces: `normalizeExecutionSteps(details: PipelineLogDetails) -> ExecutionStepDetail[]` preserving task and step order.
- Produces: `defaultExecutionStepId(steps)` selecting failed, then active, then first.
- Produces: `batchForBuild(batches, buildId)` and `hasActiveDelivery(build, batch)`.

Core failing assertions:

```ts
expect(normalizeExecutionSteps(javaLogs).map(step => step.name))
  .toEqual(['git-clone', 'maven', 'kaniko'])
expect(normalizeExecutionSteps(nodeLogs).map(step => step.name))
  .toEqual(['git-clone', 'npm', 'kaniko'])
expect(defaultExecutionStepId([
  executionStep('clone', 'Succeeded'),
  executionStep('deploy', 'Running'),
])).toBe('deploy')
expect(batchForBuild([batch(41), batch(42)], 42)?.build_version_id).toBe(42)
expect(hasActiveDelivery(build(42, 'Succeeded'), batchWithTarget('Deploying'))).toBe(true)
```

- [ ] Write failing tests proving Java, Node and Dockerfile logs retain their real step names and order, including `git-clone`, `maven`, `npm`, and `kaniko`.
- [ ] Write failing tests proving default selection priority is Failed, then Running/Pending, then first.
- [ ] Write failing tests proving the matching release batch is selected by `build_version_id` and active targets keep polling after the build succeeds.
- [ ] Run `npm --prefix frontend test -- src/features/build-explorer/state.test.ts` and confirm failures are caused by missing generic helpers.
- [ ] Implement the minimal pure TypeScript helpers; remove fixed-step normalization only after tests are red.
- [ ] Run frontend tests and `vue-tsc -b`; expect all pass.
- [ ] Commit with `feat: model actual delivery execution steps`.

---

### Task 2: Reusable Step Log and Environment Target Components

**Files:**
- Create: `frontend/src/components/pipeline/PipelineStepLogPanel.vue`
- Create: `frontend/src/components/pipeline/BuildDeliveryTargets.vue`
- Modify: `frontend/src/components/pipeline/ApplicationBuildDetail.vue`

**Interfaces:**
- `PipelineStepLogPanel` consumes real `ExecutionStepDetail[]`, selected ID, loading and error; emits step selection and retry.
- `BuildDeliveryTargets` consumes a `ReleaseBatch`, selected target ID and target-log state; emits target selection, step selection and retry.
- `ApplicationBuildDetail` composes build metadata, actual Build Pipeline steps, and the environment release section.

Target presentation contract:

```ts
expect(targetExecutionState(target({ status: 'WaitingApproval' }))).toEqual({
  canLoadLogs: false,
  description: '等待审批',
})
expect(targetExecutionState(target({ status: 'Deploying', pipeline_run_name: 'deploy-1' })).canLoadLogs)
  .toBe(true)
```

- [ ] Add failing pure presentation-state tests for target descriptions: WaitingApproval, missing PipelineRun, active, succeeded and failed.
- [ ] Run the focused Vitest suite and confirm RED.
- [ ] Implement a generic step/log component using real labels such as `clone / git-clone` and `package / maven`.
- [ ] Implement environment cards showing independent target status, environment name, approval state and PipelineRun availability.
- [ ] Refactor `ApplicationBuildDetail` to use the generic component for Build Pipeline and embed the environment component below it.
- [ ] Run frontend tests, type check and production build; expect all pass.
- [ ] Commit with `feat: show build and environment execution sections`.

---

### Task 3: Release-Batch and Deploy Log Data Flow

**Files:**
- Modify: `frontend/src/views/ApplicationBuildExplorer.vue`
- Modify: `frontend/src/features/build-explorer/state.ts`
- Modify: `frontend/src/features/build-explorer/state.test.ts`

**Interfaces:**
- Context load adds `applicationApi.releaseBatches(projectId, applicationId)`.
- Selected build resolves its batch by `build_version_id`.
- Selected target with `pipeline_run_name` loads `pipelineApi.logs` and normalizes actual steps.
- A dedicated target request gate prevents old environment responses from overwriting the current target.

Default target contract:

```ts
expect(defaultTargetId([
  target({ id: 1, status: 'Succeeded' }),
  target({ id: 2, status: 'Failed' }),
])).toBe(2)

const gate = createRequestGate()
const qaRequest = gate.next()
const prodRequest = gate.next()
expect(gate.isCurrent(qaRequest)).toBe(false)
expect(gate.isCurrent(prodRequest)).toBe(true)
```

- [ ] Add failing tests for default target selection: failed target, then active target, then first target with PipelineRun, then first target.
- [ ] Add a failing request-gate regression test showing an old target-log generation is rejected after environment selection changes.
- [ ] Run Vitest and confirm RED.
- [ ] Load release batches in the context request and update them during polling.
- [ ] On build change, reset target state, select the matching batch and default target, then load deploy logs only when a PipelineRun exists.
- [ ] Poll while the build or any target is active; stop only when all are terminal.
- [ ] Run frontend tests, type check and production build; expect all pass.
- [ ] Commit with `feat: load per-environment deployment logs`.

---

### Task 4: Verification, Documentation, and Completion

**Files:**
- Modify: `docs/current-state.md`
- Modify then move: `specs/active/build-delivery-execution-details.md` to `specs/completed/build-delivery-execution-details.md`

- [ ] Review the page against the accepted design: actual build steps, all environment targets, truthful pre-Pipeline states, Deploy-only steps/logs, and independent failures.
- [ ] Run `./scripts/verify.sh`; expect backend tests, frontend tests, type check and production build to pass.
- [ ] Request an independent code review focused on stale responses, incorrect batch/build association, approval state, and polling termination; fix all Critical/Important findings.
- [ ] Update `docs/current-state.md`, record exact verification evidence, mark every supported acceptance condition, and archive the active spec.
- [ ] Commit with `docs: complete delivery execution details`.
