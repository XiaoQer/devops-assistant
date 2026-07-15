import { describe, expect, it } from 'vitest'
import source from './RuntimeResourceTable.vue?raw'

describe('RuntimeResourceTable action contract', () => {
  it('keeps Deployment actions in one overflow menu', () => {
    expect(source).toContain('<el-dropdown')
    expect(source).toContain('command="yaml"')
    expect(source).toContain('command="restart"')
    expect(source).not.toContain('<el-button link data-runtime-action="yaml"')
    expect(source).not.toContain('<el-button link type="warning" data-runtime-action="restart"')
  })
})
