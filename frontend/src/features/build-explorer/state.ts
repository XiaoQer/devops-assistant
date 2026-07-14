import type { BuildVersion, PipelineLogDetails } from '../../types'

export interface BuildStepDetail {
  id: 'clone' | 'build' | 'push'
  label: 'Clone' | 'Build' | 'Push'
  status: string
  startedAt?: string
  finishedAt?: string
  logs: string
}

export function buildExplorerPath(projectId: number, applicationId: number, buildId: number) {
  return `/devcenter/projects/${projectId}/pipelines/applications/${applicationId}/builds/${buildId}`
}

export function selectRequestedBuild(builds: BuildVersion[], requestedId?: number) {
  if (requestedId === undefined) {
    return { build: builds[0], invalidRequestedId: false }
  }
  const build = builds.find(item => item.id === requestedId)
  return { build, invalidRequestedId: !build }
}

function stepKind(value: string): BuildStepDetail['id'] | undefined {
  const normalized = value.toLowerCase()
  if (normalized.includes('clone') || normalized.includes('git')) return 'clone'
  if (normalized.includes('push') && !normalized.includes('build')) return 'push'
  if (normalized.includes('build') || normalized.includes('kaniko')) return 'build'
  return undefined
}

export function normalizeBuildSteps(details: PipelineLogDetails): BuildStepDetail[] {
  const found = new Map<BuildStepDetail['id'], BuildStepDetail>()
  for (const task of details.tasks) {
    for (const step of task.steps) {
      const id = stepKind(`${step.step} ${step.container}`) || stepKind(task.task_name)
      if (!id || found.has(id)) continue
      const labels = { clone: 'Clone', build: 'Build', push: 'Push' } as const
      found.set(id, {
        id,
        label: labels[id],
        status: task.status,
        startedAt: task.started_at,
        finishedAt: task.finished_at,
        logs: step.logs,
      })
    }
  }
  return (['clone', 'build', 'push'] as const)
    .map(id => found.get(id))
    .filter((step): step is BuildStepDetail => Boolean(step))
}

export function defaultStepId(steps: BuildStepDetail[]) {
  return steps.find(step => step.status === 'Failed')?.id
    || steps.find(step => step.id === 'build')?.id
    || steps[0]?.id
}

export function shouldPollBuild(status: string) {
  return ['Pending', 'Running', 'Building'].includes(status)
}
