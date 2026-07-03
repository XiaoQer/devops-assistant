import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login as loginRequest, logout as logoutRequest, me } from '../api/auth'
import { advanceAuthEpoch, ApiClientError, setCsrfToken } from '../api/client'
import type { AuthenticatedUser, AuthResponse } from '../types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthenticatedUser>()
  const initialized = ref(false)
  let initializationPromise: Promise<void> | undefined
  let generation = 0

  const apply = (data: AuthResponse) => {
    user.value = data.user
    setCsrfToken(data.csrf_token)
  }

  const applyAnonymous = () => {
    user.value = undefined
    setCsrfToken()
  }

  const beginIdentityTransition = () => {
    generation += 1
    advanceAuthEpoch()
    return generation
  }

  const clear = () => {
    beginIdentityTransition()
    applyAnonymous()
    initialized.value = true
  }

  const initialize = async () => {
    if (initialized.value) return
    if (initializationPromise) return initializationPromise

    const initializationGeneration = generation
    const pending = (async () => {
      try {
        const data = await me()
        if (generation !== initializationGeneration) return
        apply(data)
        initialized.value = true
      } catch (error) {
        if (generation !== initializationGeneration) return
        if (error instanceof ApiClientError && error.status === 401) {
          applyAnonymous()
          initialized.value = true
          return
        }
        throw error
      }
    })()
    initializationPromise = pending
    try {
      return await pending
    } finally {
      if (initializationPromise === pending) {
        initializationPromise = undefined
      }
    }
  }

  const login = async (username: string, password: string) => {
    const loginGeneration = beginIdentityTransition()
    const data = await loginRequest(username, password)
    if (generation === loginGeneration) {
      apply(data)
      initialized.value = true
    }
    return data
  }

  const logout = async () => {
    const logoutGeneration = beginIdentityTransition()
    try {
      await logoutRequest()
      if (generation === logoutGeneration) {
        applyAnonymous()
        initialized.value = true
      }
    } catch (error) {
      if (error instanceof ApiClientError && error.status === 401) {
        if (generation === logoutGeneration) {
          applyAnonymous()
          initialized.value = true
        }
        return
      }
      throw error
    }
  }

  return { user, initialized, apply, initialize, login, logout, clear }
})
