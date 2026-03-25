/**
 * Auth API — login, refresh, logout, me
 */
import request from '@/utils/request'

export interface LoginPayload {
    email: string
    password: string
}

export interface TokenPair {
    access_token: string
    refresh_token: string
    token_type: string
}

export interface UserProfile {
    id: string
    email: string
    username: string
    full_name: string | null
    scope: 'platform' | 'tenant'
    tenant_id: string | null
    permissions: string[]
}

export const authApi = {
    login: (payload: LoginPayload) =>
        request.post<any, { data: TokenPair }>('/auth/login', payload),

    refresh: (refresh_token: string) =>
        request.post<any, { data: TokenPair }>('/auth/refresh', { refresh_token }),

    me: () =>
        request.get<any, { data: UserProfile }>('/auth/me'),
}

/**
 * Modules API — fetches the list of registered modules
 * (used to build navigation and check tenant license)
 */
export interface UIMeta {
    icon: string
    path: string
    children?: { title: string; path: string }[]
}

export interface ModuleInfo {
    slug: string
    display_name: string
    description: string
    version: string
    permissions: string[]
    ui_meta?: UIMeta
}

export const modulesApi = {
    list: () =>
        request.get<any, { data: ModuleInfo[] }>('/modules'),
}
