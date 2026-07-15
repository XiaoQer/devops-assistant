import { effectScope, nextTick } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { environments, inventory } = vi.hoisted(() => ({
  environments: vi.fn(), inventory: vi.fn(),
}))
vi.mock('../api/runtime', () => ({ runtimeApi: { environments, inventory } }))

import { useProjectRuntime } from './useProjectRuntime'

const data = {
  environment: { name: 'prod', display_name: 'Production', cluster_name: 'prod-cluster' },
  summary: {
    deployments: 2,
    healthy_pods: 1,
    unhealthy_pods: 1,
    restart_count: 3,
  },
  items: [],
  pagination: { page: 1, page_size: 20, total: 0, pages: 0 },
  refreshed_at: '2026-07-15T00:00:00Z',
}

const route = { query: { environment: 'prod', resource: 'pods', page: '2' } } as never
const router = { replace: vi.fn() }

describe('useProjectRuntime', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()
    vi.stubGlobal('document', { hidden: false })
    environments.mockResolvedValue([
      { name: 'dev', display_name: 'Development', cluster_name: 'dev-cluster' },
      { name: 'prod', display_name: 'Production', cluster_name: 'prod-cluster' },
    ])
    inventory.mockResolvedValue(data)
  })

  it('loads the selected environment and server-paginated resource from the URL', async () => {
    const scope = effectScope()
    const state = scope.run(() => useProjectRuntime(7, route, router as never))!
    await state.initialize()

    expect(inventory).toHaveBeenCalledWith(7, expect.objectContaining({
      environment: 'prod', resource: 'pods', page: 2, page_size: 20,
    }))
    expect(state.inventory.value).toEqual(data)
    scope.stop()
  })

  it('debounces search, resets pagination, and writes filters to the URL', async () => {
    const scope = effectScope()
    const state = scope.run(() => useProjectRuntime(7, route, router as never))!
    await state.initialize()
    inventory.mockClear()
    state.query.value = 'billing'
    await nextTick()
    expect(inventory).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(300)
    expect(state.page.value).toBe(1)
    expect(inventory).toHaveBeenCalledTimes(1)
    expect(router.replace).toHaveBeenLastCalledWith({ query: expect.objectContaining({
      environment: 'prod', resource: 'pods', query: 'billing',
    }) })
    scope.stop()
  })

  it('refreshes every 30 seconds, pauses when hidden, and preserves last data on error', async () => {
    const scope = effectScope()
    const state = scope.run(() => useProjectRuntime(7, route, router as never))!
    await state.initialize()
    expect(state.inventory.value).toEqual(data)

    await vi.advanceTimersByTimeAsync(30_000)
    expect(inventory).toHaveBeenCalledTimes(2)

    ;(document as { hidden: boolean }).hidden = true
    await vi.advanceTimersByTimeAsync(30_000)
    expect(inventory).toHaveBeenCalledTimes(2)

    ;(document as { hidden: boolean }).hidden = false
    inventory.mockRejectedValueOnce(new Error('cluster unavailable'))
    await state.refresh()
    expect(state.inventory.value).toEqual(data)
    expect(state.refreshError.value).toBe('cluster unavailable')
    scope.stop()
  })
})
