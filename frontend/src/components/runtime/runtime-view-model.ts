export type RuntimeTone = 'success' | 'primary' | 'warning' | 'danger' | 'info'

export function statusTone(status: string): RuntimeTone {
  if (status === 'Healthy') return 'success'
  if (status === 'Progressing') return 'primary'
  if (status === 'Degraded') return 'warning'
  if (status === 'Failed') return 'danger'
  return 'info'
}

export function isProduction(environment: string) {
  return ['prod', 'production'].includes(environment.trim().toLowerCase())
}

export function confirmationCopy(
  action: 'restart' | 'delete-pod', environment: string, resource: string,
) {
  const prefix = isProduction(environment) ? '生产环境高风险操作：' : ''
  return action === 'restart'
    ? `${prefix}确认滚动重启 Deployment ${resource}？现有 Pod 将被逐步替换。`
    : `${prefix}确认删除 Pod ${resource}？控制器可能会创建替代 Pod。`
}

export function shouldToggleDeploymentRow(action?: string) {
  return !action
}

export function encodeResizeFrame(cols: number, rows: number) {
  return JSON.stringify({ type: 'resize', cols, rows })
}

export type TerminalFrame = {
  type: 'stdout' | 'stderr' | 'status'
  data?: string
  status?: string
}

export function decodeTerminalFrame(value: string): TerminalFrame {
  try {
    const frame = JSON.parse(value) as TerminalFrame
    if (['stdout', 'stderr', 'status'].includes(frame.type)) return frame
  } catch {
    // Invalid server frames are converted to a safe status.
  }
  return { type: 'status', status: 'invalid-frame' }
}
