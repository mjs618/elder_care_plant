<template>
  <div class="dossier-page">
    <div class="page-head">
      <div class="head-left">
        <el-button icon="Back" circle plain @click="$router.push('/patients/list')" />
        <h2>长者健康档案</h2>
      </div>
      <div class="head-right" v-if="!loadingPatient">
        <PatientSelector
          v-model="activePatientId"
          :patients="patientList"
          @update:model-value="loadPatientData"
        />
      </div>
    </div>

    <template v-if="activePatient">
      <el-row :gutter="20">
        <el-col :span="6">
          <PatientProfileCard :patient="activePatient" />
        </el-col>

        <el-col :span="18">
          <el-card shadow="never" class="content-card">
            <el-tabs v-model="activeTab" class="dossier-tabs">
              <el-tab-pane label="既往病史与备注" name="history">
                <div class="empty-state" v-if="!activePatient.medical_history">
                  <el-empty description="该长者暂无详细病史记录" :image-size="80" />
                </div>
                <div class="history-content" v-else>
                  <p class="history-text">{{ activePatient.medical_history }}</p>
                </div>
              </el-tab-pane>
              
              <el-tab-pane label="认知评估报告 (MMSE / MoCA)" name="assessments">
                <AssessmentTimeline
                  :assessments="assessments"
                  :loading="loadingAssessments"
                />
              </el-tab-pane>
              
              <el-tab-pane label="生命体征追踪" name="vitals">
                <el-empty description="健康监测大屏与设备对接正在接入中..." />
                <div style="text-align: center;">
                  <el-button type="primary" plain @click="$router.push('/health/vitals')">跳转生命体征大屏</el-button>
                </div>
              </el-tab-pane>
            </el-tabs>
          </el-card>
        </el-col>
      </el-row>
    </template>
    
    <div v-else class="empty-layout">
      <el-empty description="在左侧下拉框中选择一位长者以查看全维档案，或从患者列表页进入" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { patientsApi, type Patient } from '@/api/patients'
import { assessmentsApi, type Assessment } from '@/api/assessments'
import PatientSelector from './components/PatientSelector.vue'
import PatientProfileCard from './components/PatientProfileCard.vue'
import AssessmentTimeline from './components/AssessmentTimeline.vue'

const route = useRoute()

const loadingPatient = ref(false)
const patientList = ref<Patient[]>([])
const activePatientId = ref<string>('')
const activePatient = ref<Patient | null>(null)
const activeTab = ref('history')

const loadingAssessments = ref(false)
const assessments = ref<Assessment[]>([])

async function loadInitialData() {
  loadingPatient.value = true
  try {
    const res = await patientsApi.list({ page: 1, size: 100 })
    patientList.value = (res as any).data.items
    
    const queryId = route.query.patient_id as string
    if (queryId && patientList.value.some(p => p.id === queryId)) {
      activePatientId.value = queryId
      await loadPatientData()
    } else if (patientList.value.length > 0) {
      activePatientId.value = patientList.value[0].id
      await loadPatientData()
    }
  } catch (e) {
    console.error(e)
  } finally {
    loadingPatient.value = false
  }
}

async function loadPatientData() {
  if (!activePatientId.value) return
  
  const match = patientList.value.find(p => p.id === activePatientId.value)
  if (match) activePatient.value = match
  else return
  
  loadingAssessments.value = true
  try {
    const res = await assessmentsApi.list({ patient_id: activePatientId.value, page: 1, size: 50 })
    assessments.value = (res as any).data.items
  } catch (e) {
    console.error('Fetch assessments failed', e)
  } finally {
    loadingAssessments.value = false
  }
}

onMounted(() => {
  loadInitialData()
})
</script>

<style scoped>
.dossier-page { display: flex; flex-direction: column; gap: 20px; }
.page-head { 
  display: flex; align-items: center; justify-content: space-between; 
}
.head-left { display: flex; align-items: center; gap: 16px; }
.head-left h2 { font-size: 20px; font-weight: 700; color: var(--text-primary); }

.content-card { min-height: 500px; }
.history-text {
  font-size: 15px;
  line-height: 1.8;
  color: var(--text-primary);
  background: var(--bg-surface);
  padding: 24px;
  border-radius: var(--radius-md);
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);
  white-space: pre-wrap;
}

.empty-layout { margin-top: 100px; }
</style>
