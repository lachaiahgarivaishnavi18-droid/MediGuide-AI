import axios from 'axios'
export const api = axios.create({ baseURL: '/api', withCredentials: true, timeout: 60000 })
export function errorText(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    return typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((d: {msg:string}) => d.msg).join('. ') : 'Could not reach the service. Please try again.'
  }
  return error instanceof Error ? error.message : 'Something went wrong.'
}
