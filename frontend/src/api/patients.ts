import request from '@/utils/request'

export interface Patient {
    id: string
    full_name: string
    id_card_num: string | null
    gender: 'M' | 'F' | 'O'
    date_of_birth: string | null
    age: number | null
    contact_phone: string | null
    emergency_contact: string | null
    emergency_phone: string | null
    room_number: string | null
    bed_number: string | null
    medical_history: string | null
    created_at: string
}

export interface PatientQuery {
    page: number
    size: number
    search?: string
}

export interface PageResult<T> {
    items: T[]
    total: number
    page: number
    size: number
}

export const patientsApi = {
    list: (params: PatientQuery) =>
        request.get<any, { data: PageResult<Patient> }>('/patients', { params }),

    get: (id: string) =>
        request.get<any, { data: Patient }>(`/patients/${id}`),

    create: (data: Partial<Patient>) =>
        request.post<any, { data: Patient }>('/patients', data),

    update: (id: string, data: Partial<Patient>) =>
        request.put<any, { data: Patient }>(`/patients/${id}`, data),

    delete: (id: string) =>
        request.delete<any, { data: null }>(`/patients/${id}`),
}
