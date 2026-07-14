import { client } from './client'
import type { PipelineRunSummary } from '../types'

export const pipelineApi = {
  list: (projectId: number, params: {page:number;pageSize:number;status?:string;query?:string}) =>
    client.get<never, {
      items:PipelineRunSummary[]
      page:number;pageSize:number;total:number
    }>(`/projects/${projectId}/pipelines`, { params }),
  status: (projectId: number, name: string) =>
    client.get(`/projects/${projectId}/pipelines/${name}/status`),
  logs: (projectId: number, name: string) =>
    client.get<never, {
      pipeline_run: string
      status: string
      reason: string
      message?: string
      started_at?: string
      finished_at?: string
      logs: string
      tasks: Array<{
        name: string
        task_name: string
        status: string
        pod?: string
        steps: Array<{ step: string; container: string; logs: string }>
      }>
    }>(`/projects/${projectId}/pipelines/${name}/logs`),
  retry: (projectId: number, name: string) =>
    client.post<never, { name: string; retried_from: string }>(`/projects/${projectId}/pipelines/${name}/retry`),
}
