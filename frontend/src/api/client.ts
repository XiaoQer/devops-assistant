import axios from 'axios'

export const client = axios.create({ baseURL: '/api', timeout: 120000 })

client.interceptors.response.use(
  response => response.data.data,
  error => Promise.reject(new Error(error.response?.data?.message || error.message)),
)

