/**
 * Tenant Management API - 租户管理接口
 */
import request from '@/utils/request'

export interface Tenant {
    id: string
    name: string
    slug: string
    status: 'active' | 'trial' | 'suspended' | 'cancelled'
    contact_email: string
}

export interface TenantDetail {
    id: string
    name: string
    slug: string
    status: 'active' | 'trial' | 'suspended' | 'cancelled'
    contact_email: string
    brand_name: string | null
    primary_color: string | null
    created_at: string
    plan: {
        id: string
        name: string
        tier: string
    }
    active_modules: string[]
    user_count: number
}

export interface CreateTenantRequest {
    name: string
    slug: string
    contact_email: string
    plan_id: string
    brand_name?: string
    primary_color?: string
}

export interface UpdateTenantRequest {
    name?: string
    contact_email?: string
    brand_name?: string
    primary_color?: string
    plan_id?: string
}

export interface UpdateTenantStatusRequest {
    status: 'active' | 'trial' | 'suspended' | 'cancelled'
    reason?: string
}

export interface UpdateTenantModulesRequest {
    module_slugs: string[]
}

export interface PageResult<T> {
    items: T[]
    total: number
    page: number
    page_size: number
}

export const tenantsApi = {
    // 租户列表
    getTenants: (page: number = 1, pageSize: number = 20) =>
        request.get<any, { data: PageResult<Tenant> }>('/tenants', {
            params: { page, page_size: pageSize }
        }),
    
    // 租户详情
    getTenant: (id: string) =>
        request.get<any, { data: TenantDetail }>(`/tenants/${id}`),
    
    // 创建租户
    createTenant: (data: CreateTenantRequest) =>
        request.post<any, { data: { id: string; slug: string } }>('/tenants', data),
    
    // 更新租户
    updateTenant: (id: string, data: UpdateTenantRequest) =>
        request.put<any, { data: Tenant }>(`/tenants/${id}`, data),
    
    // 更新租户状态
    updateTenantStatus: (id: string, data: UpdateTenantStatusRequest) =>
        request.put<any, { data: { id: string; status: string; message: string } }>(
            `/tenants/${id}/status`,
            data
        ),
    
    // 删除租户
    deleteTenant: (id: string) =>
        request.delete<any, { data: null }>(`/tenants/${id}`),
    
    // 获取租户模块
    getTenantModules: (id: string) =>
        request.get<any, { data: { active_modules: string[] } }>(`/tenants/${id}/modules`),
    
    // 更新租户模块
    updateTenantModules: (id: string, data: UpdateTenantModulesRequest) =>
        request.put<any, { data: { message: string; active_modules: string[] } }>(
            `/tenants/${id}/modules`,
            data
        ),
}
