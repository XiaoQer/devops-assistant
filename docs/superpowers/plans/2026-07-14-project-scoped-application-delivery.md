# Project-Scoped Application Delivery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Application delivery strictly Project-scoped and deploy each Environment through the Kubernetes cluster and Registry configured by its Project.

**Architecture:** A new `DeliveryContextService` resolves and validates the Project, Application, Environment, target cluster, Namespace, and default Registry. Central Tekton continues to build and deploy in phase one, with a persistent per-Project-cluster kubeconfig Secret mounted only by the deploy Task; target-cluster clients handle application configuration, runtime inspection, and rollback.

**Tech Stack:** Python 3, Flask, SQLAlchemy, Alembic, Kubernetes Python client, Tekton v1, MySQL/SQLite tests, Vue 3, TypeScript, Pinia, Vue Router, Element Plus.

## Global Constraints

- Project is the mandatory governance and workspace boundary for every Application resource.
- All API responses retain `success`, `message`, `data`, `timestamp`, and `trace_id`.
- HTTP handlers perform transport validation; business behavior remains in Services.
- Kubernetes operations stay in `KubernetesService`; Tekton operations stay in `TektonService`.
- Frontend HTTP calls stay in `frontend/src/api`.
- kubeconfig, Registry Token, application Secret values, and decrypted credentials must never appear in API payloads, logs, Pipeline parameters, Release records, or displayed test output.
- Cluster and Registry must be active and have `connection_status == "connected"` before deployment.
- ProjectMember RBAC, GitHub boundary enforcement, new build templates, Application AI, and Delivery Reconciler are excluded.
- Every behavior change follows TDD and the final verification is `./scripts/verify.sh`.

---

### Task 1: Persist Project and Delivery Target Snapshots

**Files:**
- Create: `backend/migrations/versions/f6a7b8c9d0e1_scope_application_delivery.py`
- Create: `backend/tests/test_application_delivery_migration.py`
- Modify: `backend/app/models/application.py`
- Modify: `backend/app/models/pipeline_execution.py`
- Modify: `backend/app/models/release_record.py`
- Modify: `backend/app/models/approval_record.py`

**Interfaces:**
- Produces: non-null `Application.project_id`, `PipelineExecution.project_id`, `ReleaseRecord.project_id`, and `ApprovalRecord.project_id`.
- Produces: nullable target snapshots `environment`, `kubernetes_cluster_id`, and `deploy_namespace` where applicable.
- Consumes: system Project key `default` for deterministic legacy backfill only.

- [ ] **Step 1: Write the failing migration test**

Create a pre-migration SQLite schema with a Default Project, one Project-less Application, and associated execution, release, and approval rows. Upgrade from `e5f6a7b8c9d0` to `f6a7b8c9d0e1` and assert:

```python
application = connection.execute(text(
    "SELECT project_id FROM applications WHERE id = 10"
)).mappings().one()
execution = connection.execute(text(
    "SELECT project_id, environment, kubernetes_cluster_id, deploy_namespace "
    "FROM pipeline_executions WHERE id = 20"
)).mappings().one()
assert application["project_id"] == 1
assert execution["project_id"] == 1
assert execution["environment"] == "dev"
assert execution["deploy_namespace"] == "default"
```

Downgrade to `e5f6a7b8c9d0` and assert the new snapshot columns are absent while original rows remain.

- [ ] **Step 2: Run the migration test and verify failure**

Run: `cd backend && .venv/bin/python -m pytest tests/test_application_delivery_migration.py -q`

Expected: FAIL because revision `f6a7b8c9d0e1` and new columns do not exist.

- [ ] **Step 3: Add model fields and migration**

Use batch alterations compatible with SQLite and MySQL. Backfill Project IDs through `applications.project_id`, and backfill missing Application Project IDs from the Project whose key is `default` before applying non-null constraints. Add these model fields:

```python
# PipelineExecution
project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)
environment = db.Column(db.String(30), nullable=False, default="dev", index=True)
kubernetes_cluster_id = db.Column(db.Integer, db.ForeignKey("kubernetes_clusters.id"), nullable=True)
deploy_namespace = db.Column(db.String(120), nullable=False, default="default")

# ReleaseRecord and ApprovalRecord
kubernetes_cluster_id = db.Column(db.Integer, db.ForeignKey("kubernetes_clusters.id"), nullable=True)
```

