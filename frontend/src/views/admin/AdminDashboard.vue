<template>
  <div class="admin-dashboard">
    <div class="page-header">
      <h2 class="page-title">运营总览</h2>
      <el-tag type="danger">平台超级管理员视图</el-tag>
    </div>

    <!-- Stats Cards -->
    <div class="stats-grid">
      <div v-for="stat in stats" :key="stat.label" class="stat-card card">
        <div class="stat-num" :style="{ color: stat.color }">{{ stat.value }}</div>
        <div class="stat-label">{{ stat.label }}</div>
        <div v-if="stat.trend !== undefined" class="stat-trend" :class="stat.trend >= 0 ? 'up' : 'down'">
          <el-icon><component :is="stat.trend >= 0 ? 'ArrowUp' : 'ArrowDown'" /></el-icon>
          {{ Math.abs(stat.trend) }}% 较上月
        </div>
      </div>
    </div>

    <!-- Charts Row -->
    <div class="charts-row">
      <el-card class="chart-card">
        <template #header>
          <div class="chart-header">
            <span>租户增长趋势</span>
            <el-radio-group v-model="timeRange" size="small">
              <el-radio-button value="7d">近7天</el-radio-button>
              <el-radio-button value="30d">近30天</el-radio-button>
              <el-radio-button value="90d">近90天</el-radio-button>
            </el-radio-group>
          </div>
        </template>
        <div ref="tenantChartRef" class="chart-container"></div>
      </el-card>

      <el-card class="chart-card">
        <template #header>
          <div class="chart-header">
            <span>模块使用分布</span>
          </div>
        </template>
        <div ref="moduleChartRef" class="chart-container"></div>
      </el-card>
    </div>

    <!-- Active modules list -->
    <div class="card modules-list">
      <div class="list-header">
        <h3>已注册业务模块</h3>
        <el-tag size="small">{{ moduleStore.allModules.length }} 个</el-tag>
      </div>
      <el-table :data="moduleStore.allModules" size="small" style="width: 100%">
        <el-table-column prop="slug" label="模块标识" width="180" />
        <el-table-column prop="display_name" label="显示名称" />
        <el-table-column prop="version" label="版本" width="80" />
        <el-table-column label="权限数" width="80">
          <template #default="{ row }">{{ row.permissions.length }}</template>
        </el-table-column>
        <el-table-column label="使用租户数" width="100">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ getModuleUsage(row.slug) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default>
            <el-tag size="small" type="success">已注册</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch, nextTick } from 'vue'
import { ArrowUp, ArrowDown } from '@element-plus/icons-vue'
import { useModuleStore } from '@/stores/modules'
import { platformApi, type PlatformStatsDetail } from '@/api/platform'
import * as echarts from 'echarts'

const moduleStore = useModuleStore()
const loading = ref(false)
const statsDetail = ref<PlatformStatsDetail | null>(null)
const timeRange = ref('30d')

// Chart refs
const tenantChartRef = ref<HTMLElement>()
const moduleChartRef = ref<HTMLElement>()
let tenantChart: echarts.ECharts | null = null
let moduleChart: echarts.ECharts | null = null

// Stats data
const stats = computed(() => {
  if (!statsDetail.value) {
    return [
      { label: '租户总数', value: '—', color: 'var(--brand-primary)', trend: 0 },
      { label: '激活租户', value: '—', color: 'var(--color-success)', trend: 0 },
      { label: '试用租户', value: '—', color: 'var(--color-warning)', trend: 0 },
      { label: '总用户数', value: '—', color: 'var(--brand-accent)', trend: 0 },
    ]
  }
  
  const { tenants, total_users } = statsDetail.value
  return [
    { 
      label: '租户总数', 
      value: tenants.total.toString(), 
      color: 'var(--brand-primary)',
      trend: Math.round((tenants.new_this_month / Math.max(tenants.total - tenants.new_this_month, 1)) * 100)
    },
    { 
      label: '激活租户', 
      value: tenants.active.toString(), 
      color: 'var(--color-success)',
      trend: 12
    },
    { 
      label: '试用租户', 
      value: tenants.trial.toString(), 
      color: 'var(--color-warning)',
      trend: -5
    },
    { 
      label: '总用户数', 
      value: total_users.toString(), 
      color: 'var(--brand-accent)',
      trend: 8
    },
  ]
})

