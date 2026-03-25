<template>
  <div class="assessment-list">
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">认知评估中心</h1>
        <p class="page-subtitle">MMSE / MoCA / CDR 等专业量表评估记录与追踪</p>
      </div>
      <div class="header-actions">
        <el-input
            v-model="searchQuery"
            placeholder="搜索长者姓名、评估人或备注"
            prefix-icon="Search"
            clearable
            @keyup.enter="handleSearch"
            @clear="handleSearch"
            style="width: 250px; margin-right: 16px"
        />
        <el-button type="primary" icon="Plus" @click="openDialog()">新建评估</el-button>
      </div>
    </div>

    <el-card shadow="never" class="table-card">
      <el-table :data="assessments" v-loading="loading" stripe>
        <el-table-column prop="patient_name" label="长者姓名" min-width="120">
          <template #default="{ row }">
            <span class="patient-link">{{ row.patient_name || '未知' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="assessment_type" label="量表类型" width="120">
          <template #default="{ row }">
            <el-tag :type="row.assessment_type === 'MMSE' ? 'primary' : row.assessment_type === 'MoCA' ? 'success' : 'warning'">
              {{ row.assessment_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="evaluation_date" label="评估日期" width="140" />
        <el-table-column prop="total_score" label="量表得分" width="100">
          <template #default="{ row }">
            <span class="score-display" :class="getScoreColor(row)">{{ row.total_score ?? '--' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status_diagnosis" label="认知定级" width="120">
          <template #default="{ row }">
            <el-tag size="small" :type="getStatusColor(row.status_diagnosis)" effect="dark">
              {{ formatStatus(row.status_diagnosis) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="evaluator_name" label="评估人" width="120" />
        <el-table-column prop="remarks" label="综合备注" min-width="150" show-overflow-tooltip />

        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link icon="EditPen" @click="openDialog(row)">查看/编辑</el-button>
            <el-popconfirm title="确定要删除该条记录吗？" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button type="danger" link icon="Delete">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
            v-model:current-page="page"
            v-model:page-size="size"
            :total="total"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            @size-change="fetchData"
            @current-change="fetchData"
        />
      </div>
    </el-card>

    <!-- Create / Edit Dialog -->
    <el-dialog
        v-model="dialogVisible"
        :title="isEdit ? '编辑评估报告' : '新建量表评估'"
        width="650px"
        destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px" label-position="right">
        <!-- We fetch all patients so the dropdown can let them pick who to assess -->
        <el-form-item label="评估对象" prop="patient_id" v-if="!isEdit">
          <el-select
            v-model="form.patient_id"
            filterable
            placeholder="请搜索或选择患者"
            style="width: 100%"
          >
            <el-option
              v-for="p in patientOptions"
              :key="p.id"
              :label="`${p.full_name} (${p.room_number || '无房间'})`"
              :value="p.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="量表类型" prop="assessment_type">
          <el-radio-group v-model="form.assessment_type">
            <el-radio-button label="MMSE">简易精神量表(MMSE)</el-radio-button>
            <el-radio-button label="MoCA">蒙特利尔评分(MoCA)</el-radio-button>
            <el-radio-button label="CDR">临床痴呆评定(CDR)</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="评估日期" prop="evaluation_date">
              <el-date-picker v-model="form.evaluation_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="评估人" prop="evaluator_name">
              <el-input v-model="form.evaluator_name" placeholder="评估医生/护士姓名" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="总分" prop="total_score">
              <el-input-number v-model="form.total_score" :min="0" :max="30" style="width: 100%" placeholder="录入最终得分" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="认知定级" prop="status_diagnosis">
              <el-select v-model="form.status_diagnosis" placeholder="临床判断" style="width: 100%">
                <el-option label="正常 (Normal)" value="NORMAL" />
                <el-option label="轻度认知障碍 (MCI)" value="MCI" />
                <el-option label="轻度痴呆 (Mild)" value="MILD" />
                <el-option label="中度痴呆 (Moderate)" value="MODERATE" />
                <el-option label="重度痴呆 (Severe)" value="SEVERE" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="综合备注" prop="remarks">
          <el-input v-model="form.remarks" type="textarea" :rows="3" placeholder="患者配合度、特殊表现或其他注意事项..." />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="submitLoading" @click="submitForm">保存记录</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { assessmentsApi, type Assessment } from '@/api/assessments'
import { patientsApi, type Patient } from '@/api/patients'

// --- State ---
const loading = ref(false)
const assessments = ref<Assessment[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const searchQuery = ref('')
const patientOptions = ref<Patient[]>([])

// --- Dialog State ---
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitLoading = ref(false)
const formRef = ref<FormInstance>()

const initialForm = {
  id: '',
  patient_id: '',
  assessment_type: 'MMSE' as const,
  evaluation_date: new Date().toISOString().split('T')[0],
  total_score: null as number | null,
  status_diagnosis: 'NORMAL' as const,
  evaluator_name: '',
  remarks: ''
}
const form = reactive({ ...initialForm })
const rules: FormRules = {
  patient_id: [{ required: true, message: '请选择评估对象', trigger: 'change' }],
  status_diagnosis: [{ required: true, message: '请评估认知等级', trigger: 'change' }]
}

// --- API Calls ---
async function fetchData() {
  loading.value = true
  try {
    const res = await assessmentsApi.list({
      page: page.value,
      size: size.value,
      search: searchQuery.value || undefined
    })
    const result = (res as any).data
    assessments.value = result.items
    total.value = result.total
  } catch (error) {
    console.error('Failed to fetch assessments', error)
  } finally {
    loading.value = false
  }
}

async function fetchPatients() {
  try {
    const res = await patientsApi.list({ page: 1, size: 1000 })
    const result = res as unknown as { items: Patient[] }
    patientOptions.value = result.items
  } catch (e) {
    console.error('Failed to load patient options', e)
  }
}

function handleSearch() {
  page.value = 1
  fetchData()
}

function openDialog(row?: Assessment) {
  isEdit.value = !!row
  if (row) {
    Object.assign(form, row)
  } else {
    Object.assign(form, initialForm)
  }
  dialogVisible.value = true
  // Reset validators
  setTimeout(() => formRef.value?.clearValidate(), 0)
}

async function submitForm() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitLoading.value = true
      try {
        const payload = { ...form }
        // Remove empty ID for creation
        const { id, ...createPayload } = payload
        
        if (isEdit.value) {
          // Can't change patient ID on existing assessment
          const { patient_id, ...updatePayload } = createPayload
          await assessmentsApi.update(id, updatePayload)
          ElMessage.success('更新评估记录成功')
        } else {
          await assessmentsApi.create(createPayload)
          ElMessage.success('新增评估记录成功')
        }
        dialogVisible.value = false
        fetchData()
      } catch (e) {
        console.error('Submit fail', e)
      } finally {
        submitLoading.value = false
      }
    }
  })
}

async function handleDelete(id: string) {
  try {
    await assessmentsApi.delete(id)
    ElMessage.success('已删除记录')
    fetchData()
  } catch (error) {
    console.error('Delete error', error)
  }
}

// --- Formatting Helpers ---
function formatStatus(status: string) {
  const map: Record<string, string> = {
    NORMAL: '正常',
    MCI: '轻度障碍 (MCI)',
    MILD: '轻度痴呆',
    MODERATE: '中度痴呆',
    SEVERE: '重度痴呆'
  }
  return map[status] || status
}

function getStatusColor(status: string) {
  switch (status) {
    case 'NORMAL': return 'success'
    case 'MCI': return 'warning'
    case 'MILD': return 'danger'
    case 'MODERATE': return 'danger'
    case 'SEVERE': return 'danger'
    default: return 'info'
  }
}

function getScoreColor(row: Assessment) {
  if (row.total_score == null) return ''
  if (row.assessment_type === 'MMSE') {
    if (row.total_score >= 27) return 'color-good'
    if (row.total_score <= 20) return 'color-bad'
  } else if (row.assessment_type === 'MoCA') {
    if (row.total_score >= 26) return 'color-good'
  }
  return ''
}

onMounted(() => {
  fetchData()
  fetchPatients()
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
.header-actions {
  display: flex;
  align-items: center;
}
.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
.patient-link {
  font-weight: 600;
  color: var(--text-primary);
}
.score-display {
  font-weight: 700;
}
.color-good {
  color: var(--color-success);
}
.color-bad {
  color: var(--color-danger);
}
</style>
