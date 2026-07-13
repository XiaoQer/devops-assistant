# Project Registry Connectivity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add secure Project-scoped Registry configuration and OCI `/v2/` Basic/Bearer connectivity testing, including transient form checks, persisted saved checks, GHCR, and explicit insecure-TLS warnings.

**Architecture:** A focused `OCIRegistryClient` owns HTTPS and OCI authentication behavior, while `RegistryService` owns Project scoping, validation, encryption, and persisted connection state. Project routes expose Registry CRUD and two test modes; the Vue page consumes only those scoped routes and never receives a Token.

**Tech Stack:** Flask 3.1, SQLAlchemy 2, Alembic, urllib3 2.7, pytest/unittest, Vue 3, TypeScript, Axios, Element Plus.

## Global Constraints

- `Project` is the governance and workspace boundary; every Registry mutation and saved test resolves by Project ID plus Registry ID.
- Registry username and Token are required; anonymous Registry access is not supported.
- Registry and Bearer authorization endpoints must use HTTPS. `skip_tls_verify` may disable certificate verification but must never enable HTTP.
- Support `acr`, `harbor`, `dockerhub`, `ecr`, `gcr`, `generic`, and `ghcr` through OCI `/v2/` Basic or Bearer Challenge.
- Do not perform Push, Pull, Manifest, Catalog, ImagePullSecret synchronization, cloud Token refresh, custom CA management, or background health checks.
- Do not expose plaintext Token, Authorization headers, Bearer tokens, encrypted values, or raw remote bodies through API responses, logs, fixtures, or error messages.
- Every API response keeps `success`, `message`, `data`, `timestamp`, and `trace_id`.
- Unit tests must not call a live Registry, Kubernetes cluster, DNS service, or the public internet.

---

## File Structure

- Create `backend/app/services/oci_registry_client.py`: target validation, HTTPS requests, Basic/Bearer authentication, timeout and safe failure classification.
- Modify `backend/app/services/registry_service.py`: Project-scoped CRUD, credential validation, transient/saved test orchestration, state resets and persistence.
- Modify `backend/app/models/container_registry.py`: TLS and connection-state columns plus safe serialization.
- Create `backend/migrations/versions/e5f6a7b8c9d0_add_registry_connectivity.py`: additive Registry connectivity migration after `d4e5f6a7b8c9`.
- Create `backend/tests/test_registry_migration.py`: isolated upgrade/downgrade preservation evidence.
- Create `backend/tests/test_oci_registry_client.py`: protocol and security unit tests using fake HTTP responses and resolver results.
- Modify `backend/tests/test_registry_service.py`: Project scope, credential behavior, state reset and persisted tests.
- Modify `backend/app/routes/projects.py`: Project Registry subresource CRUD and test endpoints.
- Delete `backend/app/routes/registries.py` and remove its blueprint registration after callers migrate.
- Modify `backend/tests/test_project_routes.py` and `backend/tests/test_validation_routes.py`: route envelope, Project isolation, transient/saved behavior and validation.
- Modify `backend/requirements.txt`: declare the directly imported urllib3 version already present in the workspace.
- Modify `frontend/src/types.ts`: Registry status, payload and result types.
- Modify `frontend/src/api/project.ts`: Project Registry CRUD and test calls.
- Delete `frontend/src/api/registry.ts` after both Registry views stop importing it.
- Modify `frontend/src/views/ProjectRegistriesSettings.vue`: resource cards, form test, Provider selector and TLS warning.
- Modify `frontend/src/views/ContainerRegistries.vue`: use the same Project-scoped API so the compatibility page cannot bypass Project scope.
- Modify `docs/current-state.md`: record only verified Registry connectivity behavior.
- Update and move `specs/active/project-registry-connectivity.md` to `specs/completed/project-registry-connectivity.md` only after all checks pass and acceptance evidence is recorded.

### Task 1: Persist Registry TLS and connection state

**Files:**
- Modify: `backend/app/models/container_registry.py`
- Create: `backend/migrations/versions/e5f6a7b8c9d0_add_registry_connectivity.py`
- Create: `backend/tests/test_registry_migration.py`

**Interfaces:**
- Produces model fields `skip_tls_verify: bool`, `connection_status: str`, `last_checked_at: datetime | None`, and `last_connection_message: str | None`.
- Produces `ContainerRegistry.to_dict()` keys with the same names while continuing to omit `encrypted_password`.

- [ ] **Step 1: Write the failing model and migration tests**

Add a model serialization assertion to `backend/tests/test_registry_service.py` and create an isolated migration test based on `test_kubernetes_cluster_migration.py`. Seed a Registry at revision `d4e5f6a7b8c9`, upgrade to `e5f6a7b8c9d0`, and assert:

