import { client } from './client'
import type { Application, ContainerRegistry, KubernetesCluster, Project, ProjectMember } from '../types'

export const projectApi = {
  list: () => client.get<never, Project[]>('/projects'),
  get: (id: number) => client.get<never, Project>(`/projects/${id}`),
  create: (input: {
    key: string
    name: string
    description?: string
    owner_name?: string
    owner_email?: string
    owner_title?: string
  }) => client.post<never, Project>('/projects', input),
  update: (id: number, input: Partial<Pick<Project, 'name' | 'description'>>) =>
    client.patch<never, Project>(`/projects/${id}`, input),
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
  addCluster: (projectId: number, input: Partial<KubernetesCluster>) =>
    client.post<never, KubernetesCluster>(`/projects/${projectId}/clusters`, input),
  updateCluster: (projectId: number, clusterId: number, input: Partial<KubernetesCluster>) =>
    client.patch<never, KubernetesCluster>(`/projects/${projectId}/clusters/${clusterId}`, input),
  removeCluster: (projectId: number, clusterId: number) =>
    client.delete(`/projects/${projectId}/clusters/${clusterId}`),
  setDefaultCluster: (projectId: number, clusterId: number) =>
    client.post<never, KubernetesCluster>(`/projects/${projectId}/clusters/${clusterId}/default`),
  applications: (projectId: number) =>
    client.get<never, Application[]>('/applications', { params: { projectId } }),
  registries: (projectId: number) =>
    client.get<never, ContainerRegistry[]>('/registries', { params: { projectId } }),
}