Update serializers to expose IDs and target metadata but no credentials.

- [ ] **Step 4: Run migration and model tests**

Run: `cd backend && .venv/bin/python -m pytest tests/test_application_delivery_migration.py tests/test_application_service.py tests/test_approval_service.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the data model slice**

```bash
git add backend/app/models backend/migrations/versions/f6a7b8c9d0e1_scope_application_delivery.py backend/tests/test_application_delivery_migration.py
git commit -m "feat: persist application delivery targets"
```

### Task 2: Introduce Strict Project-Scoped Resource Lookups and Routes

**Files:**
- Create: `backend/tests/test_project_application_routes.py`
- Modify: `backend/app/routes/applications.py`
- Modify: `backend/app/routes/environments.py`
- Modify: `backend/app/routes/pipelines.py`
- Modify: `backend/app/routes/releases.py`
- Modify: `backend/app/routes/approvals.py`
- Modify: `backend/app/routes/__init__.py`
- Modify: `backend/app/__init__.py`
- Modify: `backend/app/services/application_service.py`
- Modify: `backend/tests/test_auth_routes.py`
- Modify: `backend/tests/test_validation_routes.py`
- Modify: `backend/tests/test_deployment_plan_service.py`

**Interfaces:**
- Produces: `ApplicationService.get(project_id: int, application_id: int) -> Application`.
- Produces: Project-scoped API prefixes under `/api/projects/<int:project_id>`.
- Consumes: `ProjectService.get(project_id)` and existing response/validation helpers.

- [ ] **Step 1: Write cross-Project route tests**

Create Project A and B, an Application and child resources in A, authenticate, then verify each B path returns `404` with the expected resource-not-found code:

```python
paths = [
    f"/api/projects/{project_b.id}/applications/{app.id}",
    f"/api/projects/{project_b.id}/applications/{app.id}/environments",
    f"/api/projects/{project_b.id}/applications/{app.id}/executions",
    f"/api/projects/{project_b.id}/applications/{app.id}/releases",
]
for path in paths:
    response = client.get(path)
    assert response.status_code == 404
```

Also assert `/api/applications`, `/api/pipelines`, `/api/releases`, and `/api/approvals` return 404 after migration, and creation without a Project path cannot fall back to Default Project.

- [ ] **Step 2: Run route tests and verify failure**

Run: `cd backend && .venv/bin/python -m pytest tests/test_project_application_routes.py -q`

Expected: FAIL because nested routes do not exist and global routes still respond.

- [ ] **Step 3: Scope Application and child-resource lookups**

Make every helper include the parent Project:

```python
def get_application(project_id, application_id):
    app = Application.query.filter_by(
        id=application_id,
        project_id=project_id,
    ).first()
    if not app:
        raise ApiError("应用不存在", 404, "APPLICATION_NOT_FOUND")
    return app
```

Use equivalent compound filters for Environment, Config, Execution, Release, and Approval. Pipeline status/log/retry must first query `PipelineExecution` by `project_id` and `pipeline_run_name` before calling Tekton.

- [ ] **Step 4: Require Project in Application creation**

Remove `ensure_default_project()` from `ApplicationService.create`. Change the signature to:

```python
def create(self, project, payload):
    existing = Application.query.filter_by(
        project_id=project.id,
        name=payload["name"],
    ).first()
