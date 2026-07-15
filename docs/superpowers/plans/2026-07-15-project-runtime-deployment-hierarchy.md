# Project Runtime Deployment–Pod Hierarchy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the flat Deployment/Pod resource tabs with a paginated Deployment list whose rows lazily load managed Pods and link to the existing Pod detail page.

**Architecture:** The project inventory endpoint remains the single-environment Deployment summary source. A new Application-scoped endpoint resolves the delivery context and delegates ownership-checked Pod listing to `KubernetesService`; the frontend stores row-local loading/data/error state in a focused composable and renders a nested Pod table inside Element Plus expansion rows.

**Tech Stack:** Flask, Kubernetes Python client, pytest, Vue 3, TypeScript, Element Plus, Vitest.

## Global Constraints

- Project is the governance and workspace boundary; Application is the delivery aggregate.
- Kubernetes access stays in `KubernetesService`; HTTP handlers delegate business behavior to Services.
- Frontend requests stay in `frontend/src/api`, and all API responses retain the unified envelope.
- Runtime operations retain explicit confirmation, terminal reason, ticket, timeout, concurrency and audit controls.
- Do not expose environment values, Secrets or registry credentials.
- Preserve unrelated Portal work already present in the working tree.

---

### Task 1: Ownership-checked Deployment Pod summaries

**Files:**
- Modify: `backend/app/services/kubernetes_service.py`
- Modify: `backend/app/services/application_runtime_service.py`
- Test: `backend/tests/test_kubernetes_pod_detail.py`
- Test: `backend/tests/test_application_runtime_service.py`

**Interfaces:**
- Produces: `KubernetesService.list_application_deployment_pods(deployment_name, namespace, app_name) -> list[dict]`
- Produces: `ApplicationRuntimeService.deployment_pods(context, deployment_name) -> list[dict]`

- [ ] Write a failing Kubernetes Service test proving the method validates the Deployment name against the Application, lists `app=<application>` Pods, and returns name/status/ready/restart_count/node/containers/created_at.
- [ ] Run `.venv/bin/python -m pytest tests/test_kubernetes_pod_detail.py -q` from `backend`; expect failure because the method is missing.
- [ ] Implement the minimal ownership-checked summary method using `_read_application_pod` semantics and existing status normalization without serializing container environment data.
- [ ] Write and run a failing Application Runtime Service delegation test.
- [ ] Implement `deployment_pods()` using the target cluster and resolved Namespace.
- [ ] Run both focused test files and commit `feat: list deployment pods for runtime expansion`.

### Task 2: Lazy Deployment Pods HTTP endpoint

**Files:**
- Modify: `backend/app/routes/runtime.py`
- Test: `backend/tests/test_runtime_routes.py`

**Interfaces:**
- Consumes: `ApplicationRuntimeService.deployment_pods(context, deployment_name)`
- Produces: `GET /api/projects/:projectId/applications/:applicationId/environments/:environment/runtime/deployments/:deploymentName/pods`

- [ ] Write a failing route test asserting delivery-context resolution, the service call and unified response data.
- [ ] Run `.venv/bin/python -m pytest tests/test_runtime_routes.py -q`; expect 404 for the new path.
- [ ] Add the GET handler next to Deployment YAML/restart handlers and delegate to `ApplicationRuntimeService`.
- [ ] Run Runtime route and Service tests; expect all pass.
- [ ] Commit `feat: expose deployment pod expansion endpoint`.

### Task 3: Frontend row expansion state and API

**Files:**
- Modify: `frontend/src/api/runtime.ts`
- Modify: `frontend/src/api/runtime.test.ts`
- Create: `frontend/src/composables/useDeploymentPods.ts`
- Create: `frontend/src/composables/useDeploymentPods.test.ts`
- Modify: `frontend/src/types.ts`

**Interfaces:**
- Produces: `runtimeApi.deploymentPods(projectId, applicationId, environment, deployment)`
- Produces: `useDeploymentPods(loader)` with `load`, `retry`, `clear`, and keyed `entries` containing loading/data/error.

- [ ] Add a failing API test for the exact Application/Environment/Deployment Pods URL.
- [ ] Add failing composable tests proving first expansion loads, repeated expansion uses cache, failure is row-local, retry reloads, and clear invalidates all entries.
- [ ] Run focused Vitest files; expect missing API/composable failures.
- [ ] Add `RuntimePodSummary`, the API method and the minimal keyed cache composable.
- [ ] Run focused tests; expect all pass.
- [ ] Commit `feat: add lazy deployment pod state`.

### Task 4: Hierarchical Runtime table

**Files:**
- Modify: `frontend/src/components/runtime/RuntimeResourceTable.vue`
- Create: `frontend/src/components/runtime/DeploymentPodTable.vue`
- Modify: `frontend/src/views/ProjectRuntime.vue`
- Modify: `frontend/src/composables/useProjectRuntime.ts`
- Modify: `frontend/src/composables/useProjectRuntime.test.ts`

**Interfaces:**
- Consumes: `runtimeApi.deploymentPods` and `useDeploymentPods`.
- Produces: one Deployment-only table with row expansion and `pod-detail` events.

- [ ] Update failing composable tests to assert inventory always requests `resource: 'deployments'` and no longer reads/writes a resource query.
- [ ] Write a component/view-model test for Pod detail route construction and expansion cache invalidation.
- [ ] Run focused frontend tests and confirm failures represent the old flat tabs.
- [ ] Remove the Pods Tab and resource-dependent status controls from `ProjectRuntime.vue`.
- [ ] Convert `RuntimeResourceTable` to a Deployment-only table with an expand column; render `DeploymentPodTable` with loading, empty, error/retry and Pod link states.
- [ ] Clear expanded Pod cache when environment/filter/page/page-size changes and on manual refresh.
- [ ] Run all frontend tests and `npm run build`; expect pass.
- [ ] Commit `feat: nest pods under runtime deployments`.

### Task 5: Documentation and complete verification

**Files:**
- Modify: `specs/active/project-runtime-workspace-v2.md`
- Modify: `docs/current-state.md` (stage only the Runtime hunk)

**Interfaces:** None.

- [ ] Run `./scripts/verify.sh`; expect backend, frontend and build success.
- [ ] Mark hierarchy acceptance conditions with exact verification evidence; keep browser checks unchecked if authentication still blocks them.
- [ ] Update only the Runtime paragraph in `docs/current-state.md` to describe Deployment expansion rather than flat tabs.
- [ ] Run `git diff --check`, verify unrelated Portal changes remain unstaged, and commit `docs: record runtime hierarchy verification`.
