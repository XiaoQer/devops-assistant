import { defineStore } from 'pinia'
import { projectApi } from '../api/project'
import type { Project } from '../types'

const STORAGE_KEY = 'aegis.activeProjectId'

export const useProjectStore = defineStore('projects', {
  state: () => ({
    items: [] as Project[],
    loading: false,
    activeProjectId: 0,
  }),
  getters: {
    activeProject(state): Project | undefined {
      return state.items.find((item: Project) => item.id === state.activeProjectId)
    },
  },
  actions: {
    init() {
      const saved = Number(window.localStorage.getItem(STORAGE_KEY) || 0)
      this.activeProjectId = Number.isFinite(saved) ? saved : 0
    },
    setActiveProject(projectId: number) {
      this.activeProjectId = projectId
      window.localStorage.setItem(STORAGE_KEY, String(projectId || 0))
    },
    async load() {
      this.loading = true
      try {
        this.items = await projectApi.list()
        if (!this.activeProjectId && this.items.length) {
          this.setActiveProject(this.items[0].id)
        } else if (this.activeProjectId && !this.items.some((item: Project) => item.id === this.activeProjectId)) {
          this.setActiveProject(this.items[0]?.id || 0)
        }
      } finally {
        this.loading = false
      }
    },
  },
})

