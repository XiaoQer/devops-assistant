import { defineStore } from 'pinia'
import { applicationApi } from '../api/application'
import type { Application } from '../types'

export const useApplicationStore = defineStore('applications', {
  state: () => ({ items: [] as Application[], loading: false }),
  actions: {
    async load() {
      this.loading = true
      try { this.items = await applicationApi.list() }
      finally { this.loading = false }
    },
  },
})

