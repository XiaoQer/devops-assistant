import { describe, expect, it } from 'vitest'
import routerSource from './index.ts?raw'
import devCenterLayoutSource from '../layouts/DevCenterLayout.vue?raw'
import mainLayoutSource from '../layouts/MainLayout.vue?raw'

describe('retired navigation pages', () => {
  it('does not register Logs or Releases as standalone pages', () => {
    expect(routerSource).not.toContain("path: 'projects/:projectId/releases'")
    expect(routerSource).not.toContain("path: 'projects/:projectId/logs'")
    expect(devCenterLayoutSource).not.toContain("name:'Releases'")
    expect(devCenterLayoutSource).not.toContain("name:'Logs'")
    expect(mainLayoutSource).not.toContain("name: 'Releases'")
  })
})
