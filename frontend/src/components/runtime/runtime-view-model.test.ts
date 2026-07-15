import { describe, expect, it } from 'vitest'

import {
  confirmationCopy,
  decodeTerminalFrame,
  encodeResizeFrame,
  isProduction,
  shouldToggleDeploymentRow,
  statusTone,
} from './runtime-view-model'

describe('runtime view model', () => {
  it('maps runtime statuses to stable tones', () => {
    expect(statusTone('Healthy')).toBe('success')
    expect(statusTone('Progressing')).toBe('primary')
    expect(statusTone('Degraded')).toBe('warning')
    expect(statusTone('Failed')).toBe('danger')
    expect(statusTone('Unknown')).toBe('info')
  })

  it('detects production and creates explicit destructive copy', () => {
    expect(isProduction('prod')).toBe(true)
    expect(isProduction('production')).toBe(true)
    expect(isProduction('dev')).toBe(false)
    expect(confirmationCopy('delete-pod', 'prod', 'payments-a')).toContain('生产环境')
    expect(confirmationCopy('restart', 'dev', 'payments')).toContain('滚动重启')
  })

  it('encodes resize and decodes terminal output frames', () => {
    expect(JSON.parse(encodeResizeFrame(120, 40))).toEqual({
      type: 'resize', cols: 120, rows: 40,
    })
    expect(decodeTerminalFrame(JSON.stringify({ type: 'stdout', data: 'ok\n' })))
      .toEqual({ type: 'stdout', data: 'ok\n' })
    expect(decodeTerminalFrame('not-json')).toEqual({ type: 'status', status: 'invalid-frame' })
  })

  it('toggles from ordinary row clicks but ignores resource actions', () => {
    expect(shouldToggleDeploymentRow()).toBe(true)
    expect(shouldToggleDeploymentRow('yaml')).toBe(false)
    expect(shouldToggleDeploymentRow('restart')).toBe(false)
    expect(shouldToggleDeploymentRow('pod-detail')).toBe(false)
    expect(shouldToggleDeploymentRow('retry')).toBe(false)
  })
})
