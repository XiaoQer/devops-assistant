import axios from 'axios'

let csrfToken = ''
let authenticationRequiredCallback: (() => void) | undefined

export const setCsrfToken = (value = '') => {
  csrfToken = value
}

export const onAuthenticationRequired = (callback: () => void) => {
  authenticationRequiredCallback = callback
}

export const client = axios.create({
  baseURL: '/api',
  timeout: 120000,
  withCredentials: true,
})

client.interceptors.request.use(config => {
  const method = config.method?.toUpperCase() || 'GET'
  if (csrfToken && !['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    config.headers.set('X-CSRF-Token', csrfToken)
  }
  return config
})

client.interceptors.response.use(
  response => response.data.data,
  error => {
    if (error.response?.status === 401) {
      try {
        authenticationRequiredCallback?.()
      } catch {
        // Authentication cleanup must not replace the safe request error.
      }
    }
    return Promise.reject(
      new Error(error.response?.data?.message || error.message || 'Request failed'),
    )
  },
)
