import { describe, expect, it } from 'vitest'

import source from './PodOverview.vue?raw'

describe('PodOverview container-first layout contract', () => {
  it('exposes a container-first overview with a facts rail', () => {
    expect(source).toContain('class="container-first-layout"')
    expect(source).toContain('class="pod-facts"')
    expect(source).toContain('data-runtime-action="container-logs"')
    expect(source).toContain('data-runtime-action="container-terminal"')
    expect(source).toContain(':icon="Monitor"')
    expect(source).toContain('aria-label="打开终端"')
    expect(source).toContain(':disabled="!terminalEnabled"')
    expect(source).toContain('终端权限不足')
  })

  it('protects long container metadata from colliding with status and actions', () => {
    expect(source).toContain('.container-identity>div{min-width:0}')
    expect(source).toContain('.container-row{display:grid;grid-template-columns:minmax(240px,1.6fr)')
    expect(source).toContain('.container-actions{display:flex;gap:6px;justify-content:flex-end;flex-wrap:wrap}')
  })
})
