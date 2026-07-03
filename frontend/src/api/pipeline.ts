import { client } from './client'
import type { PipelineRunSummary } from '../types'

export const pipelineApi = {
  list: (params: {page:number;pageSize:number;status?:string;query?:string;projectId?:number}) =>
    client.get<never, {
      items:PipelineRunSummary[]
      page:number;pageSize:number;total:number
    }>('/pipelines', { params }),
  status: (name: string, namespace = 'devops-platform') =>
    client.get(`/pipelines/${name}/status`, { params: { namespace } }),
  logs: (name: string, namespace = 'devops-platform') =>
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
    }>(`/pipelines/${name}/logs`, {
      params: { namespace },
    }),
  retry: (name: string, namespace = 'devops-platform') =>
    client.post<never, { name: string; retried_from: string }>(`/pipelines/${name}/retry`, {}, {
      params: { namespace },
    }),
}
