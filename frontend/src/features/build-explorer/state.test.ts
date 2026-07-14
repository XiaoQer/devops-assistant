import { describe, expect, it } from 'vitest'
import type { BuildVersion, PipelineLogDetails } from '../../types'
import {
  defaultStepId,
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

const logDetails: PipelineLogDetails = {
  pipeline_run: 'service-build-42',
  status: 'Succeeded',
  reason: 'Succeeded',
  logs: 'combined logs',
  tasks: [
    {
      name: 'service-build-42-build-pod',
      task_name: 'kaniko-build',
      status: 'Succeeded',
      steps: [
        { step: 'git-clone', container: 'step-git-clone', logs: 'clone logs' },
        { step: 'build-and-push', container: 'step-build', logs: 'build logs' },
        { step: 'push-image', container: 'step-push', logs: 'push logs' },
      ],
    },
  ],
}

describe('build explorer state', () => {
  it('selects the latest build when no id is requested', () => {
    expect(selectRequestedBuild([build(42), build(41)], undefined).build?.id).toBe(42)
  })

  it('rejects an id outside the application build list', () => {
    expect(selectRequestedBuild([build(42)], 99)).toEqual({
      build: undefined,
      invalidRequestedId: true,
    })
  })

  it('normalizes task steps into clone build and push order', () => {
    expect(normalizeBuildSteps(logDetails).map(step => step.id)).toEqual(['clone', 'build', 'push'])
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
