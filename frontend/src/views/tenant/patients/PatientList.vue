<template>
  <div class="patient-list">
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">患者列表</h1>
        <p class="page-subtitle">管理机构内所有长者的基本信息与评估档案</p>
      </div>
      <PatientSearchBar
        v-model="searchQuery"
        @search="handleSearch"
        @add="openDialog()"
      />
    </div>

    <el-card shadow="never" class="table-card">
      <PatientTable
        :patients="patients"
        :loading="loading"
        @edit="openDialog"
        @view="viewDetail"
        @delete="handleDelete"
      />

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="size"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @size-change="onPageChange"
          @current-change="onPageChange"
        />
      </div>
    </el-card>

    <PatientForm
      v-model:visible="dialogVisible"
      :patient="editingPatient"
      :loading="submitLoading"
      @submit="submitForm"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { usePatients } from './composables/usePatients'
import PatientSearchBar from './components/PatientSearchBar.vue'
import PatientTable from './components/PatientTable.vue'
import PatientForm from './components/PatientForm.vue'
import type { Patient } from '@/api/patients'

const router = useRouter()
const { loading, patients, total, page, size, searchQuery, fetchList, create, update, remove, handleSearch } = usePatients()

const dialogVisible = ref(false)
const submitLoading = ref(false)
const editingPatient = ref<Patient | null>(null)

function openDialog(row?: Patient) {
  editingPatient.value = row || null
  dialogVisible.value = true
}

async function submitForm(data: Record<string, string>) {
  submitLoading.value = true
  try {
    if (data.id) {
      await update(data.id, data)
      ElMessage.success('更新成功')
    } else {
      await create(data)
      ElMessage.success('新增患者成功')
    }
    dialogVisible.value = false
    fetchList()
  } catch (error) {
    console.error('Submit error:', error)
  } finally {
    submitLoading.value = false
  }
}

async function handleDelete(id: string) {
  try {
    await remove(id)
    ElMessage.success('删除成功')
    if (patients.value.length === 1 && page.value > 1) {
      page.value--
    }
    fetchList()
  } catch (error) {
    console.error('Delete error:', error)
  }
}

function viewDetail(id: string) {
  router.push({ name: 'HealthRecords', query: { patient_id: id } })
}

function onPageChange() {
  fetchList()
}

onMounted(() => {
  fetchList()
})
</script>

<style scoped>
.patient-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
}
.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
