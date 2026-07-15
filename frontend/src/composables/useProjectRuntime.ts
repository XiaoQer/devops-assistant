import { computed, onScopeDispose, ref } from 'vue'
import { runtimeApi } from '../api/runtime'
import type { ProjectRuntimeOverview } from '../types'


export function useProjectRuntime(projectId: number) {
  const overview = ref<ProjectRuntimeOverview>()
  const loading = ref(false)
  const refreshError = ref('')
  const query = ref('')
  const environment = ref('')
  const status = ref('')
  const autoRefresh = ref(true)

  const filteredEnvironments = computed(() => {
    const needle = query.value.trim().toLowerCase()
    return (overview.value?.environments || []).flatMap(group => {
      if (environment.value && group.name !== environment.value) return []
      const applications = group.applications.filter(item => {
        if (status.value && item.status !== status.value) return false
        if (!needle) return true
        const searchable = [
          item.application_name,
          item.namespace,
          item.deployment?.name,
          ...(item.deployment?.images || []),
          ...item.pods.map(pod => `${pod.name} ${pod.node || ''}`),
        ].join(' ').toLowerCase()
        return searchable.includes(needle)
      })
      return applications.length ? [{ ...group, applications }] : []
    })
  })

  async function refresh() {
    loading.value = true
    try {
      overview.value = await runtimeApi.overview(projectId)
      refreshError.value = ''
    } catch (error) {
      refreshError.value = error instanceof Error ? error.message : 'Runtime 刷新失败'
    } finally {
      loading.value = false
    }
  }

  const timer = setInterval(() => {
    if (autoRefresh.value && (typeof document === 'undefined' || !document.hidden)) {
      void refresh()
    }
  }, 30_000)
  onScopeDispose(() => clearInterval(timer))

  return {
    overview,
    loading,
    refreshError,
    query,
    environment,
    status,
    autoRefresh,
    filteredEnvironments,
    refresh,
  }
}
