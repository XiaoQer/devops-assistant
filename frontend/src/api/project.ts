import { client } from './client'
import type {
  Application,
  ClusterConnectionResult,
  ClusterPayload,
  ContainerRegistry,
  KubernetesCluster,
  Project,
  ProjectMember,
  RegistryConnectionResult,
  RegistryPayload,
} from '../types'

export interface ProjectPayload {
  key?: string
  name?: string
  description?: string
  status?: string
  business_owner?: string
  billing_owner?: string
  github_group?: string
  github_default_visibility?: string
  aliyun_account_id?: string
  aliyun_resource_group_id?: string
  aliyun_region?: string
  aliyun_vpc_id?: string
  aliyun_binding_status?: string
  owner_name?: string
  owner_email?: string
  owner_title?: string
}

export const projectApi = {
  list: () => client.get<never, Project[]>('/projects'),
  get: (id: number) => client.get<never, Project>(`/projects/${id}`),
  create: (input: ProjectPayload & { key: string; name: string }) =>
    client.post<never, Project>('/projects', input),
  update: (id: number, input: ProjectPayload) =>
    client.patch<never, Project>(`/projects/${id}`, input),
  remove: (id: number) => client.delete(`/projects/${id}`),
  members: (projectId: number) =>
    client.get<never, ProjectMember[]>(`/projects/${projectId}/members`),
  addMember: (projectId: number, input: Partial<ProjectMember>) =>
    client.post<never, ProjectMember>(`/projects/${projectId}/members`, input),
  updateMember: (projectId: number, memberId: number, input: Partial<ProjectMember>) =>
    client.patch<never, ProjectMember>(`/projects/${projectId}/members/${memberId}`, input),
  removeMember: (projectId: number, memberId: number) =>
    client.delete(`/projects/${projectId}/members/${memberId}`),
  clusters: (projectId: number) =>
    client.get<never, KubernetesCluster[]>(`/projects/${projectId}/clusters`),
  addCluster: (projectId: number, input: ClusterPayload) =>
    client.post<never, KubernetesCluster>(`/projects/${projectId}/clusters`, input),
  updateCluster: (projectId: number, clusterId: number, input: Partial<ClusterPayload>) =>
    client.patch<never, KubernetesCluster>(`/projects/${projectId}/clusters/${clusterId}`, input),
  removeCluster: (projectId: number, clusterId: number) =>
    client.delete(`/projects/${projectId}/clusters/${clusterId}`),
  setDefaultCluster: (projectId: number, clusterId: number) =>
    client.post<never, KubernetesCluster>(`/projects/${projectId}/clusters/${clusterId}/default`),
  testClusterConnection: (
    projectId: number,
    input: Pick<ClusterPayload, 'kubeconfig' | 'kube_context'>,
  ) => client.post<never, ClusterConnectionResult>(
    `/projects/${projectId}/clusters/test-connection`, input,
  ),
  testSavedClusterConnection: (projectId: number, clusterId: number) =>
    client.post<never, ClusterConnectionResult>(
      `/projects/${projectId}/clusters/${clusterId}/test-connection`,
    ),
  applications: (projectId: number) =>
    client.get<never, Application[]>('/applications', { params: { projectId } }),
  registries: (projectId: number) =>
    client.get<never, ContainerRegistry[]>(`/projects/${projectId}/registries`),
  addRegistry: (projectId: number, input: RegistryPayload) =>
    client.post<never, ContainerRegistry>(`/projects/${projectId}/registries`, input),
  updateRegistry: (
    projectId: number,
    registryId: number,
    input: Partial<RegistryPayload>,
  ) => client.patch<never, ContainerRegistry>(
    `/projects/${projectId}/registries/${registryId}`,
    input,
  ),
  removeRegistry: (projectId: number, registryId: number) =>
    client.delete(`/projects/${projectId}/registries/${registryId}`),
  setDefaultRegistry: (projectId: number, registryId: number) =>
    client.post<never, ContainerRegistry>(
      `/projects/${projectId}/registries/${registryId}/default`,
    ),
  testRegistryConnection: (
    projectId: number,
    input: Pick<RegistryPayload, 'server' | 'username' | 'password' | 'skip_tls_verify'>,
  ) => client.post<never, RegistryConnectionResult>(
    `/projects/${projectId}/registries/test-connection`,
    input,
  ),
  testSavedRegistryConnection: (
    projectId: number,
    registryId: number,
    input?: Partial<RegistryPayload>,
  ) => client.post<never, RegistryConnectionResult>(
    `/projects/${projectId}/registries/${registryId}/test-connection`,
    input,
  ),
}
