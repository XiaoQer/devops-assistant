# Application Branch Commit Multi-Environment Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline execution) to implement this plan task-by-task with review checkpoints.

**Goal:** Let users choose a public-repository branch and commit, select multiple environments, build one immutable image once, and promote it independently to every selected environment.

**Architecture:** Add a public Git metadata service and project-scoped endpoints for branches and the latest 20 commits. Persist one immutable release batch with one build version and one target per environment. A Delivery Reconciler observes build completion and idempotently creates Deploy-only PipelineRuns using each environment’s Kubernetes context, Namespace, and configuration.

**Tech Stack:** Flask, SQLAlchemy, Alembic, GitPython, Kubernetes/Tekton custom resources, Vue 3, TypeScript, Element Plus, pytest.

## Global Constraints

- Only public Git repositories are supported; no Git credentials are added.
- Commit history is capped server-side at 20 records.
- APIs remain under the project-scoped application routes and enforce parent ownership.
- One release batch creates exactly one Build PipelineRun and at most one Deploy-only PipelineRun per target environment.
- Target failures are independent; build failure creates no deployment runs.
- Production approval is scoped to one build version and one environment.
- Secrets and credentials never appear in API responses, logs, errors, or Pipeline parameters.
- Every schema change includes an Alembic migration.

---

### Task 1: Public Git branch and commit metadata

**Files:** Create `backend/app/services/git_metadata_service.py` and `backend/tests/test_git_metadata_service.py`; modify `backend/app/routes/applications.py` and `backend/tests/test_project_application_routes.py`.

**Interfaces:**

- `GitMetadataService.list_branches(repo_url) -> list[{name, sha}]`.
- `GitMetadataService.list_commits(repo_url, branch, limit=20) -> list[{sha, message, author, authored_at}]`.
- `GET /api/projects/{project_id}/applications/{app_id}/git/branches`.
- `GET /api/projects/{project_id}/applications/{app_id}/git/branches/{branch}/commits?limit=20`.

- [ ] Write tests for branch discovery, newest-first commits, server-side limit 20, missing branch, and inaccessible public repository.
- [ ] Implement GitPython temporary remote access with cleanup in `finally`; raise `GIT_REPOSITORY_UNAVAILABLE`, `GIT_BRANCH_NOT_FOUND`, and `GIT_COMMITS_UNAVAILABLE` without local paths or credentials.
- [ ] Add project-scoped routes that resolve the application first and cap any requested limit at 20.
- [ ] Run `backend/.venv/bin/python -m pytest backend/tests/test_git_metadata_service.py backend/tests/test_project_application_routes.py -q`.

### Task 2: Release batch and target persistence

**Files:** Create `backend/app/models/application_release_batch.py` and `backend/app/models/application_release_target.py`; modify `backend/app/models/__init__.py`, `application.py`, `build_version.py`, `pipeline_execution.py`, and `approval_record.py`; create an Alembic migration; test in `backend/tests/test_release_batch_models.py`.

**Interfaces:**

- `ApplicationReleaseBatch`: application/project, branch, commit, commit message/author, status, build version, creator, timestamps.
- `ApplicationReleaseTarget`: batch, environment, build version, PipelineRun, status, approval, error, timestamps; unique `(batch_id, environment_id)`.
- BuildVersion gains immutable `commit_message` and `commit_author`.

- [ ] Add model tests for multiple targets, duplicate target rejection, relationships, and safe serialization.
- [ ] Implement foreign keys, indexes, cascade behavior, and `to_dict()` methods following existing model conventions.
- [ ] Add upgrade/downgrade migration with nullable backfill-safe columns and explicit uniqueness/index operations.
- [ ] Run the focused model tests and temporary SQLite migration upgrade/downgrade check.

### Task 3: Commit-pinned Build Pipeline

**Files:** Modify `backend/app/services/application_service.py`, `build_version_service.py`, `tekton_service.py`, the three `deploy/tekton/pipelines/*-build.yaml` manifests, and tests in `backend/tests/test_application_service.py` and `test_tekton_service.py`.

