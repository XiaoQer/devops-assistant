import { client } from './client'
import type { AuthResponse } from '../types'

export const login = (username: string, password: string) =>
  client.post<never, AuthResponse>('/auth/login', { username, password })

export const me = () => client.get<never, AuthResponse>('/auth/me')

export const logout = () => client.post<never, void>('/auth/logout')
