/**
 * Module Management API - 模块管理接口
 */
import request from '@/utils/request'

export interface ModuleInfo {
    slug: string
    display_name: string
    description: string
    version: string
    permissions: string[]
    router_prefix: string
    is_enabled: boolean
    tenant_count: number
    created_at?: string
    updated_at?: string
}

export interface ModuleDetail {
    slug: string
    display_name: string
    description: string
    version: string
    permissions: string[]
    router_prefix: string
    router_tags: string[]
    ui_meta: {
        icon: string
        path: string
        children: { title: string; path: string }[]
    } | null
    is_enabled: boolean
    tenant_count: number
    created_at?: string
    updated_at?: string
}

export interface ModuleStats {
    slug: string
    display_name: string
    active_tenants: number
    total_tenants: number
    recent_activations: number
}

export interface UpdateModuleStatusRequest {
    is_enabled: boolean
    reason?: string
}

export interface UpdateModuleVersionRequest {
    version: string
    changelog?: string
}

export const modulesApi = {
    // 获取所有模块
    getModules: (includeStats: boolean = true) =>
        request.get<any, { data: ModuleInfo[] }>('/modules', {
            params: { include_stats: includeStats }
        }),

    // 获取模块详情
    getModule: (slug: string) =>
        request.get<any, { data: ModuleDetail }>(`/modules/${slug}`),

    // 更新模块状态（启用/禁用）
    updateModuleStatus: (slug: string, data: UpdateModuleStatusRequest) =>
        request.put<any, { data: { slug: string; is_enabled: boolean; message: string } }>(
            `/modules/${slug}/status`,
            data
        ),

    // 更新模块版本
    updateModuleVersion: (slug: string, data: UpdateModuleVersionRequest) =>
        request.put<any, { data: { slug: string; version: string; message: string } }>(
            `/modules/${slug}/version`,
            data
        ),

    // 获取模块统计
    getModuleStats: (slug: string) =>
        request.get<any, { data: ModuleStats }>(`/modules/${slug}/stats`),

    // 重新加载模块
    reloadModule: (slug: string) =>
        request.post<any, { data: { slug: string; message: string } }>(`/modules/${slug}/reload`),

    // 同步模块注册表
    syncModules: () =>
        request.post<any, { data: { message: string; created_count: number; total_modules: number } }>('/modules/sync'),
}
