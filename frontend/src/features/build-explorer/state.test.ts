import { describe, expect, it } from 'vitest'
import type { BuildVersion, PipelineLogDetails } from '../../types'
import {
  buildExplorerPath,
  canRefreshHistory,
  createRequestGate,
  defaultStepId,
  explorerContentState,
  normalizeBuildSteps,
  selectRequestedBuild,
  shouldPollBuild,
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

  it('maps Java clone, Maven package and Kaniko image push', () => {
    const steps = normalizeBuildSteps(javaLogDetails, 'maven')
    expect(steps.map(step => step.id)).toEqual(['clone', 'build', 'push'])
    expect(steps.map(step => step.logs)).toEqual(['clone logs', 'maven logs', 'kaniko logs'])
  })

  it('maps Node npm as build even when its task is clone-and-test', () => {
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
    const steps = normalizeBuildSteps(details, 'npm')
    expect(steps.map(step => step.logs)).toEqual(['clone logs', 'npm logs', 'kaniko logs'])
  })

  it('represents Dockerfile Kaniko as both image build and push', () => {
    const details: PipelineLogDetails = {
      ...javaLogDetails,
      tasks: [javaLogDetails.tasks[0], javaLogDetails.tasks[2]],
    }
    const steps = normalizeBuildSteps(details, 'dockerfile')
    expect(steps.map(step => step.id)).toEqual(['clone', 'build', 'push'])
    expect(steps[1].logs).toBe('kaniko logs')
    expect(steps[2].logs).toBe('kaniko logs')
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

  it('selects the first failed step before build', () => {
    expect(defaultStepId([
      { id: 'clone', label: 'Clone', status: 'Succeeded', logs: '' },
      { id: 'build', label: 'Build', status: 'Failed', logs: 'failed' },
    ])).toBe('build')
  })

  it('polls only non-terminal build states', () => {
    expect(shouldPollBuild('Running')).toBe(true)
    expect(shouldPollBuild('Succeeded')).toBe(false)
    expect(shouldPollBuild('Failed')).toBe(false)
  })
})
