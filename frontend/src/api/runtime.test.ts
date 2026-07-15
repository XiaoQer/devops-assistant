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

  it('uses Project-scoped environment directory, paginated inventory, and resource URLs', async () => {
    client.get.mockResolvedValue({})

    await runtimeApi.environments(7)
    await runtimeApi.inventory(7, {
      environment: 'prod', resource: 'pods', page: 2, page_size: 50,
      query: 'payments', status: 'Healthy',
    })
    await runtimeApi.podDetail(7, 8, 'prod', 'payments-a')
    await runtimeApi.deploymentPods(7, 8, 'prod', 'payments')
    await runtimeApi.deploymentYaml(7, 8, 'prod', 'payments')
    await runtimeApi.podYaml(7, 8, 'prod', 'payments-a')

    expect(client.get).toHaveBeenNthCalledWith(1, '/projects/7/runtime/environments')
    expect(client.get).toHaveBeenNthCalledWith(
      2,
      '/projects/7/runtime',
      { params: {
        environment: 'prod', resource: 'pods', page: 2, page_size: 50,
        query: 'payments', status: 'Healthy',
      } },
    )
    expect(client.get).toHaveBeenNthCalledWith(
      3,
      '/projects/7/applications/8/environments/prod/runtime/pods/payments-a',
    )
    expect(client.get).toHaveBeenNthCalledWith(
      4,
      '/projects/7/applications/8/environments/prod/runtime/deployments/payments/pods',
    )
    expect(client.get).toHaveBeenNthCalledWith(
      5,
      '/projects/7/applications/8/environments/prod/runtime/deployments/payments/yaml',
    )
    expect(client.get).toHaveBeenNthCalledWith(
      6,
      '/projects/7/applications/8/runtime/pods/payments-a/yaml',
      { params: { environment: 'prod' } },
    )
  })

  it('passes selected container and bounded log tail to the Pod log endpoint', async () => {
    client.get.mockResolvedValue({})

    await runtimeApi.podLogs(7, 8, 'prod', 'payments-a', 'api', 1000)

    expect(client.get).toHaveBeenCalledWith(
      '/projects/7/applications/8/runtime/pods/payments-a/logs',
      { params: { environment: 'prod', container: 'api', tail: 1000 } },
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
