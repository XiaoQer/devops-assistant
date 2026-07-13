import axios, { type InternalAxiosRequestConfig } from 'axios'

let csrfToken = ''
let authenticationRequiredCallback: (() => void) | undefined
let authEpoch = 0
let notifiedEpoch: number | undefined
const requestEpochs = new WeakMap<InternalAxiosRequestConfig, number>()

interface ApiErrorResponse {
  message?: unknown
  error?: {
    code?: unknown
  }
}

export class ApiClientError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly code?: string,
  ) {
    super(message)
    this.name = 'ApiClientError'
  }
}

export const setCsrfToken = (value = '') => {
  csrfToken = value
}

export const onAuthenticationRequired = (callback: () => void) => {
  authenticationRequiredCallback = callback
}

export const advanceAuthEpoch = () => {
  authEpoch += 1
  notifiedEpoch = undefined
}

export const client = axios.create({
  baseURL: '/api',
  timeout: 120000,
  withCredentials: true,
})

client.interceptors.request.use(config => {
  requestEpochs.set(config, authEpoch)
  const method = config.method?.toUpperCase() || 'GET'
  if (csrfToken && !['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    config.headers.set('X-CSRF-Token', csrfToken)
  }
  return config
})

client.interceptors.response.use(
  response => response.data.data,
  error => {
    const requestError = axios.isAxiosError<ApiErrorResponse>(error) ? error : undefined
    const status = requestError?.response?.status
    const responseMessage = requestError?.response?.data?.message
    const responseCode = requestError?.response?.data?.error?.code
    const code = typeof responseCode === 'string' ? responseCode : undefined
    const requestEpoch = requestError?.config
      ? requestEpochs.get(requestError.config)
      : undefined

    if (
      status === 401
      && requestEpoch === authEpoch
      && notifiedEpoch !== authEpoch
    ) {
      notifiedEpoch = authEpoch
      try {
        authenticationRequiredCallback?.()
      } catch {
        // Authentication cleanup must not replace the safe request error.
      }
    }
    return Promise.reject(new ApiClientError(
      typeof responseMessage === 'string'
        ? responseMessage
        : error instanceof Error ? error.message : 'Request failed',
      status,
      code,
    ))
  },
)
