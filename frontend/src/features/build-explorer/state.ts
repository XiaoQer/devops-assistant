import type { BuildVersion, PipelineLogDetails, ReleaseBatch, ReleaseTarget } from '../../types'

export interface ExecutionStepDetail {
  id: string
  taskName: string
  name: string
  label: string
  status: string
  startedAt?: string
  finishedAt?: string
  logs: string
}

export function buildExplorerPath(projectId: number, applicationId: number, buildId?: number) {
  const base = `/devcenter/projects/${projectId}/pipelines/applications/${applicationId}/builds`
  return buildId === undefined ? base : `${base}/${buildId}`
}

export function selectRequestedBuild(builds: BuildVersion[], requestedId?: number) {
  if (requestedId === undefined) {
    return { build: builds[0], invalidRequestedId: false }
  }
  const build = builds.find(item => item.id === requestedId)
  return { build, invalidRequestedId: !build }
}

export function createRequestGate() {
  let generation = 0
  return {
    next: () => ++generation,
    isCurrent: (value: number) => value === generation,
  }
}

export function canRefreshHistory(loadingContext: boolean, buildId?: number): buildId is number {
  return !loadingContext && buildId !== undefined
}

export function canApplyBuildRefresh(
  capturedBuildId: number,
  requestedBuildId?: number,
  selectedBuildId?: number,
) {
  return capturedBuildId === requestedBuildId && capturedBuildId === selectedBuildId
}

export function explorerContentState(
  builds: BuildVersion[],
  invalidRequestedId: boolean,
  loading: boolean,
  hasError = false,
): 'loading' | 'error' | 'invalid' | 'history' | 'empty' {
  if (loading) return 'loading'
  if (hasError) return 'error'
  if (invalidRequestedId) return 'invalid'
  return builds.length ? 'history' : 'empty'
}

export function normalizeExecutionSteps(details: PipelineLogDetails): ExecutionStepDetail[] {
  return details.tasks.flatMap(task => task.steps.map((step, index) => ({
    id: `${task.name}:${step.step}:${index}`,
    taskName: task.task_name,
    name: step.step,
    label: `${task.task_name} / ${step.step}`,
    status: step.status || task.status,
    startedAt: task.started_at,
    finishedAt: task.finished_at,
    logs: step.logs,
  })))
}

const activeStatuses = new Set([
  'Pending', 'Running', 'Building', 'Deploying', 'WaitingApproval', 'WaitingBuild',
])

export function defaultExecutionStepId(steps: ExecutionStepDetail[]) {
  return steps.find(step => step.status === 'Failed')?.id
    || steps.find(step => activeStatuses.has(step.status))?.id
    || steps[0]?.id
}

export function batchForBuild(batches: ReleaseBatch[], buildId?: number) {
  return buildId === undefined
    ? undefined
    : batches.find(batch => batch.build_version_id === buildId)
}

export function hasActiveDelivery(build?: BuildVersion, batch?: ReleaseBatch) {
  if (build && activeStatuses.has(build.status)) return true
  if (!batch) return false
  return activeStatuses.has(batch.status)
    || batch.targets.some(target => activeStatuses.has(target.status))
}

export function targetExecutionState(target: ReleaseTarget) {
  const descriptions: Record<string, string> = {
    WaitingApproval: '等待审批',
    Pending: '等待创建部署 Pipeline',
    WaitingBuild: '等待构建完成',
    Deploying: '部署中',
    Running: '部署中',
    Succeeded: '部署成功',
    Failed: '部署失败',
  }
  return {
    canLoadLogs: Boolean(target.pipeline_run_name),
    description: descriptions[target.status] || target.status,
  }
}

export function defaultTargetId(targets: ReleaseTarget[]) {
  return targets.find(target => target.status === 'Failed')?.id
    || targets.find(target => activeStatuses.has(target.status) && Boolean(target.pipeline_run_name))?.id
    || targets.find(target => Boolean(target.pipeline_run_name))?.id
    || targets[0]?.id
}
