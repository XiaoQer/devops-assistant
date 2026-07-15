import { describe, expect, it } from 'vitest'

import source from './PodOverview.vue?raw'

describe('PodOverview container-first layout contract', () => {
  it('exposes a container-first overview with a facts rail', () => {
    expect(source).toContain('class="container-first-layout"')
    expect(source).toContain('class="pod-facts"')
    expect(source).toContain('data-runtime-action="container-logs"')
    expect(source).toContain('data-runtime-action="container-terminal"')
  })
})
