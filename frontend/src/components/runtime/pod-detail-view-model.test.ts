import { describe, expect, it } from 'vitest'
import { containerStateLabel, podDetailPath, podStatusTone } from './pod-detail-view-model'

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

  it('builds the Pod detail route from the expanded Deployment context', () => {
    expect(podDetailPath(7, 'prod', 8, 'payments-a')).toBe(
      '/devcenter/projects/7/runtime/environments/prod/applications/8/pods/payments-a',
    )
  })
})