// Get module usage count
const getModuleUsage = (slug: string) => {
  if (!statsDetail.value?.modules) return 0
  return statsDetail.value.modules[slug] || 0
}

// Initialize charts
const initCharts = () => {
  if (tenantChartRef.value) {
    tenantChart = echarts.init(tenantChartRef.value)
    updateTenantChart()
  }
  if (moduleChartRef.value) {
    moduleChart = echarts.init(moduleChartRef.value)
    updateModuleChart()
  }
}

// Update tenant growth chart
const updateTenantChart = () => {
  if (!tenantChart) return
  
  // Generate mock data based on time range
  const days = timeRange.value === '7d' ? 7 : timeRange.value === '30d' ? 30 : 90
  const dates: string[] = []
  const data: number[] = []
  const now = new Date()
  
  for (let i = days - 1; i >= 0; i--) {
    const date = new Date(now)
    date.setDate(date.getDate() - i)
    dates.push(date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }))
    data.push(Math.floor(Math.random() * 5) + (statsDetail.value?.tenants.total || 0) / days)
  }
  
  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: { rotate: days > 30 ? 45 : 0 }
    },
    yAxis: {
      type: 'value',
      minInterval: 1
    },
    series: [{
      name: '新增租户',
      type: 'bar',
      data: data,
      itemStyle: {
        color: 'var(--brand-primary)',
        borderRadius: [4, 4, 0, 0]
      }
    }]
  }
  
  tenantChart.setOption(option)
}

// Update module usage chart
const updateModuleChart = () => {
  if (!moduleChart || !statsDetail.value?.modules) return
  
  const modules = statsDetail.value.modules
  const data = Object.entries(modules)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8)
  
  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} 租户 ({d}%)'
    },
    legend: {
      orient: 'vertical',
      right: 10,
      top: 'center',
      textStyle: { fontSize: 11 }
    },
    series: [{
      name: '模块使用',
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['35%', '50%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 6,
        borderColor: '#fff',
        borderWidth: 2
      },
      label: {
        show: false
      },
      emphasis: {
        label: {
          show: true,
          fontSize: 12,
          fontWeight: 'bold'
        }
      },
      data: data.length > 0 ? data : [
        { name: '患者管理', value: 10 },
        { name: '认知评估', value: 8 },
        { name: '健康监测', value: 5 },
        { name: 'AI智能助理', value: 3 },
      ]
    }]
  }
  
  moduleChart.setOption(option)
}

// Fetch data
const fetchData = async () => {
  loading.value = true
  try {
    const res = await platformApi.getStatsDetail()
    statsDetail.value = res.data
    await nextTick()
    updateModuleChart()
  } catch (error) {
    console.error('Failed to fetch stats:', error)
  } finally {
    loading.value = false
  }
}

// Watch time range changes
watch(timeRange, () => {
  updateTenantChart()
})

// Handle resize
const handleResize = () => {
  tenantChart?.resize()
  moduleChart?.resize()
}

onMounted(() => {
  fetchData()
  initCharts()
  window.addEventListener('resize', handleResize)
})
</script>

<style scoped>
.admin-dashboard { display: flex; flex-direction: column; gap: 24px; }
.page-header { display: flex; align-items: center; gap: 12px; }
.page-title { font-size: 24px; font-weight: 700; }

.stats-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; }
.stat-card { padding: 24px; text-align: center; }
.stat-num { font-size: 36px; font-weight: 800; }
.stat-label { font-size: 13px; color: var(--text-secondary); margin-top: 6px; }
.stat-trend { 
  font-size: 12px; 
  margin-top: 8px; 
  display: flex; 
  align-items: center; 
  justify-content: center; 
  gap: 4px;
}
.stat-trend.up { color: var(--color-success); }
.stat-trend.down { color: var(--color-danger); }

.charts-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }
.chart-card { min-height: 350px; }
.chart-header { display: flex; justify-content: space-between; align-items: center; }
.chart-container { height: 280px; }

.modules-list { padding: 20px; }
.list-header { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
.list-header h3 { font-size: 16px; font-weight: 700; }
</style>
