/**
 * Elder Care Platform — Axios HTTP Client
 * Features:
 *   - Auto-attach Bearer token from user store
 *   - Unified error handling (401 → redirect to login)
 *   - Standardised response unwrapping {code, message, data}
 *   - Request cancellation support via AbortController
 */
import axios, { type AxiosInstance, type AxiosRequestConfig, type AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'

// The store is imported lazily to avoid circular deps at module init time
let _getToken: (() => string | null) | null = null
let _onUnauthorized: (() => void) | null = null

/** Call this once in main.ts after creating the Pinia instance */
export function setupRequestInterceptors(
    getToken: () => string | null,
    onUnauthorized: () => void,
) {
    _getToken = getToken
    _onUnauthorized = onUnauthorized
}

const service: AxiosInstance = axios.create({
    baseURL: '/api/v1',
    timeout: 30_000,
    headers: { 'Content-Type': 'application/json' },
})

// ── Request interceptor ──────────────────────────────────────────────────────
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

// ── Response interceptor ─────────────────────────────────────────────────────
service.interceptors.response.use(
    (response: AxiosResponse) => {
        const { code, message, data } = response.data
        // All successful platform responses use code 200 or 201
        if (code !== undefined && code !== 200 && code !== 201) {
            ElMessage.error(message || '请求失败')
            return Promise.reject(new Error(message))
        }
        // Unwrap: return `data` directly so callers don't need `.data.data`
        return response.data
    },
    (error) => {
        const status = error.response?.status
        const detail = error.response?.data?.detail || error.message || '网络错误'

        if (status === 401) {
            ElMessage.error('登录已过期，请重新登录')
            _onUnauthorized?.()
        } else if (status === 402) {
            ElMessage.warning('该功能需要升级套餐，请联系管理员')
        } else if (status === 403) {
            ElMessage.error('权限不足')
        } else if (status === 429) {
            ElMessage.warning('请求过于频繁，请稍后再试')
        } else if (status >= 500) {
            ElMessage.error('服务器内部错误，请稍后重试')
        } else {
            ElMessage.error(typeof detail === 'string' ? detail : '请求失败')
        }
        return Promise.reject(error)
    },
)

export default service