```python
columns = {column["name"] for column in inspector.get_columns("container_registries")}
assert {
    "skip_tls_verify",
    "connection_status",
    "last_checked_at",
    "last_connection_message",
}.issubset(columns)

row = connection.execute(sa.text(
    "SELECT name, skip_tls_verify, connection_status "
    "FROM container_registries WHERE name = 'Existing Harbor'"
)).mappings().one()
assert row["name"] == "Existing Harbor"
assert not row["skip_tls_verify"]
assert row["connection_status"] == "untested"
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_registry_service.py tests/test_registry_migration.py -q`

Expected: FAIL because the four model fields and migration revision do not exist.

- [ ] **Step 3: Add the model fields and serialization**

Define:

```python
skip_tls_verify = db.Column(db.Boolean, default=False, nullable=False)
connection_status = db.Column(db.String(20), default="untested", nullable=False)
last_checked_at = db.Column(db.DateTime(timezone=True))
last_connection_message = db.Column(db.String(300))
```

Return safe values from `to_dict()`:

```python
"skip_tls_verify": self.skip_tls_verify,
"connection_status": self.connection_status,
"last_checked_at": self.last_checked_at.isoformat() if self.last_checked_at else None,
"last_connection_message": self.last_connection_message,
```

- [ ] **Step 4: Add the additive Alembic migration**

Set `revision = "e5f6a7b8c9d0"` and `down_revision = "d4e5f6a7b8c9"`. Use `batch_alter_table` to add the four columns with server defaults for the two non-null fields, then remove those temporary defaults. Downgrade drops only these four columns.

- [ ] **Step 5: Run the focused tests**

Run: `cd backend && .venv/bin/python -m pytest tests/test_registry_service.py tests/test_registry_migration.py -q`

Expected: PASS, including upgrade/downgrade data preservation.

- [ ] **Step 6: Commit the persistence slice**

```bash
git add backend/app/models/container_registry.py backend/migrations/versions/e5f6a7b8c9d0_add_registry_connectivity.py backend/tests/test_registry_service.py backend/tests/test_registry_migration.py
git commit -m "feat: persist registry connection state"
```

### Task 2: Implement the isolated OCI Registry client

**Files:**
- Create: `backend/app/services/oci_registry_client.py`
- Create: `backend/tests/test_oci_registry_client.py`
- Modify: `backend/requirements.txt`

**Interfaces:**
- Produces `OCIRegistryClient.test(server: str, username: str, token: str, skip_tls_verify: bool = False) -> dict`.
- Success result: `{"connected": True, "message": str, "tls_verified": bool, "auth_method": "basic" | "bearer"}`.
- Failure result: `{"connected": False, "message": str, "tls_verified": bool, "failure_reason": "authentication_failed" | "tls_failed" | "timeout" | "unreachable" | "protocol_error"}`.
- Constructor permits injected `requester` and `resolver` callables so tests never use the network.

- [ ] **Step 1: Write failing protocol tests**

Cover these exact cases with fake responses containing only `status`, `headers`, and `data`:

```python
def test_basic_success():
    client = client_with_responses(response(200))
    result = client.test("ghcr.io", "octocat", "fake-test-token")
    assert result["connected"] is True
    assert result["auth_method"] == "basic"
    assert result["tls_verified"] is True


def test_bearer_challenge_exchanges_token_and_retries_v2():
    challenge = 'Bearer realm="https://auth.example.test/token",service="registry.example.test"'
    client = client_with_responses(
        response(401, {"WWW-Authenticate": challenge}),
        response(200, data=b'{"token":"fake-bearer-token"}'),
        response(200),
    )
    result = client.test("registry.example.test", "robot", "fake-test-token")
    assert result["connected"] is True
    assert result["auth_method"] == "bearer"
```

Also assert Basic/Bearer 401 maps to `authentication_failed`, malformed/missing challenges and token JSON map to `protocol_error`, TLS exceptions map to `tls_failed`, timeout exceptions map to `timeout`, connection/DNS failures map to `unreachable`, and `skip_tls_verify=True` returns `tls_verified=False`.

- [ ] **Step 2: Write failing target-safety tests**

Assert HTTP input, `localhost`, loopback, link-local, multicast, unspecified and `169.254.169.254` are rejected before `requester` is called. Assert `10.0.0.20` and a resolver result containing a public address are allowed. Assert an unsafe or HTTP Bearer realm returns `protocol_error` without forwarding credentials.

