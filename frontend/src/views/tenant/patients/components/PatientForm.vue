<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
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
        <el-button @click="$emit('update:visible', false)">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="loading">保存</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import type { Patient } from '@/api/patients'

const props = defineProps<{
  visible: boolean
  patient?: Patient | null
  loading: boolean
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'submit': [data: Record<string, string>]
}>()

const formRef = ref<FormInstance>()

interface PatientFormModel {
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

const isEdit = ref(false)

watch(() => props.visible, (val) => {
  if (val) {
    isEdit.value = !!props.patient
    Object.assign(form, createInitialForm())
    if (props.patient) {
      form.id = props.patient.id
      form.full_name = props.patient.full_name
      form.gender = props.patient.gender
      form.date_of_birth = props.patient.date_of_birth ?? ''
      form.id_card_num = props.patient.id_card_num ?? ''
      form.room_number = props.patient.room_number ?? ''
      form.bed_number = props.patient.bed_number ?? ''
      form.emergency_contact = props.patient.emergency_contact ?? ''
      form.emergency_phone = props.patient.emergency_phone ?? ''
      form.medical_history = props.patient.medical_history ?? ''
    }
    setTimeout(() => formRef.value?.clearValidate(), 0)
  }
})

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate((valid) => {
    if (valid) {
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
        payload.id = form.id
      }
      emit('submit', payload)
    }
  })
}
</script>

<style scoped>
.patient-form .el-select {
  width: 100%;
}
</style>
