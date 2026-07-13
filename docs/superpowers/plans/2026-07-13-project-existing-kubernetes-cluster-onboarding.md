# Project Existing Kubernetes Cluster Onboarding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Let a Project securely register an existing Kubernetes cluster from a pasted kubeconfig, assign one environment label, and test Kubernetes API connectivity before or after saving, while showing Aliyun initialization as unavailable future functionality.

**Architecture:** Extend the existing `KubernetesCluster` child resource and keep credential handling in `KubernetesClusterService`. Build isolated Kubernetes clients from decrypted per-cluster kubeconfig in `KubernetesService`; expose transient and persisted test actions through the existing Project routes and API client. The Vue page keeps plaintext only in form memory and never receives stored kubeconfig back.

**Tech Stack:** Flask 3.1, Flask-SQLAlchemy, Alembic, PyYAML, cryptography/Fernet, Kubernetes Python client 33.1, pytest, Vue 3, TypeScript, Element Plus, js-yaml, Vite

## Global Constraints

- `Project` remains the governance boundary and `KubernetesCluster` remains its child resource.
- Persist kubeconfig only as Fernet ciphertext derived from Flask `SECRET_KEY`.
- Never serialize or log kubeconfig plaintext, ciphertext, Token, certificates, private keys, or raw upstream exception details.
- Accept exactly one environment label; offer `development`, `testing`, `staging`, `production`, and custom values.
- Reject kubeconfig larger than 1 MiB, non-HTTPS servers, `exec` authentication, and local credential/CA file references.
- Connectivity means Kubernetes Version API access only; Tekton and workload permissions are out of scope.
- Saving does not require a successful connectivity test.
- All HTTP responses retain `success`, `message`, `data`, `timestamp`, and `trace_id`.

---

### Task 1: Persist safe cluster onboarding metadata

**Files:**
- Create: `backend/migrations/versions/d4e5f6a7b8c9_add_kubernetes_cluster_onboarding.py`
- Create: `backend/tests/test_kubernetes_cluster_migration.py`
- Modify: `backend/app/models/kubernetes_cluster.py`
- Test: `backend/tests/test_kubernetes_cluster_migration.py`

**Interfaces:**
- Consumes: existing `KubernetesCluster` SQLAlchemy model and migration head `c3d4e5f6a7b8`.
- Produces: model attributes `environment_label`, `encrypted_kubeconfig`, `connection_status`, `last_checked_at`, `kubernetes_version`; safe `to_dict()` key `has_kubeconfig`.

- [x] **Step 1: Write the failing migration and serialization tests**

Create a migration test that builds the pre-change `kubernetes_clusters` table, inserts a row, stamps
`c3d4e5f6a7b8`, upgrades to `d4e5f6a7b8c9`, and asserts:

```python
expected = {
    "environment_label",
    "encrypted_kubeconfig",
    "connection_status",
    "last_checked_at",
    "kubernetes_version",
}
self.assertTrue(expected.issubset(columns))
row = connection.execute(sa.text(
    "SELECT name, environment_label, encrypted_kubeconfig, connection_status "
    "FROM kubernetes_clusters WHERE id = 1"
)).mappings().one()
self.assertEqual(row["name"], "legacy")
self.assertIsNone(row["environment_label"])
self.assertIsNone(row["encrypted_kubeconfig"])
self.assertEqual(row["connection_status"], "untested")
```

After downgrade, assert all five columns are absent. Add a model test which constructs a cluster with
`encrypted_kubeconfig="ciphertext"` and asserts `to_dict()` contains `has_kubeconfig is True` but
contains neither `encrypted_kubeconfig` nor `kubeconfig`.

- [x] **Step 2: Run the focused test and verify RED**

Run: `cd backend && .venv/bin/python -m pytest tests/test_kubernetes_cluster_migration.py -q`

Expected: FAIL because revision `d4e5f6a7b8c9` and the model fields do not exist.

- [x] **Step 3: Add the migration and model fields**

Add this upgrade shape, with matching downgrade drops in reverse order:

```python
revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"

def upgrade():
    with op.batch_alter_table("kubernetes_clusters") as batch_op:
        batch_op.add_column(sa.Column("environment_label", sa.String(80), nullable=True))
        batch_op.add_column(sa.Column("encrypted_kubeconfig", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column(
            "connection_status", sa.String(20), nullable=False,
            server_default="untested",
        ))
        batch_op.add_column(sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("kubernetes_version", sa.String(80), nullable=True))
```

Mirror the fields in the model and add safe serialization:

