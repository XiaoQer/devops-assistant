import { client } from './client'
import type { ProjectRuntimeOverview, RuntimeExecSession } from '../types'


const base = (projectId: number, applicationId: number, environment: string) => (
  `/projects/${projectId}/applications/${applicationId}/environments/${encodeURIComponent(environment)}/runtime`
)

export const runtimeApi = {
  overview: (projectId: number) =>
    client.get<never, ProjectRuntimeOverview>(`/projects/${projectId}/runtime`),
  deploymentYaml: (
    projectId: number, applicationId: number, environment: string, deployment: string,
  ) => client.get<Record<string, unknown>>(
    `${base(projectId, applicationId, environment)}/deployments/${encodeURIComponent(deployment)}/yaml`,
  ),
  restartDeployment: (
    projectId: number, applicationId: number, environment: string,
    deployment: string, reason?: string,
  ) => client.post(
    `${base(projectId, applicationId, environment)}/deployments/${encodeURIComponent(deployment)}/restart`,
    { confirmed: true, reason },
  ),
  podLogs: (
    projectId: number, applicationId: number, environment: string, pod: string, container?: string,
  ) => client.get<never, { logs: string }>(
    `/projects/${projectId}/applications/${applicationId}/runtime/pods/${encodeURIComponent(pod)}/logs`,
    { params: { environment, container } },
  ),
  podYaml: (
    projectId: number, applicationId: number, environment: string, pod: string,
  ) => client.get<Record<string, unknown>>(
    `/projects/${projectId}/applications/${applicationId}/runtime/pods/${encodeURIComponent(pod)}/yaml`,
    { params: { environment } },
  ),
  deletePod: (
    projectId: number, applicationId: number, environment: string, pod: string, reason?: string,
  ) => client.delete(
    `${base(projectId, applicationId, environment)}/pods/${encodeURIComponent(pod)}`,
    { data: { confirmed: true, reason } },
  ),
  createExecSession: (
    projectId: number, applicationId: number, environment: string,
    pod: string, container: string, reason: string,
  ) => client.post<never, RuntimeExecSession>(
    `${base(projectId, applicationId, environment)}/pods/${encodeURIComponent(pod)}/exec-sessions`,
    { confirmed: true, container, reason },
  ),
}
