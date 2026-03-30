/**
 * Elder Care Platform - Axios HTTP Client
 * Features:
 *   - Auto-attach Bearer token from user store
 *   - Automatic access-token refresh on 401
 *   - Unified error handling
 *   - Standardised response unwrapping {code, message, data}
 */
import axios, { type AxiosInstance, type AxiosRequestConfig, type AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'

let _getToken: (() => string | null) | null = null
let _refreshAccessToken: (() => Promise<string | null | void>) | null = null
let _onUnauthorized: (() => void) | null = null
let refreshPromise: Promise<string | null | void> | null = null

export function setupRequestInterceptors(
    getToken: () => string | null,
    refreshAccessToken: () => Promise<string | null | void>,
    onUnauthorized: () => void,
) {
    _getToken = getToken
    _refreshAccessToken = refreshAccessToken
    _onUnauthorized = onUnauthorized
}

const service: AxiosInstance = axios.create({
    baseURL: '/api/v1',
    timeout: 30_000,
    headers: { 'Content-Type': 'application/json' },
})

service.interceptors.request.use(
    (config) => {
        const token = _getToken?.()
        if (token) {
            config.headers.Authorization = `Bearer ${token}`
        }
        return config
    },
    (error) => Promise.reject(error),
)

service.interceptors.response.use(
    (response: AxiosResponse) => {
        const { code, message } = response.data
        if (code !== undefined && code !== 200 && code !== 201) {
            ElMessage.error(message || 'Request failed')
            return Promise.reject(new Error(message))
        }
        return response.data
    },
    async (error) => {
        const status = error.response?.status
        const detail = error.response?.data?.detail || error.message || 'Network error'
        const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean }
        const requestUrl = originalRequest?.url ?? ''
        const isAuthRequest = ['/auth/login', '/auth/refresh', '/auth/logout'].some((path) =>
            requestUrl.includes(path),
        )

        if (status === 401 && !originalRequest?._retry && !isAuthRequest && _refreshAccessToken) {
            originalRequest._retry = true
            try {
                refreshPromise ??= _refreshAccessToken().finally(() => {
                    refreshPromise = null
                })
                await refreshPromise
                const token = _getToken?.()
                if (token) {
                    originalRequest.headers = {
                        ...(originalRequest.headers ?? {}),
                        Authorization: `Bearer ${token}`,
                    }
                }
                return service(originalRequest)
            } catch {
                ElMessage.error('Session expired. Please sign in again.')
                _onUnauthorized?.()
                return Promise.reject(error)
            }
        }

        if (status === 401) {
            ElMessage.error('Session expired. Please sign in again.')
            _onUnauthorized?.()
        } else if (status === 402) {
            ElMessage.warning('This feature is not included in the current subscription.')
        } else if (status === 403) {
            ElMessage.error('Permission denied')
        } else if (status === 429) {
            ElMessage.warning('Too many requests. Please try again later.')
        } else if (status >= 500) {
            ElMessage.error('Server error. Please try again later.')
        } else {
            ElMessage.error(typeof detail === 'string' ? detail : 'Request failed')
        }

        return Promise.reject(error)
    },
)

export default service
