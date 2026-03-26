import { ref } from 'vue'
import { patientsApi, type Patient, type PatientQuery, type PageResult } from '@/api/patients'

export function usePatients() {
  const loading = ref(false)
  const patients = ref<Patient[]>([])
  const total = ref(0)
  const page = ref(1)
  const size = ref(20)
  const searchQuery = ref('')

  async function fetchList(params?: Partial<PatientQuery>) {
    loading.value = true
    try {
      const res = await patientsApi.list({
        page: params?.page ?? page.value,
        size: params?.size ?? size.value,
        search: params?.search ?? (searchQuery.value || undefined)
      })
      const result = res.data as PageResult<Patient>
      patients.value = result.items
      total.value = result.total
      if (params?.page) page.value = params.page
      if (params?.size) size.value = params.size
    } catch (error) {
      console.error('Fetch patients error:', error)
    } finally {
      loading.value = false
    }
  }

  async function fetchOne(id: string) {
    try {
      const res = await patientsApi.get(id)
      return res.data
    } catch (error) {
      console.error('Fetch patient error:', error)
      return null
    }
  }

  async function create(data: Partial<Patient>) {
    try {
      const res = await patientsApi.create(data)
      return res.data
    } catch (error) {
      console.error('Create patient error:', error)
      throw error
    }
  }

  async function update(id: string, data: Partial<Patient>) {
    try {
      const res = await patientsApi.update(id, data)
      return res.data
    } catch (error) {
      console.error('Update patient error:', error)
      throw error
    }
  }

  async function remove(id: string) {
    try {
      await patientsApi.delete(id)
    } catch (error) {
      console.error('Delete patient error:', error)
      throw error
    }
  }

  function handleSearch() {
    page.value = 1
    fetchList()
  }

  return {
    loading,
    patients,
    total,
    page,
    size,
    searchQuery,
    fetchList,
    fetchOne,
    create,
    update,
    remove,
    handleSearch
  }
}
