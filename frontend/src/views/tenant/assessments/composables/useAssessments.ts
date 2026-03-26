import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { assessmentsApi, type Assessment } from '@/api/assessments'
import { patientsApi, type Patient } from '@/api/patients'

export function useAssessments() {
    const loading = ref(false)
    const assessments = ref<Assessment[]>([])
    const total = ref(0)
    const page = ref(1)
    const size = ref(20)
    const searchQuery = ref('')
    const patientOptions = ref<Patient[]>([])
    const dialogVisible = ref(false)
    const submitLoading = ref(false)
    const assessment = ref<Assessment | null>(null)

    async function fetchList(params?: { page?: number; size?: number; search?: string }) {
        loading.value = true
        try {
            const res = await assessmentsApi.list({
                page: params?.page ?? page.value,
                size: params?.size ?? size.value,
                search: params?.search ?? (searchQuery.value || undefined)
            })
            const result = (res as any).data
            assessments.value = result.items
            total.value = result.total
            if (params?.page) page.value = params.page
            if (params?.size) size.value = params.size
        } catch (error) {
            console.error('Fetch assessments error:', error)
        } finally {
            loading.value = false
        }
    }

    async function fetchPatientOptions() {
        try {
            const res = await patientsApi.list({ page: 1, size: 1000 })
            const result = res as unknown as { items: Patient[] }
            patientOptions.value = result.items
        } catch (e) {
            console.error('Fetch patient options error:', e)
        }
    }

    function handleSearch() {
        page.value = 1
        fetchList()
    }

    function onPageChange() {
        fetchList()
    }

    function openDialog(row?: Assessment) {
        if (row) {
            assessment.value = row
        } else {
            assessment.value = null
        }
        dialogVisible.value = true
    }

    async function handleSubmit(data: Record<string, any>) {
        submitLoading.value = true
        try {
            if (assessment.value) {
                await assessmentsApi.update(assessment.value.id, data)
                ElMessage.success('更新评估记录成功')
            } else {
                await assessmentsApi.create(data)
                ElMessage.success('新增评估记录成功')
            }
            dialogVisible.value = false
            fetchList()
        } catch (e) {
            console.error('Submit error:', e)
        } finally {
            submitLoading.value = false
        }
    }

    async function handleDelete(id: string) {
        try {
            await assessmentsApi.delete(id)
            ElMessage.success('已删除记录')
            if (assessments.value.length === 1 && page.value > 1) {
                page.value--
            }
            fetchList()
        } catch (error) {
            console.error('Delete error', error)
        }
    }

    return {
        loading,
        assessments,
        total,
        page,
        size,
        searchQuery,
        patientOptions,
        dialogVisible,
        submitLoading,
        assessment,
        fetchList,
        fetchPatientOptions,
        handleSearch,
        onPageChange,
        openDialog,
        handleSubmit,
        handleDelete
    }
}
