import { reactive } from 'vue'
import type { RuntimePodSummary } from '../types'

export interface DeploymentPodTarget {
  key: string
  applicationId: number
  deployment: string
}

export interface DeploymentPodEntry {
  loading: boolean
  loaded: boolean
  pods: RuntimePodSummary[]
  error: string
}

export function useDeploymentPods(
  loader: (target: DeploymentPodTarget) => Promise<RuntimePodSummary[]>,
) {
  const entries = reactive<Record<string, DeploymentPodEntry>>({})

  async function request(target: DeploymentPodTarget, force = false) {
    const current = entries[target.key]
    if (!force && (current?.loading || current?.loaded)) return
    if (!current) {
      entries[target.key] = {
        loading: false, loaded: false, pods: [], error: '',
      }
    }
    const entry = entries[target.key]
    entry.loading = true
    entry.error = ''
    try {
      entry.pods = await loader(target)
      entry.loaded = true
    } catch (error) {
      entry.error = error instanceof Error ? error.message : 'Pod 列表读取失败'
    } finally {
      entry.loading = false
    }
  }

  const load = (target: DeploymentPodTarget) => request(target)
  const retry = (target: DeploymentPodTarget) => request(target, true)
  function clear() {
    for (const key of Object.keys(entries)) delete entries[key]
  }

  return { entries, load, retry, clear }
}
