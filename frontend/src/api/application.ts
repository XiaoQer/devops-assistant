import { client } from './client'
import type {
  Application, Execution, Release, RuntimeStatus,
  ApplicationEnvironment, ApplicationConfig, DeploymentPlan,
} from '../types'

export interface CreateApplicationInput {
  project_id: number
  name: string
  repo_url: string
  branch: string
  namespace: string
}

export const applicationApi = {
  list: (projectId: number) => client.get<never, Application[]>(`/projects/${projectId}/applications`),
  get: (projectId: number, id: number) => client.get<never, Application>(`/projects/${projectId}/applications/${id}`),
  create: (projectId: number, input: Omit<CreateApplicationInput, 'project_id'>) =>
    client.post<never, Application>(`/projects/${projectId}/applications`, input),
  deployPlan: (
    projectId: number, id: number,
    options: { environment?: string; image_tag?: string; git_commit?: string } = {},
  ) => client.post<never, DeploymentPlan>(`/projects/${projectId}/applications/${id}/deploy/plan`, options),
  deploy: (
    projectId: number, id: number,
    options: { environment?: string; image_tag?: string; git_commit?: string } = {},
  ) => client.post<never, Partial<Execution> & {
    approval_required?: boolean
    approval?: import('../types').Approval
  }>(`/projects/${projectId}/applications/${id}/deploy`, options),
  executions: (projectId: number, id: number) =>
    client.get<never, Execution[]>(`/projects/${projectId}/applications/${id}/executions`),
  releases: (projectId: number, id: number, environment?: string) =>
    client.get<never, Release[]>(`/projects/${projectId}/applications/${id}/releases`, {
      params: { environment },
    }),
  rollback: (projectId: number, id: number, releaseId: number, environment = 'dev') =>
    client.post(`/projects/${projectId}/applications/${id}/rollback`, {
      release_id: releaseId,
      environment,
    }),
  status: (projectId: number, id: number, environment = 'dev') =>
    client.get<never, RuntimeStatus>(`/projects/${projectId}/applications/${id}/status`, {
      params: { environment },
    }),
  environments: (projectId: number, id: number) =>
    client.get<never, ApplicationEnvironment[]>(`/projects/${projectId}/applications/${id}/environments`),
  createEnvironment: (projectId: number, id: number, input: Partial<ApplicationEnvironment>) =>
    client.post<never, ApplicationEnvironment>(`/projects/${projectId}/applications/${id}/environments`, input),
  updateEnvironment: (projectId: number, id: number, envId: number, input: Partial<ApplicationEnvironment>) =>
    client.patch<never, ApplicationEnvironment>(`/projects/${projectId}/applications/${id}/environments/${envId}`, input),
  deleteEnvironment: (projectId: number, id: number, envId: number) =>
    client.delete(`/projects/${projectId}/applications/${id}/environments/${envId}`),
  cloneEnvironment: (projectId: number, id: number, envId: number, environmentName: string) =>
    client.post<never, ApplicationEnvironment>(`/projects/${projectId}/applications/${id}/environments/${envId}/clone`, { environment_name: environmentName }),
  compareEnvironments: (projectId: number, id: number, left: number, right: number) =>
    client.get<never, Array<{field:string;left:unknown;right:unknown;changed:boolean}>>(`/projects/${projectId}/applications/${id}/environments/compare`, { params: { left, right } }),
  configs: (projectId: number, id: number, environmentId: number, type?: string) =>
    client.get<never, ApplicationConfig[]>(`/projects/${projectId}/applications/${id}/configs`, { params: { environmentId, type } }),
  saveConfig: (projectId: number, id: number, input: Record<string, unknown>) =>
    client.post<never, ApplicationConfig>(`/projects/${projectId}/applications/${id}/configs`, input),
  updateConfig: (projectId: number, configId: number, input: Record<string, unknown>) =>
    client.patch<never, ApplicationConfig>(`/projects/${projectId}/configs/${configId}`, input),
  deleteConfig: (projectId: number, configId: number) => client.delete(`/projects/${projectId}/configs/${configId}`),
  podLogs: (projectId: number, id: number, pod: string, environment: string) =>
    client.get<never, {logs:string}>(`/projects/${projectId}/applications/${id}/runtime/pods/${pod}/logs`, { params: { environment } }),
  podYaml: (projectId: number, id: number, pod: string, environment: string) =>
    client.get<Record<string, unknown>>(`/projects/${projectId}/applications/${id}/runtime/pods/${pod}/yaml`, { params: { environment } }),
}