```python
"environment_label": self.environment_label,
"has_kubeconfig": bool(self.encrypted_kubeconfig),
"connection_status": self.connection_status,
"last_checked_at": self.last_checked_at.isoformat() if self.last_checked_at else None,
"kubernetes_version": self.kubernetes_version,
```

- [x] **Step 4: Run the focused test and verify GREEN**

Run: `cd backend && .venv/bin/python -m pytest tests/test_kubernetes_cluster_migration.py -q`

Expected: PASS.

- [x] **Step 5: Commit Task 1**

```bash
git add backend/app/models/kubernetes_cluster.py backend/migrations/versions/d4e5f6a7b8c9_add_kubernetes_cluster_onboarding.py backend/tests/test_kubernetes_cluster_migration.py
git commit -m "feat: persist kubernetes cluster onboarding metadata"
```

### Task 2: Validate, encrypt, and test kubeconfig safely

**Files:**
- Create: `backend/tests/test_kubernetes_cluster_service.py`
- Modify: `backend/app/services/kubernetes_cluster_service.py`
- Modify: `backend/app/services/kubernetes_service.py`
- Test: `backend/tests/test_kubernetes_cluster_service.py`

**Interfaces:**
- Produces: `KubernetesClusterService.inspect_kubeconfig(value, context) -> dict`, `credentials(cluster) -> tuple[str, str]`, `test_connection(kubeconfig, context) -> dict`, `test_saved_connection(cluster) -> dict`.
- Produces: `KubernetesService.from_kubeconfig(kubeconfig: dict, context: str) -> KubernetesService` and `version() -> dict[str, str]`.
- Returns connection results shaped as `{connected, message, api_server?, kubernetes_version?}`.

- [x] **Step 1: Write failing tests for validation and encryption**

Use a minimal embedded kubeconfig fixture:

```python
VALID_KUBECONFIG = """
apiVersion: v1
kind: Config
current-context: dev
clusters:
  - name: dev-cluster
    cluster:
      server: https://kubernetes.example.test
      certificate-authority-data: dGVzdA==
users:
  - name: dev-user
    user:
      token: test-token-not-a-real-secret
contexts:
  - name: dev
    context:
      cluster: dev-cluster
      user: dev-user
"""
```

Assert create encrypts the value, `credentials()` decrypts it, serialization omits both forms, blank
update preserves ciphertext, replacement changes ciphertext and resets status, and custom
`environment_label="performance"` is accepted. Add separate tests asserting `CLUSTER_KUBECONFIG_INVALID`
for oversized input, missing context, HTTP server, `exec`, `client-certificate`, `client-key`,
`tokenFile`, and `certificate-authority`.

- [x] **Step 2: Run the focused Service tests and verify RED**

Run: `cd backend && .venv/bin/python -m pytest tests/test_kubernetes_cluster_service.py -q`

Expected: FAIL because kubeconfig inspection, encryption, and test methods do not exist.

- [x] **Step 3: Implement parsing, validation, and Fernet handling**

Add constants and helpers to `KubernetesClusterService`:

```python
MAX_KUBECONFIG_BYTES = 1024 * 1024
CONNECTION_STATUSES = {"untested", "connected", "failed"}
FORBIDDEN_USER_KEYS = {"exec", "client-certificate", "client-key", "tokenFile"}

def _fernet(self):
    digest = hashlib.sha256(current_app.config["SECRET_KEY"].encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))

def inspect_kubeconfig(self, value, context):
    if not isinstance(value, str) or not value.strip() or len(value.encode()) > self.MAX_KUBECONFIG_BYTES:
        raise ApiError("kubeconfig 无效或超过 1 MiB", 400, "CLUSTER_KUBECONFIG_INVALID")
    document = yaml.safe_load(value)
    if not isinstance(document, dict):
        raise ApiError("kubeconfig 必须是对象", 400, "CLUSTER_KUBECONFIG_INVALID")
    contexts = {item.get("name"): item.get("context", {}) for item in document.get("contexts", [])}
    selected = contexts.get(context)
    if not selected:
        raise ApiError("所选 kube context 不存在", 400, "CLUSTER_CONTEXT_NOT_FOUND")
    clusters = {item.get("name"): item.get("cluster", {}) for item in document.get("clusters", [])}
    users = {item.get("name"): item.get("user", {}) for item in document.get("users", [])}
    cluster_config = clusters.get(selected.get("cluster"))
    user_config = users.get(selected.get("user"))
    if not isinstance(cluster_config, dict) or not isinstance(user_config, dict):
        raise ApiError("kube context 引用无效", 400, "CLUSTER_KUBECONFIG_INVALID")
    server = str(cluster_config.get("server", "")).strip()
    if urlparse(server).scheme != "https" or not urlparse(server).hostname:
        raise ApiError("Kubernetes API Server 必须使用 HTTPS", 400, "CLUSTER_SERVER_INVALID")
    if "certificate-authority" in cluster_config:
        raise ApiError("kubeconfig 不能引用本地 CA 文件", 400, "CLUSTER_KUBECONFIG_UNSAFE")
    if self.FORBIDDEN_USER_KEYS.intersection(user_config):
        raise ApiError("kubeconfig 不能执行命令或引用本地凭据文件", 400, "CLUSTER_KUBECONFIG_UNSAFE")
    return document
```