```

Routes resolve the Project from the path and pass it to the Service.

- [ ] **Step 5: Register only Project-scoped blueprints**

Set route prefixes so supported paths match the design. Remove registrations that expose global Application delivery resources. Keep `/api/projects` governance routes unchanged.

- [ ] **Step 6: Update existing route tests and run them**

Run: `cd backend && .venv/bin/python -m pytest tests/test_project_application_routes.py tests/test_auth_routes.py tests/test_validation_routes.py tests/test_deployment_plan_service.py -q`

Expected: PASS with nested paths and uniform response envelopes.

- [ ] **Step 7: Commit Project API isolation**

```bash
git add backend/app/routes backend/app/services/application_service.py backend/app/__init__.py backend/tests
git commit -m "feat: scope application APIs to projects"
```

### Task 3: Resolve and Validate a Delivery Context

**Files:**
- Create: `backend/app/services/delivery_context_service.py`
- Create: `backend/tests/test_delivery_context_service.py`
- Modify: `backend/app/services/deployment_plan_service.py`
- Modify: `backend/app/services/registry_service.py`
- Modify: `backend/app/services/environment_service.py`

**Interfaces:**
- Produces: frozen `DeliveryContext(project, application, environment, cluster, registry, namespace, image_name, kube_context)` dataclass.
- Produces: `DeliveryContextService.resolve(project, application, environment_name) -> DeliveryContext`.
- Produces: stable errors `ENVIRONMENT_NOT_FOUND`, `CLUSTER_REQUIRED`, `CLUSTER_NOT_READY`, `REGISTRY_REQUIRED`, and `REGISTRY_NOT_READY`.
- Consumes: only Project-scoped active Cluster and Registry records; no platform Registry fallback.

- [ ] **Step 1: Write readiness matrix tests**

Cover missing Environment, unbound Cluster, cross-Project Cluster, inactive Cluster, `untested`/`failed` Cluster, missing Registry, inactive Registry, `untested`/`failed` Registry, and a connected success case:

```python
context = service.resolve(project, application, "prod")
assert context.cluster.id == cluster.id
assert context.registry.id == registry.id
assert context.namespace == "payments-prod"
assert context.image_name == "ghcr.io/acme/payments-api"
```

- [ ] **Step 2: Run context tests and verify failure**

Run: `cd backend && .venv/bin/python -m pytest tests/test_delivery_context_service.py -q`

Expected: FAIL because the Service and dataclass do not exist.

- [ ] **Step 3: Implement minimal context resolution**

Implement exact ownership and readiness checks. Do not call `RegistryService.get_default()` because that method retains legacy fallback behavior; add and use:

```python
def get_project_default(self, project_id):
    return ContainerRegistry.query.filter_by(
        project_id=project_id,
        is_default=True,
        is_active=True,
    ).first()
