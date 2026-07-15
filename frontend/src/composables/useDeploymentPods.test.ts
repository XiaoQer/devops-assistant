import { watchEffect } from 'vue'
import { describe, expect, it, vi } from 'vitest'
import { useDeploymentPods } from './useDeploymentPods'

const target = { key: '8:payments', applicationId: 8, deployment: 'payments' }
const pods = [{
  name: 'payments-a', status: 'Running', ready: true, restart_count: 0,
  node: 'worker-1', containers: ['api'], created_at: '2026-07-15T00:00:00Z',
}]

describe('useDeploymentPods', () => {
  it('loads once and reuses the row cache', async () => {
    const loader = vi.fn().mockResolvedValue(pods)
    const state = useDeploymentPods(loader)

    await state.load(target)
    await state.load(target)

    expect(loader).toHaveBeenCalledTimes(1)
    expect(state.entries[target.key].pods).toEqual(pods)
  })

  it('publishes loading and completion through the reactive entry', async () => {
    let resolve: (value: typeof pods) => void = () => undefined
    const loader = vi.fn(() => new Promise<typeof pods>(done => { resolve = done }))
    const state = useDeploymentPods(loader)
    const observed: string[] = []
    const stop = watchEffect(() => {
      const entry = state.entries[target.key]
      observed.push(entry ? `${entry.loading}:${entry.loaded}:${entry.pods.length}` : 'missing')
    }, { flush: 'sync' })

    const pending = state.load(target)
    resolve(pods)
    await pending

    expect(observed).toContain('true:false:0')
    expect(observed[observed.length - 1]).toBe('false:true:1')
    stop()
  })

  it('keeps errors row-local and retries only that row', async () => {
    const loader = vi.fn()
      .mockRejectedValueOnce(new Error('cluster unavailable'))
      .mockResolvedValueOnce(pods)
    const state = useDeploymentPods(loader)

    await state.load(target)
    expect(state.entries[target.key].error).toBe('cluster unavailable')
    await state.retry(target)

    expect(loader).toHaveBeenCalledTimes(2)
    expect(state.entries[target.key].pods).toEqual(pods)
    expect(state.entries[target.key].error).toBe('')
  })

  it('clears cached rows when the inventory context changes', async () => {
    const state = useDeploymentPods(vi.fn().mockResolvedValue(pods))
    await state.load(target)

    state.clear()

    expect(Object.keys(state.entries)).toEqual([])
  })
})
