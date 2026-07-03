export const VIEWER_EMAIL_STORAGE_KEY = 'aegis.viewer.email'
export const VIEWER_NAME_STORAGE_KEY = 'aegis.viewer.name'

export function readViewerIdentity() {
  if (typeof window === 'undefined') {
    return { email: '', name: '' }
  }

  return {
    email: (window.localStorage.getItem(VIEWER_EMAIL_STORAGE_KEY) || '').trim().toLowerCase(),
    name: (window.localStorage.getItem(VIEWER_NAME_STORAGE_KEY) || '').trim(),
  }
}

