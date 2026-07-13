# Project Existing Kubernetes Cluster Onboarding Design

## Purpose

A Project owner can add an existing Kubernetes cluster with an encrypted kubeconfig, assign one
environment label, and test Kubernetes API connectivity before or after saving. The page also shows
the future Aliyun-backed cluster initialization path without creating cloud resources.

## Product Boundaries

`Project` remains the governance boundary and `KubernetesCluster` remains its child resource. This
increment does not implement Aliyun ACK provisioning, Tekton readiness checks, environment routing,
credential rotation, or an external secret manager.

## User Experience

“Add cluster” first opens a choice between two paths:

1. “Initialize new Kubernetes cluster” explains that Project Aliyun binding will later drive ACK
   provisioning. It is visibly unavailable and performs no mutation.
2. “Add existing cluster” opens the working form.

The existing-cluster form collects name, one environment label, kubeconfig, kube context, Namespace
Prefix, description, default state, and active state. Environment label offers `development`,
`testing`, `staging`, and `production`, plus a custom value. Pasting kubeconfig populates the context
selector and chooses `current-context` when present.

The form can test unsaved values. Saving does not require a successful test. Cluster cards show the
environment label, `untested`, `connected`, or `failed` status, last check time, Kubernetes version,
and a retest action. Edit never displays the stored kubeconfig; an empty kubeconfig field preserves
the existing secret, while a new value replaces it and resets status to `untested`.

## Persistence

Extend `kubernetes_clusters` with:

- `environment_label`: nullable string for migration compatibility, required for new and updated
  records.
- `encrypted_kubeconfig`: nullable text containing Fernet ciphertext.
- `connection_status`: non-null `untested`, `connected`, or `failed` value, default `untested`.
- `last_checked_at`: nullable timezone-aware timestamp.
- `kubernetes_version`: nullable string.

`api_server` remains and is populated from the tested client configuration after success. Existing
rows remain usable after migration with no kubeconfig and an untested status.

Serialization exposes `has_kubeconfig` but never `encrypted_kubeconfig`. Failed-test details are not
persisted because upstream errors may include endpoints or credential-adjacent material.

## Backend Responsibilities

`KubernetesClusterService` owns Project-scoped CRUD, validation, Fernet encryption/decryption, and
persistence of saved-cluster test summaries. Its validation rejects kubeconfig larger than 1 MiB,
non-object YAML, missing selected contexts, non-HTTPS cluster servers, `exec` authentication, and
local file references such as certificate, key, token, or CA paths.

`KubernetesService` gains a focused constructor/factory that accepts kubeconfig content and a context,
builds an isolated API client, applies a short timeout, and reads the Kubernetes Version API. It does
not change process-global kubeconfig state and does not require Tekton.

Expected connection failures are mapped to safe categories: authentication failed, certificate
validation failed, network unreachable, or timed out. Raw Kubernetes, TLS, YAML, and HTTP exception
text is neither logged nor returned.

## API Flow

`POST /api/projects/:projectId/clusters/test-connection` accepts `kubeconfig` and `kube_context`,
validates them, performs the version request, and returns a transient result without persistence.

`POST /api/projects/:projectId/clusters/:clusterId/test-connection` resolves the cluster inside the
specified Project, decrypts its stored kubeconfig, tests it, and updates the summary fields. A cluster
without saved kubeconfig receives a clear validation error.

A successful result contains `connected: true`, safe message text, API Server, and Kubernetes version.
A well-formed configuration that cannot connect returns a successful envelope with
`connected: false` and a safe category message. Invalid input returns a 400 API error. Both actions
retain the repository-wide response envelope.

Create and update accept plaintext `kubeconfig` only as write-only input. Create requires it. Update
preserves the encrypted value when the field is absent or blank and replaces it when a non-blank value
is provided.

## Frontend Responsibilities

`ProjectKubernetesSettings.vue` owns the choice view, form lifecycle, transient kubeconfig text,
context selection, test feedback, and cluster status presentation. It uses the existing centralized
`projectApi`; no HTTP request is written directly in the View.

The browser parses kubeconfig only to derive context names and `current-context`. The backend repeats
all validation because browser validation is not trusted. Closing the dialog or completing a save
clears the plaintext field and transient test result.

## Security Considerations

Encryption uses the existing Fernet convention derived from Flask `SECRET_KEY`. Production still
requires a stable, non-default secret. The design intentionally rejects kubeconfig `exec` plugins and
local file references to prevent server-side command execution or filesystem reads. API responses,
model serialization, errors, logs, fixtures, and documentation contain no real credentials.

Testing an arbitrary API endpoint is an SSRF-sensitive capability. The selected server must use HTTPS,
requests use a short timeout, and the action remains behind the repository's global authentication and
CSRF protections. Private network addresses remain allowed because private Kubernetes API endpoints
are a primary use case.

## Test Strategy

- Migration test proves upgrade and downgrade while retaining pre-existing cluster rows.
- Model and Service tests prove ciphertext-at-rest, safe serialization, credential preservation and
  replacement, environment-label validation, context selection, and rejection of dangerous configs.
- Kubernetes adapter tests use controlled fakes to prove version success and safe classification of
  authentication, TLS, network, and timeout failures without requiring an online cluster.
- Route tests prove transient pre-save testing, persisted retesting, Project scoping, CSRF protection,
  and the uniform response envelope.
- Frontend type checking and production build prove the API/type/view integration compiles.
- `./scripts/verify.sh` remains the final non-interactive acceptance command.

## Delivery State

After all checks pass, update `docs/current-state.md` to describe existing-cluster onboarding and
connectivity testing as verified. Keep Aliyun cluster initialization explicitly listed as unimplemented,
then move the active specification to `specs/completed/` with verification evidence.
