<template>
  <div class="assessment-list">
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">认知评估中心</h1>
        <p class="page-subtitle">MMSE / MoCA / CDR 等专业量表评估记录与追踪</p>
      </div>
      <AssessmentSearchBar
        v-model="searchQuery"
        @search="handleSearch"
        @add="openDialog()"
      />
    </div>

    <el-card shadow="never" class="table-card">
      <AssessmentTable
        :assessments="assessments"
        :loading="loading"
        @edit="openDialog"
        @delete="handleDelete"
      />

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="size"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="onPageChange"
          @current-change="onPageChange"
        />
      </div>
    </el-card>

    <AssessmentForm
      v-model:visible="dialogVisible"
      :assessment="assessment"
      :patient-options="patientOptions"
      :loading="submitLoading"
      @submit="handleSubmit"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAssessments } from './composables/useAssessments'
import AssessmentSearchBar from './components/AssessmentSearchBar.vue'
import AssessmentTable from './components/AssessmentTable.vue'
import AssessmentForm from './components/AssessmentForm.vue'

const {
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
} = useAssessments()

onMounted(() => {
    fetchList()
    fetchPatientOptions()
})
</script>

<style scoped>
.assessment-list {
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