```

- [ ] **Step 4: Make Deployment Plan consume the context**

Convert context failures into blocked checks instead of warnings. Extend `target` with safe metadata:

```python
"cluster": {
    "id": cluster.id,
    "name": cluster.name,
    "connection_status": cluster.connection_status,
},
"registry": {
    "id": registry.id,
    "name": registry.name,
    "image_prefix": registry.image_prefix,
    "connection_status": registry.connection_status,
},
```

- [ ] **Step 5: Run context and plan tests**

Run: `cd backend && .venv/bin/python -m pytest tests/test_delivery_context_service.py tests/test_deployment_plan_service.py -q`

Expected: PASS, including strict blocking for unready resources.

- [ ] **Step 6: Commit delivery readiness**

```bash
git add backend/app/services backend/tests/test_delivery_context_service.py backend/tests/test_deployment_plan_service.py
git commit -m "feat: validate application delivery context"
```

### Task 4: Build Complete Target Kubernetes Clients and Runtime Operations

**Files:**
- Create: `backend/app/services/application_runtime_service.py`
- Create: `backend/tests/test_application_runtime_service.py`
- Modify: `backend/app/services/kubernetes_service.py`
- Modify: `backend/app/services/kubernetes_cluster_service.py`
- Modify: `backend/app/services/release_service.py`
- Modify: `backend/app/routes/applications.py`
- Modify: `backend/tests/test_kubernetes_cluster_service.py`

**Interfaces:**
- Produces: `KubernetesClusterService.client(cluster) -> KubernetesService`.
- Produces: `ApplicationRuntimeService.status(context)`, `pod_logs(context, pod_name, container, tail)`, `pod_manifest(context, pod_name)`, and `rollback(context, image)`.
- Consumes: validated `DeliveryContext`; runtime methods never instantiate default `KubernetesService()`.

- [ ] **Step 1: Extend the isolated-client failing test**

Assert `KubernetesService.from_kubeconfig` initializes every required API:

```python
service = KubernetesService.from_kubeconfig(document, "dev")
assert service.core_api is core_api.return_value
assert service.apps_api is apps_api.return_value
assert service.networking_api is networking_api.return_value
assert service.custom_api is custom_api.return_value
```

Add runtime tests with two fake target clients and prove Environment A never calls Environment B's client.

- [ ] **Step 2: Run target-client tests and verify failure**

Run: `cd backend && .venv/bin/python -m pytest tests/test_kubernetes_cluster_service.py tests/test_application_runtime_service.py -q`

Expected: FAIL because the isolated client has only Version API and Runtime Service is absent.

- [ ] **Step 3: Complete `from_kubeconfig` and add cluster client factory**

Initialize `CoreV1Api`, `AppsV1Api`, `NetworkingV1Api`, `CustomObjectsApi`, and `VersionApi` from one isolated `ApiClient`. Parse the decrypted YAML through `yaml.safe_load` before passing it to `from_kubeconfig`.

- [ ] **Step 4: Move runtime and rollback behavior into the Service**

Routes resolve scoped models and context, then delegate. `ReleaseService.rollback` creates the audit record only after the target operation succeeds and snapshots the target Cluster ID and Namespace.

- [ ] **Step 5: Run Kubernetes and runtime tests**

Run: `cd backend && .venv/bin/python -m pytest tests/test_kubernetes_cluster_service.py tests/test_application_runtime_service.py tests/test_application_service.py -q`

Expected: PASS; mocks prove no default client is constructed.

- [ ] **Step 6: Commit target runtime clients**

```bash
git add backend/app/services backend/app/routes/applications.py backend/tests
git commit -m "feat: use environment clusters for application runtime"
```

### Task 5: Materialize Target and Central Credentials Separately

**Files:**
- Create: `backend/app/services/cluster_credential_materializer.py`
- Create: `backend/tests/test_cluster_credential_materializer.py`
- Modify: `backend/app/services/configuration_service.py`
- Modify: `backend/app/services/kubernetes_service.py`
- Modify: `backend/app/services/kubernetes_cluster_service.py`
- Modify: `backend/app/routes/projects.py`
- Modify: `backend/tests/test_application_service.py`
- Modify: `backend/tests/test_kubernetes_cluster_service.py`
- Modify: `backend/tests/test_project_routes.py`

**Interfaces:**
- Produces: `ClusterCredentialMaterializer.materialize(project, cluster, central_kubernetes) -> str` returning only the deterministic Secret name.
- Produces: `ClusterCredentialMaterializer.delete(project, cluster, central_kubernetes) -> None` for cluster deletion cleanup.
- Produces: `ConfigurationService.materialize(app, environment, target_kubernetes, registry) -> dict` for target resources only.
- Produces: `ConfigurationService.materialize_build_registry(registry, central_kubernetes, tekton_namespace) -> str`.
- Consumes: `KubernetesClusterService.credentials(cluster)` internally; decrypted kubeconfig never leaves the materializer call chain.

- [ ] **Step 1: Write Secret safety and client-separation tests**

Assert deterministic naming, Aegis labels, create-or-patch behavior, and safe return value:

```python
name = materializer.materialize(project, cluster, central)
assert name == f"aegis-kubeconfig-p{project.id}-c{cluster.id}"
central.apply_secret.assert_called_once()
assert "token:" not in name
```

Assert application ConfigMap, Secret, and pull Secret calls go only to the target client, while Kaniko credentials go only to the central client.
Assert a cluster bound to an Environment cannot be deleted, while deletion of an unbound cluster removes
its deterministic central Secret without serializing kubeconfig.

- [ ] **Step 2: Run materialization tests and verify failure**

Run: `cd backend && .venv/bin/python -m pytest tests/test_cluster_credential_materializer.py tests/test_application_service.py -q`

Expected: FAIL because central and target materialization are still combined.

- [ ] **Step 3: Implement the credential materializer**

Store kubeconfig under the key `config`, label the Secret with Project and Cluster IDs, and call the Kubernetes adapter rather than raw client APIs from the business service:

```python
central_kubernetes.apply_secret(
    secret_name,
    current_app.config["TEKTON_NAMESPACE"],
    {"config": kubeconfig},
    labels={
        "app.kubernetes.io/managed-by": "aegis",
        "aegis.dev/project-id": str(project.id),
        "aegis.dev/cluster-id": str(cluster.id),
    },
)
```

Extend `KubernetesService.apply_secret` with an optional labels argument while preserving existing labels.

Implement `delete` with `KubernetesService.delete_secret(name, namespace)`, treating a missing Secret as
successful cleanup. The Project cluster deletion route performs referential validation first, removes the
central Secret, and only then commits database deletion; a central Kubernetes failure returns a sanitized
error and leaves the cluster record intact for retry.

- [ ] **Step 4: Split target and central Registry materialization**

Remove the loop that writes Environment and Tekton namespaces through one client. Target and central calls must be explicit at the orchestration layer.

- [ ] **Step 5: Run materialization and secret-leak tests**

Run: `cd backend && .venv/bin/python -m pytest tests/test_cluster_credential_materializer.py tests/test_application_service.py tests/test_registry_service.py tests/test_kubernetes_cluster_service.py -q`

Expected: PASS; failure output and serialized objects contain no fixture credentials.

- [ ] **Step 6: Commit credential separation**

```bash
git add backend/app/services backend/tests
git commit -m "feat: materialize scoped delivery credentials"
```

### Task 6: Mount Target kubeconfig Only in the Tekton Deploy Task

**Files:**
- Modify: `backend/app/services/tekton_service.py`
- Modify: `backend/tests/test_tekton_service.py`
- Modify: `deploy/tekton/pipelines/java-maven-kaniko-deploy.yaml`
- Modify: `deploy/tekton/pipelines/node-npm-kaniko-deploy.yaml`
- Modify: `deploy/tekton/pipelines/dockerfile-kaniko-deploy.yaml`

**Interfaces:**
- Produces: `TektonService.create_pipeline_run(..., kubeconfig_secret_name: str, kube_context: str, ...)`.
- Consumes: Secret name and context only; kubeconfig content is forbidden.

- [ ] **Step 1: Write PipelineRun and YAML structure tests**

Extend the generated-body test:

```python
params = {item["name"]: item["value"] for item in body["spec"]["params"]}
assert params["kubeconfig_secret_name"] == "aegis-kubeconfig-p1-c2"
assert params["kube_context"] == "prod"
assert "token" not in str(body).lower()
```

Parameterize all three YAML files and assert only `tasks[name=deploy]` contains a volumeMount named `target-kubeconfig`; clone and build Tasks must not contain it.

- [ ] **Step 2: Run Tekton tests and verify failure**

Run: `cd backend && .venv/bin/python -m pytest tests/test_tekton_service.py -q`

Expected: FAIL because target parameters and mounts are absent.

- [ ] **Step 3: Add safe PipelineRun parameters**

Add only these values to `spec.params`:

```python
{"name": "kubeconfig_secret_name", "value": kubeconfig_secret_name},
{"name": "kube_context", "value": kube_context},
```

The central PipelineRun remains in `TEKTON_NAMESPACE`.

- [ ] **Step 4: Update all three Pipeline templates**

Add Pipeline params and mount only inside the deploy Task:

```yaml
taskSpec:
  params:
    - {name: kubeconfig_secret_name}
    - {name: kube_context}
  volumes:
    - name: target-kubeconfig
      secret:
        secretName: $(params.kubeconfig_secret_name)
  steps:
    - name: kubectl
      image: docker.io/alpine/k8s:1.31.0
      volumeMounts:
        - name: target-kubeconfig
          mountPath: /var/run/aegis/kubeconfig
          readOnly: true
