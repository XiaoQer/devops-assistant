import { client } from './client'
import type { Approval } from '../types'

export const approvalApi = {
  list: (params: {page:number;pageSize:number;status?:string;environment?:string}) =>
    client.get<never, {items:Approval[];page:number;pageSize:number;total:number}>('/approvals', { params }),
  submit: (input: Record<string, unknown>) =>
    client.post<never, Approval>('/approvals', input),
  approve: (id: number, comment?: string) =>
    client.post<never, Approval>(`/approvals/${id}/approve`, { comment }),
  reject: (id: number, comment: string) =>
    client.post<never, Approval>(`/approvals/${id}/reject`, { comment }),
}

