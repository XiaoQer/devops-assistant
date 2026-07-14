import { client } from './client'
import type { Release } from '../types'

export const releaseApi = {
  list: (projectId: number, params: {page:number;pageSize:number;environment?:string;status?:string}) =>
    client.get<never, {items:Release[];page:number;pageSize:number;total:number}>(`/projects/${projectId}/releases`, { params }),
}
