import { describe, expect, it } from 'vitest'
import type { BuildVersion, PipelineLogDetails, ReleaseBatch, ReleaseTarget } from '../../types'
import {
  buildExplorerPath,
  canRefreshHistory,
  createRequestGate,
  batchForBuild,
  defaultExecutionStepId,
  explorerContentState,
  hasActiveDelivery,
  normalizeExecutionSteps,
  selectRequestedBuild,
  shouldPollBuild,
  targetExecutionState,
} from './state'

function build(id: number): BuildVersion {
  return {
    id,
    application_id: 12,
    project_id: 7,
    version: `build-${id}`,
    git_repo: 'https://github.com/example/service.git',
    git_branch: 'main',
    image_name: 'registry.example/service',
    image_tag: `build-${id}`,
    image: `registry.example/service:build-${id}`,
    status: 'Succeeded',
    created_by: 'admin',
    created_at: '2026-07-14T08:00:00Z',
  }
}

const javaLogDetails: PipelineLogDetails = {
  pipeline_run: 'service-build-42',
  status: 'Succeeded',
  reason: 'Succeeded',
  logs: 'combined logs',
  tasks: [
    {
      name: 'service-build-42-clone',
      task_name: 'clone',
      status: 'Succeeded',
      steps: [{ step: 'git-clone', container: 'step-git-clone', logs: 'clone logs' }],
    },
    {
      name: 'service-build-42-package',
      task_name: 'package',
      status: 'Succeeded',
      steps: [{ step: 'maven', container: 'step-maven', logs: 'maven logs' }],
    },
    {
      name: 'service-build-42-image',
      task_name: 'build-image',
      status: 'Succeeded',
      steps: [{ step: 'kaniko', container: 'step-kaniko', logs: 'kaniko logs' }],
    },
  ],
}

describe('build explorer state', () => {
  it('builds a stable deep link for an application build', () => {
    expect(buildExplorerPath(7, 12, 42)).toBe(
      '/devcenter/projects/7/pipelines/applications/12/builds/42',
    )
  })

  it('builds the application build history path without a build id', () => {
    expect(buildExplorerPath(7, 12)).toBe(
      '/devcenter/projects/7/pipelines/applications/12/builds',
    )
  })

  it('selects the latest build when no id is requested', () => {
    expect(selectRequestedBuild([build(42), build(41)], undefined).build?.id).toBe(42)
  })

  it('rejects an id outside the application build list', () => {
    expect(selectRequestedBuild([build(42)], 99)).toEqual({
      build: undefined,
      invalidRequestedId: true,
    })
  })

  it('preserves Java Task and Step names in execution order', () => {
    const steps = normalizeExecutionSteps(javaLogDetails)
    expect(steps.map(step => `${step.taskName}/${step.name}`)).toEqual([
      'clone/git-clone', 'package/maven', 'build-image/kaniko',
    ])
    expect(steps.map(step => step.logs)).toEqual(['clone logs', 'maven logs', 'kaniko logs'])
  })

  it('preserves Node npm as an actual step inside clone-and-test', () => {
    const details: PipelineLogDetails = {
      ...javaLogDetails,
      tasks: [
        {
          name: 'node-clone-test', task_name: 'clone-and-test', status: 'Succeeded',
          steps: [
            { step: 'git-clone', container: 'step-git-clone', logs: 'clone logs' },
            { step: 'npm', container: 'step-npm', logs: 'npm logs' },
          ],
        },
        {
          name: 'node-image', task_name: 'build-image', status: 'Succeeded',
          steps: [{ step: 'kaniko', container: 'step-kaniko', logs: 'kaniko logs' }],
        },
      ],
    }
    const steps = normalizeExecutionSteps(details)
    expect(steps.map(step => step.name)).toEqual(['git-clone', 'npm', 'kaniko'])
    expect(steps.map(step => step.logs)).toEqual(['clone logs', 'npm logs', 'kaniko logs'])
  })

  it('does not invent a separate push step for Dockerfile Kaniko', () => {
    const details: PipelineLogDetails = {
      ...javaLogDetails,
      tasks: [javaLogDetails.tasks[0], javaLogDetails.tasks[2]],
    }
    const steps = normalizeExecutionSteps(details)
    expect(steps.map(step => step.name)).toEqual(['git-clone', 'kaniko'])
    expect(steps[1].logs).toBe('kaniko logs')
  })

  it('shows invalid deep-link state before an existing history list', () => {
    expect(explorerContentState([build(42)], true, false)).toBe('invalid')
  })

  it('shows a context request error instead of an empty history', () => {
    expect(explorerContentState([], false, false, true)).toBe('error')
  })

  it('rejects a stale context request generation', () => {
    const gate = createRequestGate()
    const oldRequest = gate.next()
    const newRequest = gate.next()
    expect(gate.isCurrent(oldRequest)).toBe(false)
    expect(gate.isCurrent(newRequest)).toBe(true)
  })

  it('does not let polling supersede a full context load', () => {
    expect(canRefreshHistory(true, 42)).toBe(false)
    expect(canRefreshHistory(false, 42)).toBe(true)
  })

  it('selects failed, then active, then first execution step', () => {
    const steps = normalizeExecutionSteps(javaLogDetails)
    expect(defaultExecutionStepId([
      { ...steps[0], status: 'Succeeded' },
      { ...steps[1], status: 'Running' },
    ])).toBe(steps[1].id)
    expect(defaultExecutionStepId([
      { ...steps[0], status: 'Failed' },
      { ...steps[1], status: 'Running' },
    ])).toBe(steps[0].id)
    expect(defaultExecutionStepId(steps)).toBe(steps[0].id)
  })

  it('associates a release batch with its exact build version', () => {
    const batches = [
      { id: 1, build_version_id: 41 },
      { id: 2, build_version_id: 42 },
    ] as ReleaseBatch[]
    expect(batchForBuild(batches, 42)?.id).toBe(2)
  })

  it('keeps polling while any environment target is active', () => {
    const batch = {
      id: 2,
      build_version_id: 42,
      status: 'Deploying',
      targets: [{ id: 7, status: 'Deploying' }],
    } as ReleaseBatch
    expect(hasActiveDelivery(build(42), batch)).toBe(true)
    expect(hasActiveDelivery(build(42), { ...batch, status: 'Succeeded', targets: [{ id: 7, status: 'Succeeded' }] } as ReleaseBatch)).toBe(false)
  })

  it('describes target business state without inventing a PipelineRun', () => {
    const waiting = targetExecutionState({ status: 'WaitingApproval' } as ReleaseTarget)
    expect(waiting).toEqual({ canLoadLogs: false, description: '等待审批' })
    const pending = targetExecutionState({ status: 'Pending' } as ReleaseTarget)
    expect(pending).toEqual({ canLoadLogs: false, description: '等待创建部署 Pipeline' })
  })

  it('loads logs only when the environment target has a PipelineRun', () => {
    const deploying = targetExecutionState({
      status: 'Deploying',
      pipeline_run_name: 'deploy-qa-1',
    } as ReleaseTarget)
    expect(deploying).toEqual({ canLoadLogs: true, description: '部署中' })
  })

  it('polls only non-terminal build states', () => {
    expect(shouldPollBuild('Running')).toBe(true)
    expect(shouldPollBuild('Succeeded')).toBe(false)
    expect(shouldPollBuild('Failed')).toBe(false)
  })
})
