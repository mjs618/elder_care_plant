import request from '@/utils/request'
import type { PageResult } from './patients'

export interface Assessment {
    id: string
    patient_id: string
    patient_name?: string
    assessment_type: 'MMSE' | 'MoCA' | 'CDR' | 'OTHER'
    evaluation_date: string
    total_score: number | null
    score_breakdown: Record<string, any> | null
    status_diagnosis: 'NORMAL' | 'MCI' | 'MILD' | 'MODERATE' | 'SEVERE'
    evaluator_name: string | null
    remarks: string | null
    created_at: string
}

export interface AssessmentQuery {
    page: number
    size: number
    search?: string
    patient_id?: string
}

export const assessmentsApi = {
    list: (params: AssessmentQuery) =>
        request.get<any, { data: PageResult<Assessment> }>('/assessments', { params }),

    get: (id: string) =>
        request.get<any, { data: Assessment }>(`/assessments/${id}`),

    create: (data: Partial<Assessment>) =>
        request.post<any, { data: Assessment }>('/assessments', data),

    update: (id: string, data: Partial<Assessment>) =>
        request.put<any, { data: Assessment }>(`/assessments/${id}`, data),

    delete: (id: string) =>
        request.delete<any, { data: null }>(`/assessments/${id}`),
}
