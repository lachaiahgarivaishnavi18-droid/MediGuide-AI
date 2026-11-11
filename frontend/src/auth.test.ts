import { AxiosError, type AxiosResponse } from 'axios'
import { afterEach, expect, it, vi } from 'vitest'
import { api } from './api'
import { authErrorText, readUser, waitForAuthService } from './auth'

function failure(status: number, data: unknown = '<html>Gateway unavailable</html>') {
  return new AxiosError('Request failed', undefined, undefined, undefined, { status, data } as AxiosResponse)
}

afterEach(() => {
  vi.restoreAllMocks()
  vi.useRealTimers()
})

it('waits for the backend after a gateway error using only readiness GETs', async () => {
  vi.useFakeTimers()
  const get = vi.spyOn(api, 'get').mockRejectedValueOnce(failure(502)).mockResolvedValueOnce({ data: { status: 'ok' } })
  const post = vi.spyOn(api, 'post')
  const readiness = waitForAuthService()
  await vi.advanceTimersByTimeAsync(2000)
  await readiness
  expect(get).toHaveBeenCalledTimes(2)
  expect(get).toHaveBeenLastCalledWith('/system/status', { timeout: 12000 })
  expect(post).not.toHaveBeenCalled()
})

it('rejects a successful response containing HTML instead of a user', () => {
  expect(() => readUser('<html>')).toThrow('invalid response')
})

it('distinguishes gateway, credentials, database and network errors', () => {
  expect(authErrorText(failure(502))).toMatch(/service is temporarily unavailable/)
  expect(authErrorText(failure(401))).toMatch(/Invalid email or password/)
  expect(authErrorText(failure(503, { code: 'DATABASE_UNAVAILABLE' }))).toMatch(/account database/)
  expect(authErrorText(new AxiosError('Network Error', 'ERR_NETWORK'))).toMatch(/internet connection/)
})
