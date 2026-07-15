import { beforeEach, describe, expect, it, vi } from 'vitest'

const { client } = vi.hoisted(() => ({
  client: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}))

vi.mock('./client', () => ({ client }))

import { runtimeApi } from './runtime'

describe('runtimeApi', () => {
  beforeEach(() => vi.clearAllMocks())

  it('uses Project-scoped overview and resource URLs', async () => {
    client.get.mockResolvedValue({})

    await runtimeApi.overview(7)
    await runtimeApi.deploymentYaml(7, 8, 'prod', 'payments')
    await runtimeApi.podYaml(7, 8, 'prod', 'payments-a')

    expect(client.get).toHaveBeenNthCalledWith(1, '/projects/7/runtime')
    expect(client.get).toHaveBeenNthCalledWith(
      2,
      '/projects/7/applications/8/environments/prod/runtime/deployments/payments/yaml',
    )
    expect(client.get).toHaveBeenNthCalledWith(
      3,
      '/projects/7/applications/8/runtime/pods/payments-a/yaml',
      { params: { environment: 'prod' } },
    )
  })

  it('sends explicit confirmation for mutations and exec sessions', async () => {
    client.post.mockResolvedValue({})
    client.delete.mockResolvedValue({})

    await runtimeApi.restartDeployment(7, 8, 'prod', 'payments', 'incident recovery')
    await runtimeApi.deletePod(7, 8, 'prod', 'payments-a', 'replace unhealthy pod')
    await runtimeApi.createExecSession(
      7, 8, 'prod', 'payments-a', 'api', 'inspect production process',
    )

    expect(client.post).toHaveBeenNthCalledWith(
      1,
      '/projects/7/applications/8/environments/prod/runtime/deployments/payments/restart',
      { confirmed: true, reason: 'incident recovery' },
    )
    expect(client.delete).toHaveBeenCalledWith(
      '/projects/7/applications/8/environments/prod/runtime/pods/payments-a',
      { data: { confirmed: true, reason: 'replace unhealthy pod' } },
    )
    expect(client.post).toHaveBeenNthCalledWith(
      2,
      '/projects/7/applications/8/environments/prod/runtime/pods/payments-a/exec-sessions',
      { confirmed: true, container: 'api', reason: 'inspect production process' },
    )
  })
})
