import { effectScope, nextTick } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { overview } = vi.hoisted(() => ({ overview: vi.fn() }))
vi.mock('../api/runtime', () => ({ runtimeApi: { overview } }))

import { useProjectRuntime } from './useProjectRuntime'

const data = {
  summary: {
    environments: 2,
    deployments: 2,
    healthy_pods: 1,
    unhealthy_pods: 1,
    restart_count: 3,
  },
  environments: [
    {
      name: 'dev', display_name: 'Development', cluster_name: 'dev-cluster',
      applications: [{
        application_id: 1, application_name: 'payments-api', namespace: 'payments-dev',
        status: 'Healthy', deployment: { name: 'payments-api', replicas: 1, ready_replicas: 1,
          updated_replicas: 1, available_replicas: 1, images: ['api:v1'] }, pods: [],
      }],
    },
    {
      name: 'prod', display_name: 'Production', cluster_name: 'prod-cluster',
      applications: [{
        application_id: 2, application_name: 'billing-worker', namespace: 'billing-prod',
        status: 'Degraded', deployment: { name: 'billing-worker', replicas: 2, ready_replicas: 1,
          updated_replicas: 2, available_replicas: 1, images: ['worker:v2'] }, pods: [],
      }],
    },
  ],
  refreshed_at: '2026-07-15T00:00:00Z',
}

describe('useProjectRuntime', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()
    vi.stubGlobal('document', { hidden: false })
    overview.mockResolvedValue(data)
  })

  it('filters by environment, health, and keyword', async () => {
    const scope = effectScope()
    const state = scope.run(() => useProjectRuntime(7))!
    await state.refresh()
    state.environment.value = 'prod'
    state.status.value = 'Degraded'
    state.query.value = 'billing'
    await nextTick()

    expect(state.filteredEnvironments.value).toHaveLength(1)
    expect(state.filteredEnvironments.value[0].applications[0].application_name)
      .toBe('billing-worker')
    scope.stop()
  })

  it('refreshes every 30 seconds, pauses when hidden, and preserves last data on error', async () => {
    const scope = effectScope()
    const state = scope.run(() => useProjectRuntime(7))!
    await state.refresh()
    expect(state.overview.value).toEqual(data)

    await vi.advanceTimersByTimeAsync(30_000)
    expect(overview).toHaveBeenCalledTimes(2)

    ;(document as { hidden: boolean }).hidden = true
    await vi.advanceTimersByTimeAsync(30_000)
    expect(overview).toHaveBeenCalledTimes(2)

    ;(document as { hidden: boolean }).hidden = false
    overview.mockRejectedValueOnce(new Error('cluster unavailable'))
    await state.refresh()
    expect(state.overview.value).toEqual(data)
    expect(state.refreshError.value).toBe('cluster unavailable')
    scope.stop()
  })
})
