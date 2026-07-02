import { client } from './client'
import type { ContainerRegistry } from '../types'

export type RegistryInput = Omit<
  ContainerRegistry,
  'id' | 'provider' | 'image_prefix' | 'has_credentials' | 'created_at' | 'updated_at' | 'project_name'
> & {
  provider: string
  password?: string
}

export const registryApi = {
  list: (projectId?: number) => client.get<never, ContainerRegistry[]>('/registries', {
    params: projectId ? { projectId } : undefined,
  }),
  create: (input: Partial<RegistryInput>) =>
    client.post<never, ContainerRegistry>('/registries', input),
  update: (id: number, input: Partial<RegistryInput>) =>
    client.patch<never, ContainerRegistry>(`/registries/${id}`, input),
  remove: (id: number) => client.delete(`/registries/${id}`),
  setDefault: (id: number) =>
    client.post<never, ContainerRegistry>(`/registries/${id}/default`),
}
