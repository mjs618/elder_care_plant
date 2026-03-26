<template>
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
        <el-button type="primary" link icon="EditPen" @click="$emit('edit', row)">查看/编辑</el-button>
        <el-popconfirm title="确定要删除该条记录吗？" @confirm="$emit('delete', row.id)">
          <template #reference>
            <el-button type="danger" link icon="Delete">删除</el-button>
          </template>
        </el-popconfirm>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup lang="ts">
import type { Assessment } from '@/api/assessments'

defineProps<{
  assessments: Assessment[]
  loading: boolean
}>()

defineEmits<{
  'edit': [assessment: Assessment]
  'delete': [id: string]
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
  if (row.total_score === null || row.total_score === undefined) return ''
  if (row.assessment_type === 'MMSE') {
    if (row.total_score >= 27) return 'color-good'
    if (row.total_score >= 24) return ''
    return 'color-bad'
  }
  return ''
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
.color-good {
  color: var(--el-color-success);
}
.color-bad {
  color: var(--el-color-danger);
}
</style>
