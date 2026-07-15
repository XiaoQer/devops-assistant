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

  it('keeps tabs readable in both inactive and active states', () => {
    expect(source).toContain('.detail-card :deep(.el-tabs__item){height:46px;color:#475467')
    expect(source).toContain('.detail-card :deep(.el-tabs__item.is-active){color:#175cd3')
    expect(source).toContain('.detail-card :deep(.el-tabs__active-bar){height:2px;background:#175cd3')
  })
})
