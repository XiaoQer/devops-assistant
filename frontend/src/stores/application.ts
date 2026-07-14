import { defineStore } from 'pinia'
import { applicationApi } from '../api/application'
import type { Application } from '../types'
import { useProjectStore } from './project'

export const useApplicationStore = defineStore('applications', {
  state: () => ({ items: [] as Application[], loading: false }),
  actions: {
    async load(projectId?: number) {
      const projectStore = useProjectStore()
      this.loading = true
      try {
        const activeProjectId = projectId ?? projectStore.activeProjectId
        this.items = activeProjectId ? await applicationApi.list(activeProjectId) : []
      }
      finally { this.loading = false }
    },
  },
})
