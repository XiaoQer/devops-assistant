import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login as loginRequest, logout as logoutRequest, me } from '../api/auth'
import { setCsrfToken } from '../api/client'
import type { AuthenticatedUser, AuthResponse } from '../types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthenticatedUser>()
  const initialized = ref(false)
  let initializationPromise: Promise<void> | undefined

  const apply = (data?: AuthResponse) => {
    user.value = data?.user
    setCsrfToken(data?.csrf_token)
  }

  const clear = () => {
    apply()
  }

  const initialize = async () => {
    if (initialized.value) return
    if (initializationPromise) return initializationPromise

    initializationPromise = (async () => {
      try {
        apply(await me())
      } catch {
        clear()
      } finally {
        initialized.value = true
      }
    })()

    return initializationPromise
  }

  const login = async (username: string, password: string) => {
    const data = await loginRequest(username, password)
    apply(data)
    return data
  }

  const logout = async () => {
    try {
      await logoutRequest()
    } finally {
      clear()
    }
  }

  return { user, initialized, apply, initialize, login, logout, clear }
})
