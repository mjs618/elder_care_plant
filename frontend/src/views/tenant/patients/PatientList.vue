<template>
  <div class="patient-list">
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">患者列表</h1>
        <p class="page-subtitle">管理机构内所有长者的基本信息与评估档案</p>
      </div>
      <div class="header-actions">
        <el-input
            v-model="searchQuery"
            placeholder="搜索姓名、身份证或房间号"
            prefix-icon="Search"
            clearable
            @keyup.enter="handleSearch"
            @clear="handleSearch"
            style="width: 260px; margin-right: 16px"
        />
        <el-button type="primary" icon="Plus" @click="openDialog()">新增患者</el-button>
      </div>
    </div>

    <el-card shadow="never" class="table-card">
      <el-table :data="patients" v-loading="loading" stripe>
        <el-table-column prop="full_name" label="姓名" min-width="120" />
        <el-table-column label="性别" width="80">
          <template #default="{ row }">
            <el-tag :type="row.gender === 'M' ? 'primary' : row.gender === 'F' ? 'danger' : 'info'" size="small">
              {{ row.gender === 'M' ? '男' : row.gender === 'F' ? '女' : '其他' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="age" label="年龄" width="80" />
        <el-table-column prop="id_card_num" label="身份证号" min-width="180" />
        <el-table-column prop="room_number" label="房间号" width="120" />
        <el-table-column prop="bed_number" label="床位" width="100" />
        <el-table-column prop="emergency_contact" label="紧急联系人" min-width="120" />
        <el-table-column prop="emergency_phone" label="紧急电话" min-width="140" />
        
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link icon="EditPen" @click="openDialog(row)">编辑</el-button>
            <el-button type="primary" link icon="View" @click="viewDetail(row.id)">档案</el-button>
            <el-popconfirm title="确定要删除该患者吗？此操作不可逆。" @confirm="handleDelete(row.id)" confirm-button-type="danger">
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
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next"
            @size-change="fetchData"
            @current-change="fetchData"
        />
      </div>
    </el-card>

    <!-- Add / Edit Dialog -->
    <el-dialog
        v-model="dialogVisible"
        :title="isEdit ? '编辑患者信息' : '新增患者'"
        width="650px"
        destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px" class="patient-form">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="姓名" prop="full_name">
              <el-input v-model="form.full_name" placeholder="请输入姓名" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="性别" prop="gender">
              <el-select v-model="form.gender" placeholder="请选择">
                <el-option label="男" value="M" />
                <el-option label="女" value="F" />
                <el-option label="其他" value="O" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="出生日期" prop="date_of_birth">
              <el-date-picker v-model="form.date_of_birth" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="身份证号" prop="id_card_num">
              <el-input v-model="form.id_card_num" placeholder="请输入身份证号" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="房间号" prop="room_number">
              <el-input v-model="form.room_number" placeholder="例如：A区101" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="床位号" prop="bed_number">
              <el-input v-model="form.bed_number" placeholder="例如：01" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="紧急联系人" prop="emergency_contact">
              <el-input v-model="form.emergency_contact" placeholder="姓名/亲属关系" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="紧急电话" prop="emergency_phone">
              <el-input v-model="form.emergency_phone" placeholder="电话号码" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="病史与备注" prop="medical_history">
              <el-input v-model="form.medical_history" type="textarea" :rows="3" placeholder="既往病史、特长、忌口等重要信息..." />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitForm" :loading="submitLoading">保存</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { patientsApi, type Patient } from '@/api/patients'

const router = useRouter()
const loading = ref(false)
const patients = ref<Patient[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const searchQuery = ref('')

// -- Dialog State --
const dialogVisible = ref(false)
const submitLoading = ref(false)
const isEdit = ref(false)
const formRef = ref<FormInstance>()

type PatientFormModel = {
  id: string
  full_name: string
  gender: 'M' | 'F' | 'O'
  date_of_birth: string
  id_card_num: string
  room_number: string
  bed_number: string
  emergency_contact: string
  emergency_phone: string
  medical_history: string
}

function createInitialForm(): PatientFormModel {
  return {
    id: '',
    full_name: '',
    gender: 'M',
    date_of_birth: '',
    id_card_num: '',
    room_number: '',
    bed_number: '',
    emergency_contact: '',
    emergency_phone: '',
    medical_history: ''
  }
}

const form = reactive<PatientFormModel>(createInitialForm())

const rules = reactive<FormRules>({
  full_name: [{ required: true, message: '姓名不能为空', trigger: 'blur' }],
  gender: [{ required: true, message: '请选择性别', trigger: 'change' }],
})

// -- Methods --
async function fetchData() {
  loading.value = true
  try {
    const res = await patientsApi.list({
      page: page.value,
      size: size.value,
      search: searchQuery.value || undefined
    })
    const result = res.data as import('@/api/patients').PageResult<Patient>
    patients.value = result.items
    total.value = result.total
  } catch (error) {
    console.error('Fetch error:', error)
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  fetchData()
}

function openDialog(row?: Patient) {
  isEdit.value = !!row
  Object.assign(form, createInitialForm())
  if (row) {
    form.id = row.id
    form.full_name = row.full_name
    form.gender = row.gender
    form.date_of_birth = row.date_of_birth ?? ''
    form.id_card_num = row.id_card_num ?? ''
    form.room_number = row.room_number ?? ''
    form.bed_number = row.bed_number ?? ''
    form.emergency_contact = row.emergency_contact ?? ''
    form.emergency_phone = row.emergency_phone ?? ''
    form.medical_history = row.medical_history ?? ''
  }
  dialogVisible.value = true
  // Reset validation state after DOM updates
  setTimeout(() => formRef.value?.clearValidate(), 0)
}

async function submitForm() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitLoading.value = true
      try {
        const payload: Record<string, string> = {
          full_name: form.full_name,
          gender: form.gender,
          id_card_num: form.id_card_num,
          room_number: form.room_number,
          bed_number: form.bed_number,
          emergency_contact: form.emergency_contact,
          emergency_phone: form.emergency_phone,
          medical_history: form.medical_history
        }
        if (form.date_of_birth) {
          payload.date_of_birth = form.date_of_birth
        }

        if (isEdit.value) {
          await patientsApi.update(form.id, payload)
          ElMessage.success('更新成功')
        } else {
          await patientsApi.create(payload)
          ElMessage.success('新增患者成功')
        }
        dialogVisible.value = false
        fetchData()
      } finally {
        submitLoading.value = false
      }
    }
  })
}

async function handleDelete(id: string) {
  try {
    await patientsApi.delete(id)
    ElMessage.success('删除成功')
    if (patients.value.length === 1 && page.value > 1) {
      page.value--
    }
    fetchData()
  } catch (error) {
    console.error('Delete error:', error)
  }
}

function viewDetail(id: string) {
  router.push({ name: 'HealthRecords', query: { patient_id: id } })
}

// -- Initialization --
onMounted(() => {
  fetchData()
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
.header-actions {
  display: flex;
  align-items: center;
}
.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
.patient-form .el-select {
  width: 100%;
}
</style>
