<template>
  <div class="module-page">
    <div class="page-head">
      <h2>生命体征</h2>
      <el-button type="primary" :icon="Plus">录入体征</el-button>
    </div>
    <div class="vitals-cards">
      <div v-for="v in vitals" :key="v.label" class="vital-card card">
        <div class="vital-icon" :style="{ background: v.color }">
          <el-icon size="22" color="white"><component :is="v.icon" /></el-icon>
        </div>
        <div>
          <div class="vital-val">{{ v.value }}</div>
          <div class="vital-label">{{ v.label }}</div>
          <el-tag size="small" :type="v.status">{{ v.statusText }}</el-tag>
        </div>
      </div>
    </div>
    <el-card><el-empty description="生命体征趋势图 — 连接后端后显示" /></el-card>
  </div>
</template>
<script setup lang="ts">
import { Plus } from '@element-plus/icons-vue'
type TagType = 'primary' | 'success' | 'warning' | 'info' | 'danger'

interface VitalItem {
  label: string
  value: string
  icon: string
  color: string
  status: TagType
  statusText: string
}

const vitals: VitalItem[] = [
  { label: '血压', value: '— mmHg', icon: 'Monitor', color: 'linear-gradient(135deg,#EF4444,#F59E0B)', status: 'info', statusText: '待录入' },
  { label: '心率', value: '— bpm', icon: 'Timer', color: 'linear-gradient(135deg,#3B82F6,#8B5CF6)', status: 'info', statusText: '待录入' },
  { label: '血糖', value: '— mmol/L', icon: 'Sugar', color: 'linear-gradient(135deg,#10B981,#3B82F6)', status: 'info', statusText: '待录入' },
  { label: '体温', value: '— °C', icon: 'Sunny', color: 'linear-gradient(135deg,#F59E0B,#EF4444)', status: 'info', statusText: '待录入' },
]
</script>
<style scoped>
.module-page { display: flex; flex-direction: column; gap: 20px; }
.page-head { display: flex; align-items: center; justify-content: space-between; }
.page-head h2 { font-size: 22px; font-weight: 700; }
.vitals-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; }
.vital-card { display: flex; align-items: center; gap: 16px; padding: 20px; }
.vital-icon { width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.vital-val { font-size: 22px; font-weight: 700; }
.vital-label { font-size: 12px; color: var(--text-secondary); margin-bottom: 4px; }
</style>