params:
  - {name: kubeconfig_secret_name, value: $(params.kubeconfig_secret_name)}
  - {name: kube_context, value: $(params.kube_context)}
```

The deploy Task's mount is exactly:

```yaml
volumeMounts:
  - name: target-kubeconfig
    mountPath: /var/run/aegis/kubeconfig
    readOnly: true
```

Every deploy command uses:

```sh
kubectl --kubeconfig=/var/run/aegis/kubeconfig/config --context="$(params.kube_context)" -n "$(params.namespace)"
```

Reference the Secret by parameter without placing Secret content in the PipelineRun.

- [ ] **Step 5: Run Tekton tests**

Run: `cd backend && .venv/bin/python -m pytest tests/test_tekton_service.py -q`

Expected: PASS for all three templates and generated PipelineRun structure.

- [ ] **Step 6: Commit cross-cluster Tekton deployment**

```bash
git add backend/app/services/tekton_service.py backend/tests/test_tekton_service.py deploy/tekton/pipelines
git commit -m "feat: deploy tekton runs to environment clusters"
```

### Task 7: Orchestrate Deployment, Approval Revalidation, and Scoped History

**Files:**
- Modify: `backend/app/services/application_service.py`
- Modify: `backend/app/services/approval_service.py`
- Modify: `backend/app/services/release_service.py`
- Modify: `backend/app/routes/applications.py`
- Modify: `backend/app/routes/approvals.py`
- Modify: `backend/app/routes/releases.py`
- Modify: `backend/app/routes/pipelines.py`
- Modify: `backend/tests/test_application_service.py`
- Modify: `backend/tests/test_approval_service.py`
- Modify: `backend/tests/test_project_application_routes.py`

**Interfaces:**
- Consumes: `DeliveryContextService.resolve`, target/central materializers, and safe Tekton parameters.
- Produces: Project- and target-snapshotted `PipelineExecution`, `ReleaseRecord`, and `ApprovalRecord`.
- Produces: approval that re-resolves the current Delivery Context before external writes.

- [ ] **Step 1: Write orchestration order tests**

Use mocks to assert this order and failure boundary:

```python
assert calls == [
    "resolve_context",
    "materialize_target_config",
    "materialize_central_registry",
    "materialize_cluster_kubeconfig",
    "create_pipeline_run",
]
assert PipelineExecution.query.count() == 1
assert ReleaseRecord.query.count() == 1
```

For each failing external step, assert later calls do not happen and no pending execution/release is persisted.

- [ ] **Step 2: Write approval revalidation tests**

Create a pending approval, change its Registry or Cluster to `failed`, then approve. Assert `REGISTRY_NOT_READY` or `CLUSTER_NOT_READY`, no PipelineRun, and Approval remains `Pending`.

- [ ] **Step 3: Run orchestration tests and verify failure**

Run: `cd backend && .venv/bin/python -m pytest tests/test_application_service.py tests/test_approval_service.py tests/test_project_application_routes.py -q`

Expected: FAIL because deployment does not use the confirmed context and approval does not revalidate readiness.

- [ ] **Step 4: Refactor deployment orchestration**

Pass Project and explicit Environment through the call chain. Set snapshot fields from the resolved context. Commit the database transaction only after PipelineRun creation returns a name. Roll back the SQLAlchemy session on an external failure before returning a sanitized API error.

- [ ] **Step 5: Scope Pipeline, Release, and Approval collections**

Query database rows by `project_id`; do not list arbitrary central PipelineRuns as the Project source of truth. Status/log/retry use the stored execution's PipelineRun name and the fixed central Tekton Namespace.

- [ ] **Step 6: Run backend delivery tests**

Run: `cd backend && .venv/bin/python -m pytest tests/test_application_service.py tests/test_approval_service.py tests/test_deployment_plan_service.py tests/test_project_application_routes.py tests/test_tekton_service.py -q`

Expected: PASS.

- [ ] **Step 7: Commit the complete backend delivery flow**

```bash
git add backend/app backend/tests
git commit -m "feat: orchestrate project scoped application delivery"
```

### Task 8: Keep the Frontend Inside the Active Project Workspace

**Files:**
- Modify: `frontend/src/api/application.ts`
- Modify: `frontend/src/api/pipeline.ts`
- Modify: `frontend/src/api/release.ts`
- Modify: `frontend/src/api/approval.ts`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/stores/application.ts`
- Modify: `frontend/src/views/ApplicationCreate.vue`
- Modify: `frontend/src/views/ApplicationList.vue`
- Modify: `frontend/src/views/ApplicationDetail.vue`
- Modify: `frontend/src/views/PipelineRuns.vue`
- Modify: `frontend/src/views/PipelineDetail.vue`
- Modify: `frontend/src/views/ReleaseCenter.vue`
- Modify: `frontend/src/views/Approvals.vue`
- Modify: `frontend/src/components/application/EnvironmentCenter.vue`
- Modify: `frontend/src/types.ts`

