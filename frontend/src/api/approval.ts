import { client } from './client'
import type { Approval } from '../types'

export const approvalApi = {
  list: (projectId: number, params: {page:number;pageSize:number;status?:string;environment?:string}) =>
    client.get<never, {items:Approval[];page:number;pageSize:number;total:number}>(`/projects/${projectId}/approvals`, { params }),
  submit: (projectId: number, input: Record<string, unknown>) =>
    client.post<never, Approval>(`/projects/${projectId}/approvals`, input),
  approve: (projectId: number, id: number, comment?: string) =>
    client.post<never, Approval>(`/projects/${projectId}/approvals/${id}/approve`, { comment }),
  reject: (projectId: number, id: number, comment: string) =>
    client.post<never, Approval>(`/projects/${projectId}/approvals/${id}/reject`, { comment }),
}
