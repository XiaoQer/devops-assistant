# Application Multi-Environment Release Design

## Decision

Use one Build Pipeline followed by a Delivery Reconciler that fans out independent Deploy-only
PipelineRuns per selected environment. The release request is pinned to an explicitly selected
public-repository branch and commit; the UI shows at most the latest 20 commits and selects the
newest commit by default.

## Why

A single dynamic Tekton Pipeline would make an arbitrary number of environment tasks difficult to
model, while synchronous backend polling would couple an HTTP request to long-running execution.
The reconciler keeps the existing Build once / Promote boundary, supports independent environment
failure and production approval, and makes retries idempotent.

## Components

- Git metadata service: reads public remote branches and the latest 20 commits for a branch.
- Application release API: validates branch, commit, environment ownership and delivery context,
  then creates one immutable build version and one Build PipelineRun.
- Delivery Reconciler: observes build completion and creates at most one Deploy-only PipelineRun
  per selected environment.
- TektonService: passes the commit to Build Pipeline and the immutable image reference to
  Deploy-only PipelineRuns.
- Application release UI: branch selector, commit list, multi-environment selector and batch
  status view.

## Data and invariants

The build version is immutable for repository, branch, commit, image tag and digest. Environment
deployments reference the build version and retain their own PipelineRun, approval and status.
All environment deployment contexts are resolved server-side at creation or approval time.
One failed environment does not cancel sibling environments; a failed build creates no deployment
run.

## Verification

Cover Git metadata limits and errors, commit-pinned Build Pipeline parameters, multi-environment
fan-out, idempotent reconciliation, independent failure, production approval, project scoping,
and the frontend flow. Run `./scripts/verify.sh` before implementation is considered complete.
