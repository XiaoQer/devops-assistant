import { describe, expect, it } from 'vitest'
import { containerStateLabel, podStatusTone } from './pod-detail-view-model'

describe('pod detail view model', () => {
  it('prioritizes waiting and terminated reasons over generic state labels', () => {
    expect(containerStateLabel({ state: 'waiting', reason: 'CrashLoopBackOff' })).toBe('CrashLoopBackOff')
    expect(containerStateLabel({ state: 'terminated', exit_code: 1 })).toBe('Terminated (1)')
    expect(containerStateLabel({ state: 'running' })).toBe('Running')
  })

  it('maps operational Pod states to visible tones', () => {
    expect(podStatusTone('Running', true)).toBe('success')
    expect(podStatusTone('Pending', false)).toBe('warning')
    expect(podStatusTone('Failed', false)).toBe('danger')
  })
})
