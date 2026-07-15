import { onScopeDispose, ref, watch } from 'vue'
import type { RouteLocationNormalizedLoaded, Router } from 'vue-router'
import { runtimeApi } from '../api/runtime'
import type { RuntimeEnvironmentOption, RuntimeInventory } from '../types'

export function useProjectRuntime(projectId: number, route: RouteLocationNormalizedLoaded, router: Router) {
  const environments = ref<RuntimeEnvironmentOption[]>([])
  const inventory = ref<RuntimeInventory>()
  const environment = ref(String(route.query.environment || ''))
  const query = ref(String(route.query.query || ''))
  const status = ref(String(route.query.status || ''))
  const page = ref(Math.max(1, Number(route.query.page) || 1))
  const pageSize = ref([20, 50, 100].includes(Number(route.query.page_size)) ? Number(route.query.page_size) : 20)
  const loading = ref(false)
  const refreshError = ref('')
  const autoRefresh = ref(true)

  function syncUrl() {
    void router.replace({ query: {
      environment: environment.value,
      ...(query.value ? { query: query.value } : {}),
      ...(status.value ? { status: status.value } : {}),
      ...(page.value > 1 ? { page: String(page.value) } : {}),
      ...(pageSize.value !== 20 ? { page_size: String(pageSize.value) } : {}),
    } })
  }

  async function loadEnvironments() {
    environments.value = await runtimeApi.environments(projectId)
    if (!environments.value.some(item => item.name === environment.value)) {
      environment.value = environments.value[0]?.name || ''
    }
    syncUrl()
  }

  async function refresh() {
    if (!environment.value) return
    loading.value = true
    try {
      inventory.value = await runtimeApi.inventory(projectId, {
        environment: environment.value, resource: 'deployments', page: page.value,
        page_size: pageSize.value, query: query.value || undefined, status: status.value || undefined,
      })
      refreshError.value = ''
    } catch (error) {
      refreshError.value = error instanceof Error ? error.message : 'Runtime 刷新失败'
    } finally { loading.value = false }
  }

  async function initialize() { await loadEnvironments(); await refresh() }
  function resetPageAndRefresh() {
    if (page.value !== 1) {
      page.value = 1
      return
    }
    syncUrl()
    void refresh()
  }
  watch([environment, status, pageSize], resetPageAndRefresh)
  watch(page, () => { syncUrl(); void refresh() })
  let queryTimer: ReturnType<typeof setTimeout> | undefined
  watch(query, () => {
    clearTimeout(queryTimer)
    queryTimer = setTimeout(resetPageAndRefresh, 300)
  })
  const timer = setInterval(() => {
    if (autoRefresh.value && (typeof document === 'undefined' || !document.hidden)) void refresh()
  }, 30_000)
  onScopeDispose(() => { clearInterval(timer); clearTimeout(queryTimer) })
  return { environments, inventory, environment, query, status, page, pageSize, loading, refreshError, autoRefresh, initialize, refresh }
}