- [ ] **Step 3: Run the client tests and verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_oci_registry_client.py -q`

Expected: FAIL with `ModuleNotFoundError: app.services.oci_registry_client`.

- [ ] **Step 4: Implement target validation and safe request plumbing**

Implement `OCIRegistryClient` with `urllib3.PoolManager`, a five-second connect timeout, a ten-second read timeout, `redirect=False`, bounded token response parsing, and an explicit Basic Authorization header created with base64. Declare `urllib3==2.7.0` in `backend/requirements.txt` because it becomes a direct dependency.

Use `ipaddress.ip_address()` and the injected resolver to reject `is_loopback`, `is_link_local`, `is_multicast`, and `is_unspecified`; allow `is_private` except the explicit cloud metadata/link-local ranges. Accept bare Registry host/port input by constructing `https://<server>/v2/`, but reject any input whose supplied scheme is not HTTPS.

- [ ] **Step 5: Implement Basic and Bearer Challenge handling**

Parse only quoted challenge parameters with a bounded regular expression, require an HTTPS `realm`, pass optional `service` and `scope` as query fields, accept `token` or `access_token`, and retry `/v2/` with `Bearer <value>`. Never interpolate credentials, headers, token response bodies, or exception text into returned messages.

- [ ] **Step 6: Run the client tests**

Run: `cd backend && .venv/bin/python -m pytest tests/test_oci_registry_client.py -q`

Expected: PASS with no external network access.

- [ ] **Step 7: Commit the OCI client slice**

```bash
git add backend/app/services/oci_registry_client.py backend/tests/test_oci_registry_client.py backend/requirements.txt
git commit -m "feat: add OCI registry connectivity client"
```

### Task 3: Add Project-scoped Registry service behavior

**Files:**
- Modify: `backend/app/services/registry_service.py`
- Modify: `backend/tests/test_registry_service.py`

**Interfaces:**
- `list(project) -> list[ContainerRegistry]`
- `get(project, registry_id) -> ContainerRegistry`, raising `REGISTRY_NOT_FOUND` without cross-Project disclosure.
- `create(project, payload)`, `update(item, payload)`, `delete(item)`, and `set_default(item)` preserve the single-default invariant inside the Project.
- `test_connection(payload, current=None) -> dict` validates unsaved/override values and never persists.
- `test_saved_connection(item) -> dict` uses stored credentials and persists status, timestamp, and safe message.

- [ ] **Step 1: Write failing service tests for Project scope and credentials**

Create two Projects and assert `list()` and `get()` cannot cross scopes. Assert `ghcr` is accepted. Assert create rejects a blank username or Token. Assert encrypted Token and API serialization never expose `fake-test-token`. Assert update with blank `password` keeps the saved encrypted value while `clear_credentials` is no longer accepted as a valid persisted configuration.

- [ ] **Step 2: Write failing service tests for transient and saved checks**

Inject a fake client into `RegistryService`. Assert:

```python
result = service.test_connection({
    "server": "ghcr.io",
    "username": "octocat",
    "password": "fake-test-token",
    "skip_tls_verify": False,
})
assert result["connected"] is True
assert ContainerRegistry.query.count() == 0
```

For an existing item, assert `test_connection(payload, current=item)` uses the stored Token when `password` is blank but does not change database status. Assert `test_saved_connection(item)` sets `connected`/`failed`, `last_checked_at`, and the backend-generated message.

- [ ] **Step 3: Write failing state-reset tests**

Start with a connected item. Updating `server`, `username`, non-empty `password`, or `skip_tls_verify` must set status to `untested` and clear time/message. Updating only `name`, `namespace`, `email`, `pull_secret_name`, `is_active`, or default status must retain the connection result.

- [ ] **Step 4: Run focused tests and verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_registry_service.py -q`

Expected: FAIL because the old service accepts optional credentials, lacks Project object scoping, GHCR, test orchestration, and reset behavior.

- [ ] **Step 5: Implement the minimal service changes**

Add constructor injection:

```python
def __init__(self, connectivity_client=None):
    self.connectivity_client = connectivity_client or OCIRegistryClient()
