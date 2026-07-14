# Project-Scoped Application Delivery Design

**Date:** 2026-07-14

**Status:** Approved design, pending implementation plan

## Purpose

Make Application a real Project-scoped delivery aggregate. Project Kubernetes clusters become
Environment deployment targets, and the Project default Registry becomes the build and runtime
image source. The first implementation phase keeps the current central Tekton execution model and
allows only the deploy Task to mount the selected target cluster kubeconfig.

## Confirmed Decisions

1. Tekton remains central and performs both image build and target-cluster deployment in phase one.
2. Each Project Kubernetes cluster has one persistent kubeconfig Secret in the central Tekton
   Namespace. The deploy Task is the only Task that mounts it.
3. A later phase introduces a Delivery Reconciler that observes completed builds, deploys through a
   target-cluster client, and removes persistent target credentials from the central build cluster.
4. Application APIs become strict Project subresources. Global compatibility endpoints are removed.
5. Deployment requires a bound, active, connected Cluster and an active, default, connected Project
   Registry.
6. ProjectMember role authorization is deferred until login users can be reliably linked to members.
   Authentication and Project resource isolation remain mandatory in this phase.

## Architecture

### Control plane and target plane

The central Kubernetes client operates Tekton resources and central build credentials only. A target
Kubernetes client is constructed from the Environment-bound cluster and operates application
resources only.

```text
Central Kubernetes / Tekton
  - PipelineRun
  - Registry credential for Kaniko
  - Persistent target kubeconfig Secret

Environment target Kubernetes cluster
  - Namespace
  - ConfigMap and application Secret
  - Registry imagePullSecret
  - Deployment, Service and Ingress
  - Runtime status, Pod logs and rollback
```

This separation prevents the existing default `KubernetesService()` from silently directing both
control-plane and application operations to the same cluster.

### DeliveryContextService

`DeliveryContextService` is the business boundary for resolving a delivery target. It consumes the
already scoped Project, Application and Environment and resolves:

- active Environment-bound Kubernetes cluster;
- active, default Project Registry;
- target Namespace and kube context;
- image prefix and deployment metadata.

It verifies parent-child ownership and connection state. It returns identifiers and model references,
not decrypted kubeconfig or Registry tokens. Missing, inactive, untested, failed or cross-Project
resources produce stable business errors that Deployment Plan can expose as blocking checks.

### KubernetesClusterService and target clients

`KubernetesClusterService` retains kubeconfig validation and encryption responsibilities and gains a
target-client factory. The factory decrypts the selected cluster kubeconfig, loads the saved context
with `persist_config=False`, and returns a fully initialized `KubernetesService` supporting config,
runtime and rollback operations.

`KubernetesService.from_kubeconfig` must initialize every API used by target operations, not only the
Version API currently required by connection tests.

### ClusterCredentialMaterializer

`ClusterCredentialMaterializer` is the only component allowed to copy target kubeconfig into the
central Tekton Namespace. It uses a deterministic Secret name derived from Project ID and Cluster ID,
labels the Secret as Aegis-managed, and performs an idempotent create-or-patch before every release.

The Secret contains a kubeconfig file only. Secret data and decrypted values are never returned by
models, API serializers or log messages. Updating Project kubeconfig is reflected on the next release
because every release performs an upsert. Deleting a cluster attempts to remove the matching central
Secret after referential checks prevent deletion of a cluster still bound to Environments.

### Configuration and Registry credentials

Configuration materialization accepts distinct central and target clients:

- target client: Namespace, ConfigMap, application Secret and imagePullSecret;
- central client: Kaniko Registry Secret in the Tekton Namespace.

The current behavior that writes both namespaces through one client is removed. Project Registry
lookup never falls back to a platform-level Registry for Application delivery.

### TektonService and Pipeline templates

`TektonService` remains a central-control-plane adapter. PipelineRun creation receives only the target
kubeconfig Secret name and kube context, never kubeconfig content.

The Java Maven, Node npm and Dockerfile Pipeline templates add matching parameters. Their deploy Task
mounts the referenced Secret read-only and invokes `kubectl` with an explicit kubeconfig path and
context. Source, build and Kaniko Tasks do not mount the volume. Existing Registry credentials remain
available only where required for image build.

### ApplicationRuntimeService

`ApplicationRuntimeService` resolves the scoped delivery context, creates the Environment target
client, and owns application status, Pod logs, Pod manifests and rollback. HTTP handlers perform input
validation and serialization only. `ReleaseService` continues to own release records and delegates the
external rollback operation to the runtime service.

## Data Model and Migration