Catch YAML parser errors and convert them to the same safe `ApiError`. Add `_encrypt`, `_decrypt`, and
`credentials` following `RegistryService`; never include the submitted value in an exception. Update
`_validated()` so create requires non-blank `environment_label`, kubeconfig, and context; update keeps
existing ciphertext for blank/absent input; replacement resets test summary fields.

- [x] **Step 4: Write failing adapter and connection classification tests**

Patch `kubernetes.config.load_kube_config_from_dict` and `client.VersionApi.get_code`. Assert successful
version access returns:

```python
{
    "connected": True,
    "message": "Kubernetes API 连接成功",
    "api_server": "https://kubernetes.example.test",
    "kubernetes_version": "v1.31.2",
}
```

Parameterize `ApiException(status=401)`, `ssl.SSLCertVerificationError`, `TimeoutError`, and
`OSError`; assert each result is `connected: false`, uses a safe category message, and contains no raw
exception text or fixture token. Assert `test_saved_connection()` persists status/time/version/server
on success and only status/time on failure.

- [x] **Step 5: Run the adapter tests and verify RED**

Run: `cd backend && .venv/bin/python -m pytest tests/test_kubernetes_cluster_service.py -q`

Expected: FAIL because isolated client construction and version testing are absent.

- [x] **Step 6: Implement isolated Kubernetes version checks**

Add to `KubernetesService` without changing global kubeconfig state:

```python
@classmethod
def from_kubeconfig(cls, kubeconfig, context):
    instance = cls.__new__(cls)
    instance.mode = "cluster-kubeconfig"
    configuration = client.Configuration()
    config.load_kube_config_from_dict(
        kubeconfig,
        context=context,
        client_configuration=configuration,
        persist_config=False,
    )
    instance.api_client = client.ApiClient(configuration)
    instance.version_api = client.VersionApi(instance.api_client)
    return instance

def version(self):
    result = self.version_api.get_code(_request_timeout=5)
    return {"server": self.server, "version": result.git_version}
```

In `KubernetesClusterService.test_connection()`, validate first, call this adapter, and map expected
authentication/TLS/timeout/network exceptions to safe results. In `test_saved_connection()`, decrypt,
call `test_connection`, update only the approved summary fields, and commit.

- [x] **Step 7: Run focused and neighboring tests and verify GREEN**

Run: `cd backend && .venv/bin/python -m pytest tests/test_kubernetes_cluster_service.py tests/test_registry_service.py tests/test_application_service.py -q`

Expected: PASS.

- [x] **Step 8: Commit Task 2**

```bash
git add backend/app/services/kubernetes_cluster_service.py backend/app/services/kubernetes_service.py backend/tests/test_kubernetes_cluster_service.py
git commit -m "feat: securely test kubernetes cluster kubeconfig"
```

### Task 3: Expose transient and saved connectivity actions

**Files:**
- Modify: `backend/app/routes/projects.py`
- Modify: `backend/tests/test_project_routes.py`
- Modify: `backend/tests/test_validation_routes.py`
- Test: `backend/tests/test_project_routes.py`

**Interfaces:**
- Consumes: Task 2 `test_connection()` and `test_saved_connection()`.
- Produces: `POST /api/projects/<project_id>/clusters/test-connection` and `POST /api/projects/<project_id>/clusters/<cluster_id>/test-connection`.

- [x] **Step 1: Write failing route tests**

Patch Service test methods, submit through `csrf_post`, and assert the transient endpoint receives the
write-only `kubeconfig` plus `kube_context`, returns the standard envelope, and creates no row. Create a
cluster with encrypted config, retest it, and assert the persisted endpoint returns the result. Request
that cluster under `other_project_id` and assert 404 `CLUSTER_NOT_FOUND`. Assert missing fields and
non-object JSON return 400 without invoking a Kubernetes client.

