import type { RuntimePodContainerDetail } from '../../types'
import type { RuntimeTone } from './runtime-view-model'

export function containerStateLabel(container: Pick<RuntimePodContainerDetail, 'state' | 'reason' | 'exit_code'>) {
  if (container.reason) return container.reason
  if (container.state === 'terminated') return `Terminated${container.exit_code == null ? '' : ` (${container.exit_code})`}`
  return container.state.charAt(0).toUpperCase() + container.state.slice(1)
}

export function podStatusTone(status: string, ready: boolean): RuntimeTone {
  if (ready && status === 'Running') return 'success'
  if (status === 'Pending') return 'warning'
  if (['Failed', 'CrashLoopBackOff', 'ImagePullBackOff'].includes(status)) return 'danger'
  return 'info'
}

export function formatRuntimeTime(value?: string | null) {
  return value ? new Date(value).toLocaleString() : '—'
}

export function podDetailPath(
  projectId: number, environment: string, applicationId: number, podName: string,
) {
  return `/devcenter/projects/${projectId}/runtime/environments/${encodeURIComponent(environment)}/applications/${applicationId}/pods/${encodeURIComponent(podName)}`
}
