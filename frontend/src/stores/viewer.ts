import { defineStore } from 'pinia'
import { VIEWER_EMAIL_STORAGE_KEY, VIEWER_NAME_STORAGE_KEY, readViewerIdentity } from '../constants/viewer'

export const useViewerStore = defineStore('viewer', {
  state: () => ({
    email: '',
    name: '',
  }),
  getters: {
    configured: state => Boolean(state.email),
    initials: state => {
      if (state.name) {
        return state.name
          .split(/\s+/)
          .filter(Boolean)
          .slice(0, 2)
          .map(part => part[0]?.toUpperCase())
          .join('')
      }
      return (state.email.slice(0, 2) || 'ME').toUpperCase()
    },
    displayName: state => state.name || state.email || 'Portal viewer',
  },
  actions: {
    init() {
      const identity = readViewerIdentity()
      this.email = identity.email
      this.name = identity.name
    },
    setIdentity(payload: { email?: string; name?: string }) {
      this.email = String(payload.email || '').trim().toLowerCase()
      this.name = String(payload.name || '').trim()

      if (typeof window === 'undefined') return

      if (this.email) window.localStorage.setItem(VIEWER_EMAIL_STORAGE_KEY, this.email)
      else window.localStorage.removeItem(VIEWER_EMAIL_STORAGE_KEY)

      if (this.name) window.localStorage.setItem(VIEWER_NAME_STORAGE_KEY, this.name)
      else window.localStorage.removeItem(VIEWER_NAME_STORAGE_KEY)
    },
    clear() {
      this.setIdentity({ email: '', name: '' })
    },
  },
})