- [x] **Step 2: Run route tests and verify RED**

Run: `cd backend && .venv/bin/python -m pytest tests/test_project_routes.py tests/test_validation_routes.py -q`

Expected: FAIL with 404 for the new endpoints.

- [x] **Step 3: Add the two route actions and extend create validation**

Implement before the integer-id cluster route to avoid ambiguous matching:

```python
@bp.post("/<int:project_id>/clusters/test-connection")
def test_cluster_connection(project_id):
    get_project(project_id)
    payload = json_object(request.get_json(silent=True), required=True)
    require_fields(payload, "kubeconfig", "kube_context")
    result = cluster_service.test_connection(payload["kubeconfig"], payload["kube_context"])
    return success(result, result["message"])

@bp.post("/<int:project_id>/clusters/<int:cluster_id>/test-connection")
def test_saved_cluster_connection(project_id, cluster_id):
    project = get_project(project_id)
    result = cluster_service.test_saved_connection(cluster_service.get(project, cluster_id))
    return success(result, result["message"])
```

Require `name`, `environment_label`, `kubeconfig`, and `kube_context` on create. Keep update validation
inside the Service so blank kubeconfig can preserve credentials.

- [x] **Step 4: Run route tests and verify GREEN**

Run: `cd backend && .venv/bin/python -m pytest tests/test_project_routes.py tests/test_validation_routes.py -q`

Expected: PASS.

- [x] **Step 5: Commit Task 3**

```bash
git add backend/app/routes/projects.py backend/tests/test_project_routes.py backend/tests/test_validation_routes.py
git commit -m "feat: add cluster connectivity test endpoints"
```

### Task 4: Build the two-path onboarding UI

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api/project.ts`
- Modify: `frontend/src/views/ProjectKubernetesSettings.vue`
- Verify: frontend TypeScript and production bundle

**Interfaces:**
- Consumes: Task 3 endpoints and safe cluster representation.
- Produces: `ClusterConnectionResult`, `ClusterPayload`, API methods `testClusterConnection` and `testSavedClusterConnection`.

- [x] **Step 1: Extend frontend types and API, then run type checking for RED**

Add:

```typescript
export type ClusterConnectionStatus = 'untested' | 'connected' | 'failed'

export interface ClusterConnectionResult {
  connected: boolean
  message: string
  api_server?: string
  kubernetes_version?: string
}

export interface ClusterPayload {
  name: string
  environment_label: string
  kube_context: string
  kubeconfig?: string
  namespace_prefix?: string
  description?: string
  is_default?: boolean
  is_active?: boolean
}
```

Extend `KubernetesCluster` with the safe fields. Add API calls:

```typescript
testClusterConnection: (projectId: number, input: Pick<ClusterPayload, 'kubeconfig' | 'kube_context'>) =>
  client.post<never, ClusterConnectionResult>(`/projects/${projectId}/clusters/test-connection`, input),
testSavedClusterConnection: (projectId: number, clusterId: number) =>
  client.post<never, ClusterConnectionResult>(`/projects/${projectId}/clusters/${clusterId}/test-connection`),
```

Run: `npm --prefix frontend run build`

Expected: FAIL until the existing View is updated to use the required `ClusterPayload` fields.

- [x] **Step 2: Implement the choice screen and existing-cluster form**

In `ProjectKubernetesSettings.vue`, replace direct form opening with a dialog state machine and these
transitions:

```typescript
const dialogStep = ref<'choice' | 'existing'>('choice')

function openAddDialog() {
  editing.value = undefined
  Object.assign(form, defaults)
  dialogStep.value = 'choice'
  dialog.value = true
}

function chooseExistingCluster() {
  dialogStep.value = 'existing'
}

function openEditDialog(item: KubernetesCluster) {
  editing.value = item
  Object.assign(form, {
    name: item.name,
    environment_label: item.environment_label || 'development',
    kube_context: item.kube_context,
    kubeconfig: '',
    namespace_prefix: item.namespace_prefix || '',
    description: item.description || '',
    is_default: item.is_default,
    is_active: item.is_active,
  })
  dialogStep.value = 'existing'
  dialog.value = true
}
```

The `choice` template renders two `button` cards. The Aliyun button is `disabled`, has an “即将支持”
badge, and contains no handler. The existing-cluster button calls `chooseExistingCluster`.

Use this reactive form shape:

```typescript
const defaults: ClusterPayload = {
  name: '',
  environment_label: 'development',
  kube_context: '',
  kubeconfig: '',
  namespace_prefix: '',
  description: '',
  is_default: false,
  is_active: true,
}
```

Use `js-yaml` `load()` to derive contexts with this function; call it from the kubeconfig input's
`@input` handler:

```typescript
interface KubeconfigSummary {
  contexts?: Array<{ name?: string }>
  'current-context'?: string
}