- [ ] Add failing tests proving a selected commit is stored and passed to the PipelineRun, and no deployment run is created in the build path.
- [ ] Add required `commit` parameters to Java Maven, Node npm, and Dockerfile build Pipelines; checkout the requested SHA after fetching the selected branch and fail if it is unavailable.
- [ ] Extend `ApplicationService.build(...)` with branch, commit, commit message, commit author, and release batch context; preserve one BuildVersion and one Build PipelineRun per batch.
- [ ] Label/annotate the Build PipelineRun with the release batch identifier.
- [ ] Run focused Python tests plus YAML parsing for all build manifests.

### Task 4: Release batch API and validation

**Files:** Create or modify `backend/app/services/release_batch_service.py`; modify `backend/app/routes/applications.py`, `deployment_plan_service.py`, `approval_service.py`, and `release_service.py`; test in `backend/tests/test_release_batch_service.py` and `test_project_application_routes.py`.

**Interfaces:**

- `POST /api/projects/{project_id}/applications/{app_id}/release-batches` with `{branch, git_commit, environment_ids}`.
- `GET /api/projects/{project_id}/applications/{app_id}/release-batches`.
- `GET /api/projects/{project_id}/applications/{app_id}/release-batches/{batch_id}`.
- `ReleaseBatchService.create(app, branch, git_commit, environment_ids, user)`.

- [ ] Test invalid commit, empty/duplicate/cross-application environments, invalid delivery contexts, one-build creation, and production target approval.
- [ ] Re-read the selected commit server-side, resolve every environment and DeliveryContext, and create batch plus unique targets transactionally before creating the single Build PipelineRun.
- [ ] Keep production approval independent from non-production targets and revalidate context during approval.
- [ ] Run focused tests and verify standard API response/error structures.

### Task 5: Delivery Reconciler fan-out

**Files:** Create `backend/app/services/delivery_reconciler.py` and `backend/tests/test_delivery_reconciler.py`; modify `backend/app/services/build_version_service.py`, `approval_service.py`, and `backend/app/routes/applications.py`.

**Interfaces:**

- `DeliveryReconciler.reconcile_batch(batch_id) -> dict`.
- `DeliveryReconciler.reconcile_pending() -> int`.

- [ ] Test build failure with zero deploy runs, successful fan-out to every eligible target, repeated scans without duplicates, independent target failure, and approval waiting.
- [ ] Synchronize Tekton status into BuildVersion and target status without leaking secrets.
- [ ] Resolve current environment context immediately before creating each Deploy-only PipelineRun; persist PipelineRun, execution, release, and approval links.
- [ ] Use the target uniqueness constraint and persisted PipelineRun name as the idempotency key.
- [ ] Invoke reconciliation from batch/build detail reads for local responsiveness and expose the service entry point for periodic worker/cron execution without blocking HTTP on Tekton completion.

### Task 6: Frontend release flow

**Files:** Modify `frontend/src/api/application.ts`, `frontend/src/types.ts`, and `frontend/src/views/ApplicationDetail.vue`; create `frontend/src/components/application/ReleaseBatchStatus.vue` for the batch status list and polling presentation.

**Interfaces:**

- `applicationApi.gitBranches(projectId, applicationId)`.
- `applicationApi.gitCommits(projectId, applicationId, branch, limit=20)`.
- `applicationApi.createReleaseBatch(projectId, applicationId, input)` and `releaseBatch(...)`.
- Types: `GitBranch`, `GitCommit`, `ReleaseBatch`, `ReleaseTarget`.

- [ ] Replace the deployment dialog with branch selection, latest-20 commit selection (newest default), and multi-select environment cards showing cluster, Namespace, approval, and current status.
- [ ] Disable submit until a commit and at least one environment are selected; show repository/branch/commit errors inline.
- [ ] Poll batch details while build/targets are active and show build failure, waiting approval, deploying, partial success, and complete states.
- [ ] Run `npm --prefix frontend run build` and verify the existing project-scoped navigation remains intact.

### Task 7: Verification and specification completion

**Files:** Modify `docs/current-state.md`; move `specs/active/application-branch-commit-multi-environment-release.md` to `specs/completed/` only after acceptance.

- [ ] Run `./scripts/verify.sh`.
- [ ] Verify one Build PipelineRun, N Deploy-only PipelineRuns, one shared image Tag/Digest, independent failures, and no deploy runs after build failure with mocked Tekton tests.
- [ ] Document the verified public-repository-only limitation, 20-commit limit, release batch/reconciler behavior, and remaining worker operation requirements.
- [ ] Check every active-spec acceptance box with evidence, update status to accepted, and move the spec to completed.
