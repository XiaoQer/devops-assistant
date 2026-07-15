import { describe, expect, it } from 'vitest'

import source from './PodDetail.vue?raw'

describe('PodDetail container-first layout contract', () => {
  it('keeps destructive Pod actions behind the overflow menu', () => {
    expect(source).toContain('data-runtime-action="more"')
    expect(source).not.toContain('data-runtime-action="delete-pod"')
  })

  it('wires Container actions back to the selected container', () => {
    expect(source).toContain('@container-logs="openContainerLogs"')
    expect(source).toContain('@container-terminal="openContainerTerminal"')
    expect(source).toContain('class="pod-title pod-page-header"')
  })

  it('uses compact page-header typography instead of the global oversized header', () => {
    expect(source).toContain('.pod-page-header :deep(h1){max-width:900px;font-size:24px')
    expect(source).toContain('.pod-page-header :deep(.eyebrow){min-height:0')
  })
})
