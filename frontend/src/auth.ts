import axios from 'axios'
import { api } from './api'
import type { User } from './types'

const invalidResponse = 'The service returned an invalid response. Please try again.'
const gatewayStatuses = [502, 503, 504]

function isTimeout(error: unknown) {
  return axios.isAxiosError(error) && ['ECONNABORTED', 'ETIMEDOUT'].includes(error.code ?? '')
}

export function readUser(data: unknown): User {
  const user = data as Partial<User> | null
  if (!user || typeof user !== 'object' || typeof user.id !== 'string' || !user.id ||
      typeof user.name !== 'string' || !user.name.trim() ||
      typeof user.email !== 'string' || !['patient', 'admin'].includes(user.role ?? '') ||
      !user.preferences || typeof user.preferences !== 'object' || Array.isArray(user.preferences)) {
    throw new Error(invalidResponse)
  }
  return user as User
}

export async function waitForAuthService() {
  const deadline = Date.now() + 85000
  for (;;) {
    try {
      const { data } = await api.get<{ status?: string }>('/system/status', {
        timeout: Math.min(12000, Math.max(1, deadline - Date.now())),
      })
      if (data?.status !== 'ok') throw new Error(invalidResponse)
      return
    } catch (error) {
      const status = axios.isAxiosError(error) ? error.response?.status : undefined
      if (Date.now() + 2000 >= deadline ||
          (!gatewayStatuses.includes(status ?? 0) && !isTimeout(error))) throw error
      await new Promise(resolve => setTimeout(resolve, 2000))
    }
  }
}

export function authErrorText(error: unknown): string {
  if (!axios.isAxiosError(error)) return error instanceof Error ? error.message : invalidResponse
  if (isTimeout(error)) return 'The service took too long to respond. Please try again.'
  const response = error.response
  if (!response) return 'Could not connect to the service. Check your internet connection and try again.'
  if (response.data?.code === 'DATABASE_UNAVAILABLE') return 'The account database is temporarily unavailable. Please try again shortly.'
  if (gatewayStatuses.includes(response.status)) return 'The service is temporarily unavailable. Please try again shortly.'
  if (response.status === 401) return 'Invalid email or password.'
  if (response.status === 403) return 'Authentication failed. Please check your account access and try again.'
  if (response.status === 409) return 'An account with that email address already exists.'
  if (response.status === 422) return 'Please check your account details and try again.'
  if (response.status === 429) return 'Too many attempts. Please wait and try again.'
  if (response.status >= 500) return 'The service encountered an error. Please try again shortly.'
  return invalidResponse
}
