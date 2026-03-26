<template>
  <el-skeleton animated :rows="3" v-if="loading" />
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
</template>

<script setup lang="ts">
import type { Assessment } from '@/api/assessments'

defineProps<{
  assessments: Assessment[]
  loading: boolean
}>()

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
</script>

<style scoped>
.timeline-card { border-radius: var(--radius-md); padding: 4px; }
.timeline-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.timeline-head h4 { font-size: 16px; font-weight: 600; color: var(--text-primary); }
.focus-score { color: var(--brand-primary); font-size: 18px; margin-left: 8px; }
.timeline-text { margin-bottom: 6px; font-size: 14px; color: var(--text-secondary); }
</style>
