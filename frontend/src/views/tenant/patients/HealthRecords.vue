<template>
  <div class="dossier-page">
    <div class="page-head">
      <div class="head-left">
        <el-button icon="Back" circle plain @click="$router.push('/patients/list')" />
        <h2>长者健康档案</h2>
      </div>
      <!-- Patient Selector if navigated from the menu directly rather than button -->
      <div class="head-right" v-if="!loadingPatient">
        <el-select
          v-model="activePatientId"
          filterable
          placeholder="搜索或切换长者档案..."
          @change="loadPatientData"
          style="width: 280px"
        >
          <el-option
            v-for="p in patientList"
            :key="p.id"
            :label="`${p.full_name} (${p.room_number || '待分配'})`"
            :value="p.id"
          />
        </el-select>
      </div>
    </div>

    <template v-if="activePatient">
      <el-row :gutter="20">
        <!-- Sidebar Profile Card -->
        <el-col :span="6">
          <el-card class="profile-card" shadow="never">
            <div class="avatar-box">
              <el-avatar :size="80" style="background: var(--brand-primary); font-size: 32px">
                {{ activePatient.full_name?.[0] || '?' }}
              </el-avatar>
              <h3>{{ activePatient.full_name }}</h3>
              <el-tag :type="activePatient.gender === 'M' ? 'primary' : 'danger'" effect="plain">
                {{ activePatient.gender === 'M' ? '爷爷' : activePatient.gender === 'F' ? '奶奶' : '未知' }}
              </el-tag>
            </div>
            
            <div class="meta-list">
              <div class="meta-item">
                <span class="label">年龄</span>
                <span class="val">{{ activePatient.age || '未知' }} 岁</span>
              </div>
              <div class="meta-item">
                <span class="label">房间排床</span>
                <span class="val">{{ activePatient.room_number || '-' }} - {{ activePatient.bed_number || '-' }}</span>
              </div>
              <div class="meta-item">
                <span class="label">联系方式</span>
                <span class="val">{{ activePatient.contact_phone || '无记录' }}</span>
              </div>
              <div class="meta-item">
                <span class="label">紧急联系人</span>
                <span class="val">{{ activePatient.emergency_contact || '无记录' }} ({{ activePatient.emergency_phone || '-' }})</span>
              </div>
              <div class="meta-item">
                <span class="label">身份证号</span>
                <span class="val">{{ activePatient.id_card_num || '无记录' }}</span>
              </div>
              <div class="meta-item">
                <span class="label">入驻日期</span>
                <span class="val">{{ activePatient.created_at?.split('T')[0] || '-' }}</span>
              </div>
            </div>
          </el-card>
        </el-col>

        <!-- Main Content Area -->
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
                <el-skeleton animated :rows="3" v-if="loadingAssessments" />
                <el-empty v-else-if="!assessments.length" description="该长者尚未进行过脑健康评估量表登记" />
                <el-timeline v-else style="padding: 10px 0;">
                  <el-timeline-item
                    v-for="ass in assessments"
                    :key="ass.id"
                    :timestamp="ass.evaluation_date"
                    :type="getTimelineType(ass.status_diagnosis)"
                    size="large"
                  >
                    <el-card shadow="hover" class="timeline-card">
                      <div class="timeline-head">
                        <h4>{{ ass.assessment_type }} 测试评分：<span class="focus-score">{{ ass.total_score }} 分</span></h4>
                        <el-tag :type="getTimelineType(ass.status_diagnosis)" effect="dark">{{ formatStatus(ass.status_diagnosis) }}</el-tag>
                      </div>
                      <p class="timeline-text"><strong>评估人:</strong> {{ ass.evaluator_name || '未知' }}</p>
                      <p class="timeline-text" v-if="ass.remarks"><strong>诊断备注:</strong> {{ ass.remarks }}</p>
                    </el-card>
                  </el-timeline-item>
                </el-timeline>
              </el-tab-pane>
              
              <!-- Placeholder for next development Phase -->
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

const route = useRoute()

// State
const loadingPatient = ref(false)
const patientList = ref<Patient[]>([])
const activePatientId = ref<string>('')
const activePatient = ref<Patient | null>(null)
const activeTab = ref('history')

// Assessment Tab Data
const loadingAssessments = ref(false)
const assessments = ref<Assessment[]>([])

async function loadInitialData() {
  loadingPatient.value = true
  try {
    // 1. Fetch available patients
    const res = await patientsApi.list({ page: 1, size: 1000 })
    patientList.value = (res as any).data.items
    
    // 2. Check if navigated directly with patient ID
    const queryId = route.query.patient_id as string
    if (queryId && patientList.value.some(p => p.id === queryId)) {
      activePatientId.value = queryId
      await loadPatientData()
    } else if (patientList.value.length > 0) {
      // Default to first user if just clicking "Health Records" casually
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
  
  // Set Current Profile
  const match = patientList.value.find(p => p.id === activePatientId.value)
  if (match) activePatient.value = match
  else return
  
  // Fetch specific assessment timelines
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

// Helpers
function formatStatus(status: string) {
  const map: Record<string, string> = {
    NORMAL: '认知正常',
    MCI: '轻度损害 (MCI)',
    MILD: '轻微痴呆',
    MODERATE: '中度痴呆',
    SEVERE: '重度痴呆'
  }
  return map[status] || status
}

function getTimelineType(status: string) {
  switch (status) {
    case 'NORMAL': return 'success'
    case 'MCI': return 'warning'
    case 'MILD': return 'danger'
    case 'MODERATE': return 'danger'
    case 'SEVERE': return 'danger'
    default: return 'info'
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

.profile-card { height: 100%; text-align: center; }
.avatar-box { margin-bottom: 24px; }
.avatar-box h3 { margin: 12px 0 6px; font-size: 18px; font-weight: 600; }

.meta-list { text-align: left; }
.meta-item {
  display: flex;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px dashed var(--border-subtle);
}
.meta-item:last-child { border-bottom: none; }
.meta-item .label { color: var(--text-secondary); font-size: 14px; }
.meta-item .val { font-weight: 500; font-size: 14px; color: var(--text-primary); max-width: 60%; text-align: right; }

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

.timeline-card { border-radius: var(--radius-md); padding: 4px; }
.timeline-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.timeline-head h4 { font-size: 16px; font-weight: 600; color: var(--text-primary); }
.focus-score { color: var(--brand-primary); font-size: 18px; margin-left: 8px; }
.timeline-text { margin-bottom: 6px; font-size: 14px; color: var(--text-secondary); }

.empty-layout { margin-top: 100px; }
</style>