One Alembic migration performs deterministic backfills before adding constraints:

- historical Applications without a Project are assigned to the existing system Default Project;
- `applications.project_id` becomes non-null;
- `pipeline_executions` gains non-null `project_id` plus target `environment`,
  `kubernetes_cluster_id` and `deploy_namespace` snapshot fields;
- `release_records.project_id` and `approval_records.project_id` are backfilled from their Application
  and become non-null;
- Release and Approval records gain target cluster snapshot fields.

Environment cluster binding remains nullable so users may save incomplete configuration. Deployment
readiness, rather than database nullability, blocks incomplete Environments. Legacy platform Registry
rows and the Default Project remain intact, but Application delivery no longer falls back to them.

## Project-Scoped API

The supported resource tree becomes:

```text
/api/projects/{project_id}/applications
/api/projects/{project_id}/applications/{application_id}
/api/projects/{project_id}/applications/{application_id}/environments
/api/projects/{project_id}/applications/{application_id}/configs
/api/projects/{project_id}/applications/{application_id}/deploy/plan
/api/projects/{project_id}/applications/{application_id}/deploy
/api/projects/{project_id}/applications/{application_id}/runtime/...
/api/projects/{project_id}/pipelines
/api/projects/{project_id}/releases
/api/projects/{project_id}/approvals
```

Every lookup includes all parent identifiers. A mismatch returns the same 404 response as a missing
resource. Pipeline status, logs and retry first locate a Project-owned `PipelineExecution`; callers
cannot use an arbitrary PipelineRun name to query central Tekton.

Global Application, Pipeline, Release and Approval compatibility endpoints are removed after the
frontend migrates in the same change set.

## Deployment and Approval Flow

1. Resolve Project, Application and explicitly selected Environment.
2. Build the Delivery Context and produce blocking checks for invalid Cluster or Registry state.
3. If approval is required, persist a Project-scoped Approval with target cluster and Namespace
   snapshots; do not perform external writes.
4. On direct deployment or approval, resolve the Delivery Context again. Approval never bypasses
   current readiness checks.
5. Use the target client to materialize application configuration and runtime Registry Secret.
6. Use the central client to materialize Kaniko Registry credentials and the target kubeconfig Secret.
7. Create the central PipelineRun with target Secret name, context and Namespace parameters.
8. Persist PipelineExecution and Release records only after PipelineRun creation succeeds.
9. Synchronize central Tekton status into Execution, Release, Application and Environment records.

All external writes are idempotent. If target configuration or central credential materialization
fails, no PipelineRun is created. If PipelineRun creation fails, the API reports failure and does not
record a successful or running release.

## Frontend Design

Project routes are the only supported entry points. Application creation obtains Project ID from the
route and shows it as fixed context instead of a switchable selector. Application detail, Pipeline,
Release, Approval and Runtime links retain the Project ID.

Environment cards show the selected cluster and its connection state. Deployment Plan shows target
cluster, Namespace, Registry and actionable blocking checks. The UI may still save incomplete
Application and Environment configuration, but the deploy action remains disabled when the backend
plan reports blocking checks.

## Security and Error Handling

- kubeconfig, Registry tokens and application Secret values never appear in API payloads, errors,
  logs, Pipeline parameters, Release records or test fixtures intended for display;
- target kubeconfig is stored only in the encrypted MySQL column and the central Kubernetes Secret;
- only the deploy Task mounts target kubeconfig;
- Project mismatches return 404 rather than authorization details;
- untested, failed or inactive Cluster and Registry states block deployment;
- connection and Kubernetes failures use stable, sanitized error categories;
- approval revalidation prevents stale approved requests from bypassing current Project policy.

## Verification Strategy

Backend service tests use mocked central and target Kubernetes clients and prove that operations reach
the correct side. Route tests cover every cross-Project lookup and verify 404 isolation. Tekton tests
inspect generated PipelineRun objects and the three Pipeline YAML files to ensure only the deploy Task
mounts kubeconfig. Migration tests perform upgrade, data verification and downgrade.

Frontend tests cover route-derived Project context and Project-preserving navigation. Type checking and
the production build must pass. The final verification runs `./scripts/verify.sh` without requiring an
online Kubernetes cluster, Tekton installation or Registry.

## Deferred Phase: Delivery Reconciler

The next phase splits build from deployment. Central Tekton builds and pushes the image, while a
Delivery Reconciler observes terminal build results and deploys through the target Kubernetes client.
That phase removes persistent target kubeconfig Secrets from the central build cluster and introduces
an idempotent build-to-deploy state machine with retries and recovery. It is intentionally excluded from
the first implementation plan.
