import { describe, expect, it } from 'vitest'
import source from './DeploymentPodTable.vue?raw'

describe('DeploymentPodTable visual contract', () => {
  it('uses a dedicated responsive grid with readable text contrast', () => {
    expect(source).toContain('class="runtime-pod-item"')
    expect(source).toContain('grid-template-columns:minmax(0,2fr)')
    expect(source).toContain('color:#344054')
    expect(source).toContain('color:#667085')
  })
})
