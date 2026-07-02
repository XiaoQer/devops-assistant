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
  list: (projectId?: number) => client.get<never, Application[]>('/applications', {
    params: projectId ? { projectId } : undefined,
  }),
  get: (id: number) => client.get<never, Application>(`/applications/${id}`),
  create: (input: CreateApplicationInput) =>
    client.post<never, Application>('/applications', input),
  deployPlan: (
    id: number,
    options: { environment?: string; image_tag?: string; git_commit?: string } = {},
  ) => client.post<never, DeploymentPlan>(`/applications/${id}/deploy/plan`, options),
  deploy: (
    id: number,
    options: { environment?: string; image_tag?: string; git_commit?: string } = {},
  ) => client.post<never, Partial<Execution> & {
    approval_required?: boolean
    approval?: import('../types').Approval
  }>(`/applications/${id}/deploy`, options),
  executions: (id: number) =>
    client.get<never, Execution[]>(`/applications/${id}/executions`),
  releases: (id: number, environment?: string) =>
    client.get<never, Release[]>(`/applications/${id}/releases`, {
      params: { environment },
    }),
  rollback: (id: number, releaseId: number, environment = 'dev') =>
    client.post(`/applications/${id}/rollback`, {
      release_id: releaseId,
      environment,
    }),
  status: (id: number, environment = 'dev') =>
    client.get<never, RuntimeStatus>(`/applications/${id}/status`, {
      params: { environment },
    }),
  environments: (id: number) =>
    client.get<never, ApplicationEnvironment[]>(`/applications/${id}/environments`),
  createEnvironment: (id: number, input: Partial<ApplicationEnvironment>) =>
    client.post<never, ApplicationEnvironment>(`/applications/${id}/environments`, input),
  updateEnvironment: (id: number, envId: number, input: Partial<ApplicationEnvironment>) =>
    client.patch<never, ApplicationEnvironment>(`/applications/${id}/environments/${envId}`, input),
  deleteEnvironment: (id: number, envId: number) =>
    client.delete(`/applications/${id}/environments/${envId}`),
  cloneEnvironment: (id: number, envId: number, environmentName: string) =>
    client.post<never, ApplicationEnvironment>(`/applications/${id}/environments/${envId}/clone`, { environment_name: environmentName }),
  compareEnvironments: (id: number, left: number, right: number) =>
    client.get<never, Array<{field:string;left:unknown;right:unknown;changed:boolean}>>(`/applications/${id}/environments/compare`, { params: { left, right } }),
  configs: (id: number, environmentId: number, type?: string) =>
    client.get<never, ApplicationConfig[]>(`/applications/${id}/configs`, { params: { environmentId, type } }),
  saveConfig: (id: number, input: Record<string, unknown>) =>
    client.post<never, ApplicationConfig>(`/applications/${id}/configs`, input),
  updateConfig: (configId: number, input: Record<string, unknown>) =>
    client.patch<never, ApplicationConfig>(`/configs/${configId}`, input),
  deleteConfig: (configId: number) => client.delete(`/configs/${configId}`),
  podLogs: (id: number, pod: string, environment: string) =>
    client.get<never, {logs:string}>(`/applications/${id}/runtime/pods/${pod}/logs`, { params: { environment } }),
  podYaml: (id: number, pod: string, environment: string) =>
    client.get<Record<string, unknown>>(`/applications/${id}/runtime/pods/${pod}/yaml`, { params: { environment } }),
}
