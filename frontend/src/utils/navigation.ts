export const PORTAL_PATH = '/portal'
export const PROJECT_MANAGER_PATH = '/project-center'
export const DEV_CENTER_PATH = '/devcenter'

export function projectManagerProjectPath(projectId: number | string) {
  return `${PROJECT_MANAGER_PATH}/projects/${projectId}`
}

export function devCenterProjectPath(projectId: number | string) {
  return `${DEV_CENTER_PATH}/projects/${projectId}`
}

export function devCenterApplicationsPath(projectId: number | string) {
  return `${devCenterProjectPath(projectId)}/applications`
}

export function devCenterApplicationCreatePath(projectId: number | string) {
  return `${devCenterApplicationsPath(projectId)}/new`
}

export function devCenterApplicationPath(projectId: number | string, applicationId: number | string) {
  return `${devCenterApplicationsPath(projectId)}/${applicationId}`
}

export function devCenterPipelinesPath(projectId: number | string) {
  return `${devCenterProjectPath(projectId)}/pipelines`
}

export function devCenterPipelinePath(projectId: number | string, pipelineRunName: string) {
  return `${devCenterPipelinesPath(projectId)}/${encodeURIComponent(pipelineRunName)}`
}

export function devCenterApprovalsPath(projectId: number | string) {
  return `${devCenterProjectPath(projectId)}/approvals`
}
