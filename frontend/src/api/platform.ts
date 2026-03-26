/**
 * Platform Admin API - 运营控制台接口
 */
import request from '@/utils/request'

export interface PlatformStats {
    total_tenants: number
    total_plans: number
    registered_modules: string[]
}

export interface PlatformStatsDetail {
    tenants: {
        total: number
        active: number
        trial: number
        suspended: number
        new_this_month: number
    }
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
    // 统计
    getStats: () =>
        request.get<any, { data: PlatformStats }>('/admin/stats'),
    
    getStatsDetail: () =>
        request.get<any, { data: PlatformStatsDetail }>('/admin/stats/detail'),
    
    // 套餐管理
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
