import { client } from './client'

export const pipelineApi = {
  list: (params: {page:number;pageSize:number;status?:string;query?:string}) =>
    client.get<never, {
      items:Array<{
        name:string;namespace:string;application?:string;pipeline?:string
        status:string;reason:string;repo_url?:string;branch?:string;image?:string
        started_at?:string;finished_at?:string;created_at:string
      }>
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
}