**Interfaces:**
- Produces: API functions whose first argument is `projectId: number`.
- Consumes: Project route param `projectId` for every delivery page and link.
- Consumes: backend Deployment Plan target Cluster and Registry summaries.

- [ ] **Step 1: Change API signatures first and run type checking**

Use explicit Project paths, for example:

```typescript
get: (projectId: number, applicationId: number) =>
  client.get<never, Application>(`/projects/${projectId}/applications/${applicationId}`),
deployPlan: (projectId: number, applicationId: number, options: DeployOptions) =>
  client.post<never, DeploymentPlan>(
    `/projects/${projectId}/applications/${applicationId}/deploy/plan`,
    options,
  ),
```

Run: `npm --prefix frontend run build`

Expected: FAIL with call-site type errors, proving every global call site is identified.

- [ ] **Step 2: Lock Application creation to the route Project**

Read `Number(route.params.projectId)`, fetch that Project for display, remove the Project selector, and submit to the nested API. After creation navigate to:

```typescript
router.push(`/devcenter/projects/${projectId}/applications/${result.id}`)
```

- [ ] **Step 3: Preserve Project context in all delivery views**

Update links for Application, Pipeline, Release, Approval, Runtime, logs, and retry to stay under `/devcenter/projects/${projectId}`. Remove global delivery routes from the router.

