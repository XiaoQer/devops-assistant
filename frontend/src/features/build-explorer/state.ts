import type { BuildVersion, PipelineLogDetails } from '../../types'

export interface BuildStepDetail {
  id: 'clone' | 'build' | 'push'
  label: 'Clone' | 'Build' | 'Push'
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

function findStep(
  details: PipelineLogDetails,
  matches: (taskName: string, stepName: string) => boolean,
) {
  for (const task of details.tasks) {
    const taskName = task.task_name.toLowerCase()
    for (const step of task.steps) {
      const stepName = `${step.step} ${step.container}`.toLowerCase()
      if (matches(taskName, stepName)) return { task, step }
    }
  }
  return undefined
}

export function normalizeBuildSteps(details: PipelineLogDetails, buildType?: string): BuildStepDetail[] {
  const clone = findStep(details, (_task, step) => step.includes('git-clone'))
  const packageBuild = findStep(details, (task, step) => (
    task === 'package'
    || step.includes('maven')
    || step.includes('npm')
  ))
  const kaniko = findStep(details, (task, step) => (
    task === 'build-image' || step.includes('kaniko')
  ))
  const build = buildType?.toLowerCase() === 'dockerfile' ? kaniko : (packageBuild || kaniko)
  const sources = [
    { id: 'clone', label: 'Clone', source: clone },
    { id: 'build', label: 'Build', source: build },
    { id: 'push', label: 'Push', source: kaniko },
  ] as const
  return sources.flatMap(({ id, label, source }) => source ? [{
    id,
    label,
    status: source.task.status,
    startedAt: source.task.started_at,
    finishedAt: source.task.finished_at,
    logs: source.step.logs,
  }] : [])
}

export function defaultStepId(steps: BuildStepDetail[]) {
  return steps.find(step => step.status === 'Failed')?.id
    || steps.find(step => step.id === 'build')?.id
    || steps[0]?.id
}

export function shouldPollBuild(status: string) {
  return ['Pending', 'Running', 'Building'].includes(status)
}