```

Change `PROVIDERS` to include `ghcr`; make create require both username and password; let update reuse the existing encrypted Token only when the incoming password is absent or blank. Compare normalized connection fields before mutation and call a focused `_reset_connection_state(item)` only when they change.

For saved testing, persist only the safe client result:

```python
item.connection_status = "connected" if result["connected"] else "failed"
item.last_checked_at = datetime.now(timezone.utc)
item.last_connection_message = result["message"][:300]
db.session.commit()
```

- [ ] **Step 6: Run focused service tests**

Run: `cd backend && .venv/bin/python -m pytest tests/test_registry_service.py -q`

Expected: PASS.

- [ ] **Step 7: Commit the service slice**

```bash
git add backend/app/services/registry_service.py backend/tests/test_registry_service.py
git commit -m "feat: manage project registry connectivity"
```

### Task 4: Expose Project Registry routes and remove the unscoped API

**Files:**
- Modify: `backend/app/routes/projects.py`
- Modify: `backend/app/routes/__init__.py`
- Modify: `backend/app/__init__.py`
- Delete: `backend/app/routes/registries.py`
- Modify: `backend/tests/test_project_routes.py`
- Modify: `backend/tests/test_validation_routes.py`

**Interfaces:**
- Exposes the seven endpoints specified in `specs/active/project-registry-connectivity.md` under `/api/projects/<project_id>/registries`.
- Transient test payload requires `server`, `username`, and `password` for new configuration.
- Saved test accepts an optional JSON object of overrides; an empty or absent body performs and persists the saved check.

- [ ] **Step 1: Write failing route tests for scoped CRUD**

Create/list/update/default/delete a Registry exclusively through `/api/projects/<project_id>/registries`. For each ID route, call it with a second Project ID and assert status 404 with `REGISTRY_NOT_FOUND`. Assert the old `/api/registries` path returns 404 after migration.

- [ ] **Step 2: Write failing route tests for both test modes**

Patch `registry_service.test_connection` and assert transient testing returns the standard envelope and does not persist. Patch `test_saved_connection` and assert an empty saved-test request persists through the service. For an override payload, patch `test_connection`, assert it receives `current=item`, and assert the saved status remains unchanged.

- [ ] **Step 3: Write validation and secret-boundary route tests**

Assert list/non-object payloads return `INVALID_REQUEST_BODY`; missing transient `server`, `username`, or `password` returns `VALIDATION_ERROR`; create requires `name`, `server`, `username`, and `password`. Recursively serialize every response and assert `fake-test-token`, `Authorization`, `encrypted_password`, and `fake-bearer-token` are absent.

- [ ] **Step 4: Run route tests and verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_project_routes.py tests/test_validation_routes.py -q`

Expected: FAIL because Project Registry routes do not exist and the unscoped blueprint is still registered.

- [ ] **Step 5: Add Project routes and remove the old blueprint**

Instantiate `registry_service = RegistryService()` beside `cluster_service`. Every route begins with `project = get_project(project_id)` and every ID operation calls `registry_service.get(project, registry_id)`. Use `json_object()` and `require_fields()` at the transport boundary, then wrap service output with `success()`.

Remove `registries_bp` exports/imports and delete the old route file only after every route test targets the Project API.

- [ ] **Step 6: Run all relevant backend tests**

Run: `cd backend && .venv/bin/python -m pytest tests/test_oci_registry_client.py tests/test_registry_service.py tests/test_registry_migration.py tests/test_project_routes.py tests/test_validation_routes.py tests/test_application_service.py tests/test_deployment_plan_service.py tests/test_tekton_service.py -q`

Expected: PASS; deployment consumers still obtain decrypted Registry credentials through `RegistryService.credentials()`.

- [ ] **Step 7: Commit the route slice**

```bash
git add backend/app/routes/projects.py backend/app/routes/__init__.py backend/app/__init__.py backend/tests/test_project_routes.py backend/tests/test_validation_routes.py backend/app/routes/registries.py
git commit -m "feat: scope registry API to projects"
```

### Task 5: Build the Registry connectivity UI

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api/project.ts`
- Delete: `frontend/src/api/registry.ts`
- Modify: `frontend/src/views/ProjectRegistriesSettings.vue`
- Modify: `frontend/src/views/ContainerRegistries.vue`

**Interfaces:**
- Adds `RegistryConnectionStatus`, `RegistryConnectionResult`, and `RegistryPayload` types.
- `projectApi` exposes `registries`, `addRegistry`, `updateRegistry`, `removeRegistry`, `setDefaultRegistry`, `testRegistryConnection`, and `testSavedRegistryConnection`.

- [ ] **Step 1: Add types and Project API methods**

Define:

```typescript
export type RegistryConnectionStatus = 'untested' | 'connected' | 'failed'

export interface RegistryPayload {
  name: string
  provider: ContainerRegistry['provider']
  server: string
  namespace?: string
  username: string
  password?: string
  email?: string
  pull_secret_name?: string
  skip_tls_verify: boolean
  is_active: boolean
}