- [ ] **Step 4: Display readiness details**

Environment cards show Cluster name and `connection_status`. Deployment Plan shows target Cluster, Namespace, Registry, and backend-provided blocking checks. The deploy confirmation stays disabled when `can_deploy` is false.

- [ ] **Step 5: Run the frontend production build**

Run: `npm --prefix frontend run build`

Expected: PASS with `vue-tsc -b` and Vite production output.

- [ ] **Step 6: Commit the Project-scoped frontend**

```bash
git add frontend/src
git commit -m "feat: keep application delivery in project workspace"
```

### Task 9: Complete Regression Verification and Project Memory

**Files:**
- Modify: `docs/current-state.md`
- Modify: `specs/active/project-scoped-application-delivery.md`
- Move after acceptance: `specs/active/project-scoped-application-delivery.md` to `specs/completed/project-scoped-application-delivery.md`
- Modify as required by verified regressions: files already listed in Tasks 1-8 only.

**Interfaces:**
- Consumes: all completed tasks and acceptance conditions.
- Produces: verified current-state documentation and completed specification.

- [ ] **Step 1: Run the complete backend suite**

Run: `cd backend && .venv/bin/python -m pytest tests -q`

Expected: all tests PASS without an online Kubernetes cluster, Tekton installation, or Registry.

- [ ] **Step 2: Run the frontend production build**

Run: `npm --prefix frontend run build`

Expected: PASS.

- [ ] **Step 3: Run repository verification**

Run: `./scripts/verify.sh`

Expected: `Verification passed`.

- [ ] **Step 4: Inspect secret-safety and global-route regressions**

Run:

```bash
rg -n "encrypted_kubeconfig|encrypted_password" backend/app/routes frontend/src
rg -n "'/applications|\"/applications|'/pipelines|\"/pipelines|'/releases|\"/releases|'/approvals|\"/approvals" frontend/src
```

Expected: no credential serialization and no active global delivery API/navigation paths.

- [ ] **Step 5: Update project memory and acceptance evidence**

Record verified behavior, exact test count, build result, migration evidence, deferred Delivery Reconciler, and deferred ProjectMember RBAC in `docs/current-state.md`. Fill the specification's verification evidence, mark every proven acceptance checkbox, set status to accepted, and move it to `specs/completed/` only after all checks pass.

- [ ] **Step 6: Commit verified documentation**

```bash
git add docs/current-state.md specs
git commit -m "docs: verify project scoped application delivery"
```

## Execution Order and Review Gates

Tasks must execute in order because later interfaces depend on earlier schema and service boundaries. After each task, review the focused diff and run its listed tests before proceeding. Do not combine Task 8 frontend migration with incomplete backend routes, and do not mark the active specification complete until Task 9 verification evidence exists.

The deferred Delivery Reconciler receives a separate future specification and plan. It must not be partially scaffolded in this implementation.