function parseContexts(value: string) {
  contextOptions.value = []
  transientTestResult.value = undefined
  if (!value.trim()) return
  try {
    const parsed = load(value) as KubeconfigSummary
    const names = (parsed?.contexts || [])
      .map(item => item.name?.trim())
      .filter((name): name is string => Boolean(name))
    contextOptions.value = [...new Set(names)]
    const current = parsed?.['current-context']
    form.kube_context = current && names.includes(current) ? current : names[0] || ''
  } catch {
    form.kube_context = ''
    ElMessage.warning('无法解析 kubeconfig')
  }
}
```

Render `<el-select allow-create filterable>` with the four environment label options and
`<el-select>` over `contextOptions` for context selection.

- [x] **Step 3: Add transient and saved test interactions**

Add the test actions exactly as follows and bind them to the form/card buttons:

```typescript
async function testFormConnection() {
  if (!form.kubeconfig?.trim() || !form.kube_context) {
    ElMessage.warning('请粘贴 kubeconfig 并选择 context')
    return
  }
  testing.value = true
  try {
    transientTestResult.value = await projectApi.testClusterConnection(projectId.value, {
      kubeconfig: form.kubeconfig,
      kube_context: form.kube_context,
    })
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    testing.value = false
  }
}

async function testSavedConnection(clusterId: number) {
  testingClusterId.value = clusterId
  try {
    const result = await projectApi.testSavedClusterConnection(projectId.value, clusterId)
    result.connected ? ElMessage.success(result.message) : ElMessage.warning(result.message)
    await refresh()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    testingClusterId.value = undefined
  }
}
```

Render safe success/failure alerts. On dialog close and after save, execute:

```typescript
form.kubeconfig = ''
contextOptions.value = []
transientTestResult.value = undefined
```

Editing copies only safe fields and leaves `kubeconfig` blank. Saving an edit omits the blank
`kubeconfig` property. Display environment label, status, last checked time, version, and actual API
Server on every cluster card.

- [x] **Step 4: Run frontend build and verify GREEN**

Run: `npm --prefix frontend run build`

Expected: `vue-tsc -b` and `vite build` exit 0.

- [x] **Step 5: Commit Task 4**

```bash
git add frontend/src/types.ts frontend/src/api/project.ts frontend/src/views/ProjectKubernetesSettings.vue
git commit -m "feat: add existing kubernetes cluster onboarding UI"
```

### Task 5: Verify acceptance and update project memory

**Files:**
- Modify: `docs/current-state.md`
- Move: `specs/active/project-existing-kubernetes-cluster-onboarding.md` to `specs/completed/project-existing-kubernetes-cluster-onboarding.md`
- Test: all repository checks

**Interfaces:**
- Consumes: all previous tasks and the accepted specification.
- Produces: verified repository state and completed specification with evidence.

- [x] **Step 1: Run the complete verification command**

Run: `./scripts/verify.sh`

Expected: all backend tests pass; frontend type checking and production build pass; exit code 0.

- [x] **Step 2: Inspect secret boundaries and diff quality**

Run:

```bash
rg -n "encrypted_kubeconfig|kubeconfig|test-token-not-a-real-secret" backend/app frontend/src
git diff --check
git status --short
```

Expected: `encrypted_kubeconfig` appears only in model/service persistence code; no View or API response
serializes it; fixture token appears only in tests; `git diff --check` exits 0; status contains only this
feature's intended files.

- [x] **Step 3: Update current state and complete the specification**

Record verified existing-cluster onboarding, encrypted kubeconfig, environment labels, and connectivity
testing in `docs/current-state.md`. Keep Aliyun ACK initialization in “部分实现或过渡中的能力”. In
the specification, check every acceptance item, replace design-stage evidence with actual test/build
evidence, set status to `已验收`, add completion date `2026-07-13`, and move it to `specs/completed/`.

- [x] **Step 4: Re-run the complete verification after documentation changes**

Run: `./scripts/verify.sh`

Expected: exit 0 with the same passing backend and frontend evidence.

- [x] **Step 5: Commit Task 5**

```bash
git add docs/current-state.md specs/active/project-existing-kubernetes-cluster-onboarding.md specs/completed/project-existing-kubernetes-cluster-onboarding.md
git commit -m "docs: record verified kubernetes cluster onboarding"
```
