/**
 * Platform admin API.
 */
import request from '@/utils/request'

export interface PlatformStats {
    total_tenants: number
    total_plans: number
    registered_modules: string[]
}

export interface TenantSeriesPoint {
    date: string
    new_tenants: number
    total_tenants: number
}

export interface PlatformStatsDetail {
    tenants: {
        total: number
        active: number
        trial: number
        suspended: number
        cancelled: number
        new_this_month: number
    }
    tenant_series: TenantSeriesPoint[]
    modules: Record<string, number>
    total_plans: number
    total_users: number
}

export interface Plan {
    id: string
    name: string
    tier: 'free' | 'standard' | 'enterprise'
    description: string | null
    rate_limit_rpm: number
    max_users: number
    max_patients: number
    included_modules: string
    tenant_count: number
    active_tenant_count: number
}

export interface CreatePlanRequest {
    name: string
    tier: 'free' | 'standard' | 'enterprise'
    description?: string
    rate_limit_rpm?: number
    max_users?: number
    max_patients?: number
    included_modules?: string
}

export interface UpdatePlanRequest {
    name?: string
    tier?: 'free' | 'standard' | 'enterprise'
    description?: string
    rate_limit_rpm?: number
    max_users?: number
    max_patients?: number
    included_modules?: string
}

export const platformApi = {
    getStats: () =>
        request.get<any, { data: PlatformStats }>('/admin/stats'),

    getStatsDetail: (days: 7 | 30 | 90 = 30) =>
        request.get<any, { data: PlatformStatsDetail }>('/admin/stats/detail', {
            params: { days },
        }),

    getPlans: () =>
        request.get<any, { data: Plan[] }>('/admin/plans'),

    getPlan: (id: string) =>
        request.get<any, { data: Plan }>(`/admin/plans/${id}`),

    createPlan: (data: CreatePlanRequest) =>
        request.post<any, { data: Plan }>('/admin/plans', data),

    updatePlan: (id: string, data: UpdatePlanRequest) =>
        request.put<any, { data: Plan }>(`/admin/plans/${id}`, data),

    deletePlan: (id: string) =>
        request.delete<any, { data: null }>(`/admin/plans/${id}`),
}