export interface RegistryConnectionResult {
  connected: boolean
  message: string
  tls_verified: boolean
  auth_method?: 'basic' | 'bearer'
  failure_reason?: 'authentication_failed' | 'tls_failed' | 'timeout' | 'unreachable' | 'protocol_error'
}
```

Extend `ContainerRegistry` with the four persisted fields. Implement Project endpoint methods in `projectApi`; the saved-test method accepts optional overrides so editing can test current unsaved fields while a card call sends no body.

- [ ] **Step 2: Run the scoped-API source check and verify it fails**

Run: `rg -n "registryApi|['\"]\/registries" frontend/src/api frontend/src/views`

Expected: matches in `api/registry.ts`, `ProjectRegistriesSettings.vue`, and
`ContainerRegistries.vue`, proving the frontend still uses the unscoped API.

- [ ] **Step 3: Update the Project Registry cards**

Render status labels using `untested → 未测试`, `connected → 已连接`, and `failed → 连接失败`. Show `last_checked_at`, `last_connection_message`, and a persistent warning when `skip_tls_verify` is true. Add a per-card `testingRegistryId` loading state and a direct “测试连接” button that calls `testSavedRegistryConnection(projectId, registry.id)` then refreshes.

- [ ] **Step 4: Update the dialog**

Replace the Provider text input with options for ACR, Harbor, Docker Hub, ECR, GCR, Generic OCI, and GitHub Container Registry. Require Server and username; require Token on create and allow blank Token only on edit. Add `skip_tls_verify` switch, risk copy, `testingForm` loading state and an inline result panel.

On edit, call the saved-test endpoint with overrides so a blank password reuses the saved Token. On create, call the transient endpoint. Do not close the dialog or block save when the result has `connected: false`.

- [ ] **Step 5: Migrate the compatibility Registry view**

Use `projectStore.activeProjectId` for every call to the Project API. Keep its existing layout, Provider labels and actions, but route all list/create/update/delete/default calls through `projectApi`; remove its import of `registryApi`.

- [ ] **Step 6: Delete the unscoped frontend API and verify**

Delete `frontend/src/api/registry.ts`, then run:

`cd frontend && npm run type-check && npm run build`

Expected: both commands PASS; no source file imports `../api/registry` or calls `/registries` without a Project path.

- [ ] **Step 7: Commit the frontend slice**

```bash
git add frontend/src/types.ts frontend/src/api/project.ts frontend/src/api/registry.ts frontend/src/views/ProjectRegistriesSettings.vue frontend/src/views/ContainerRegistries.vue
git commit -m "feat: add registry connectivity workspace"
```

### Task 6: Verify, document, and complete the active specification

**Files:**
- Modify: `docs/current-state.md`
- Move: `specs/active/project-registry-connectivity.md` to `specs/completed/project-registry-connectivity.md`

**Interfaces:**
- Produces repository-level evidence that every acceptance criterion is implemented and verified.

- [ ] **Step 1: Run focused secret and behavior checks**

Run:

```bash
cd backend && .venv/bin/python -m pytest tests/test_oci_registry_client.py tests/test_registry_service.py tests/test_registry_migration.py tests/test_project_routes.py tests/test_validation_routes.py -q
```

Expected: all focused tests PASS with no network access.

- [ ] **Step 2: Run the complete repository verification**

Run: `./scripts/verify.sh`

Expected: backend suite, frontend type check, frontend production build, and migration checks all PASS. Existing documented warnings may remain warnings but no new failure is accepted.

- [ ] **Step 3: Review the Registry page manually**

Verify create/edit validation, Provider options including GHCR, inline success/failure results, saved card retest, status/time/message rendering, and persistent insecure-TLS warning. Do not enter production credentials; use local test-only values.

- [ ] **Step 4: Update repository memory and acceptance evidence**

Add the implemented Registry behavior and latest verification counts to `docs/current-state.md`. In the active spec, check each proven acceptance item and record exact commands/results under `验证证据`; do not claim a manual check that was not run.

- [ ] **Step 5: Complete the specification**

Set status to `已验收`, record `2026-07-13`, and move the file:

Run: `git mv specs/active/project-registry-connectivity.md specs/completed/project-registry-connectivity.md`

Expected: the active specification is removed and its completed counterpart is staged as a rename.

- [ ] **Step 6: Re-run final verification after documentation changes**

Run: `git diff --check && ./scripts/verify.sh`

Expected: whitespace check and full verification PASS.

- [ ] **Step 7: Commit the verified feature**

```bash
git add docs/current-state.md specs/active/project-registry-connectivity.md specs/completed/project-registry-connectivity.md
git commit -m "docs: record verified registry connectivity"
```
