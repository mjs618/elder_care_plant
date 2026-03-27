/**
 * Tenant management API.
 */
import request from '@/utils/request'

export type TenantStatus = 'active' | 'trial' | 'suspended' | 'cancelled'

export interface TenantPlanSummary {
    id: string | null
    name: string | null
    tier: string | null
}

export interface Tenant {
    id: string
    name: string
    slug: string
    status: TenantStatus
    contact_email: string
    brand_name: string | null
    primary_color: string | null
    created_at: string | null
    plan: TenantPlanSummary
}

export interface TenantDetail {
    id: string
    name: string
    slug: string
    status: TenantStatus
    contact_email: string
    brand_name: string | null
    primary_color: string | null
    created_at: string
    plan: TenantPlanSummary
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
    status: TenantStatus
    reason?: string
}

export interface UpdateTenantModulesRequest {
    module_slugs: string[]
}

export interface TenantQuery {
    search?: string
    status?: TenantStatus
}

export interface PageResult<T> {
    items: T[]
    total: number
    page: number
    size: number
}

export const tenantsApi = {
    getTenants: (page: number = 1, pageSize: number = 20, query: TenantQuery = {}) =>
        request.get<any, { data: PageResult<Tenant> }>('/tenants', {
            params: {
                page,
                page_size: pageSize,
                search: query.search || undefined,
                status: query.status || undefined,
            },
        }),

    getTenant: (id: string) =>
        request.get<any, { data: TenantDetail }>(`/tenants/${id}`),

    createTenant: (data: CreateTenantRequest) =>
        request.post<any, { data: { id: string; slug: string } }>('/tenants', data),

    updateTenant: (id: string, data: UpdateTenantRequest) =>
        request.put<any, { data: Tenant }>(`/tenants/${id}`, data),

    updateTenantStatus: (id: string, data: UpdateTenantStatusRequest) =>
        request.put<any, { data: { id: string; status: string; message: string } }>(
            `/tenants/${id}/status`,
            data,
        ),

    deleteTenant: (id: string) =>
        request.delete<any, { data: null }>(`/tenants/${id}`),

    getTenantModules: (id: string) =>
        request.get<any, { data: { active_modules: string[] } }>(`/tenants/${id}/modules`),

    updateTenantModules: (id: string, data: UpdateTenantModulesRequest) =>
        request.put<any, { data: { message: string; active_modules: string[] } }>(
            `/tenants/${id}/modules`,
            data,
        ),
}
