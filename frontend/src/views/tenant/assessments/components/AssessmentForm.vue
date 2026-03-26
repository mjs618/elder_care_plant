<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    :title="isEdit ? '编辑评估报告' : '新建量表评估'"
    width="650px"
    destroy-on-close
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="100px" label-position="right">
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
          <el-radio-button value="MMSE">简易精神量表(MMSE)</el-radio-button>
          <el-radio-button value="MoCA">蒙特利尔评分(MoCA)</el-radio-button>
          <el-radio-button value="CDR">临床痴呆评定(CDR)</el-radio-button>
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
              <el-option label="正常" value="NORMAL" />
              <el-option label="轻度认知障碍 (MCI)" value="MCI" />
              <el-option label="轻度痴呆" value="MILD" />
              <el-option label="中度痴呆" value="MODERATE" />
              <el-option label="重度痴呆" value="SEVERE" />
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
        <el-button @click="$emit('update:visible', false)">取消</el-button>
        <el-button type="primary" :loading="loading" @click="handleSubmit">保存记录</el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch, computed } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import type { Assessment } from '@/api/assessments'
import type { Patient } from '@/api/patients'

const props = defineProps<{
  visible: boolean
  assessment: Assessment | null
  patientOptions: Patient[]
  loading: boolean
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'submit': [data: Record<string, any>]
}>()

const formRef = ref<FormInstance>()

interface AssessmentFormModel {
  patient_id: string
  assessment_type: 'MMSE' | 'MoCA' | 'CDR' | 'OTHER'
  evaluation_date: string
  total_score: number | null
  status_diagnosis: string
  evaluator_name: string
  remarks: string
}

function createInitialForm(): AssessmentFormModel {
  return {
    patient_id: '',
    assessment_type: 'MMSE',
    evaluation_date: new Date().toISOString().split('T')[0],
    total_score: null,
    status_diagnosis: 'NORMAL',
    evaluator_name: '',
    remarks: ''
  }
}

const form = reactive<AssessmentFormModel>(createInitialForm())

const rules = reactive<FormRules>({
  patient_id: [{ required: true, message: '请选择评估对象', trigger: 'change' }],
  status_diagnosis: [{ required: true, message: '请评估认知等级', trigger: 'change' }]
})

const isEdit = computed(() => !!props.assessment)

watch(() => props.visible, (val) => {
  if (val) {
    Object.assign(form, createInitialForm())
    if (props.assessment) {
      form.patient_id = props.assessment.patient_id
      form.assessment_type = props.assessment.assessment_type
      form.evaluation_date = props.assessment.evaluation_date
      form.total_score = props.assessment.total_score
      form.status_diagnosis = props.assessment.status_diagnosis
      form.evaluator_name = props.assessment.evaluator_name ?? ''
      form.remarks = props.assessment.remarks ?? ''
    }
    setTimeout(() => formRef.value?.clearValidate(), 0)
  }
})

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate((valid) => {
    if (valid) {
      const payload: Record<string, any> = { ...form }
      emit('submit', payload)
    }
  })
}
</script>

<style scoped>
.patient-link {
  font-weight: 600;
  color: var(--text-primary);
}
.score-display {
  font-weight: 700;
}
</style>
