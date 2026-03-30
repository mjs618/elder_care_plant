<template>
  <section class="dashboard-page">
    <header class="hero-panel card">
      <div class="hero-copy">
        <span class="hero-eyebrow">Operations Radar</span>
        <h2>平台运营总览</h2>
        <p>
          把租户增长、账号规模和模块热度收束到一块面板里，便于平台管理员快速判断增长质量与交付压力。
        </p>
      </div>

      <div class="hero-actions">
        <div class="hero-stat">
          <strong>{{ statsDetail?.total_users ?? 0 }}</strong>
          <span>租户侧账号</span>
        </div>
        <div class="hero-stat">
          <strong>{{ moduleStore.allModules.length }}</strong>
          <span>已注册模块</span>
        </div>
        <el-radio-group v-model="timeRange" size="large" class="range-switch">
          <el-radio-button :value="7">7 天</el-radio-button>
          <el-radio-button :value="30">30 天</el-radio-button>
          <el-radio-button :value="90">90 天</el-radio-button>
        </el-radio-group>
      </div>
    </header>

    <div class="stats-grid">
      <article v-for="stat in stats" :key="stat.label" class="stat-card card">
        <div class="stat-head">
          <span>{{ stat.label }}</span>
          <div class="stat-chip" :style="{ color: stat.color, background: `${stat.color}22` }">
            <el-icon><component :is="stat.icon" /></el-icon>
          </div>
        </div>
        <strong class="stat-value">{{ stat.value }}</strong>
        <p>{{ stat.description }}</p>
        <div class="stat-trend" :class="{ negative: stat.trend < 0 }">
          <el-icon><component :is="stat.trend >= 0 ? ArrowUp : ArrowDown" /></el-icon>
          <span>{{ formatTrend(stat.trend) }}</span>
        </div>
      </article>
    </div>

    <div class="insight-grid">
      <section class="chart-card card">
        <div class="section-head">
          <div>
            <span class="section-eyebrow">Growth Curve</span>
            <h3>租户增长轨迹</h3>
          </div>
          <p>上方折线展示累计租户规模，下方柱状展示每天新增，趋势完全来自真实租户创建数据。</p>
        </div>
        <div ref="tenantChartRef" class="chart-shell" v-loading="loading" />
      </section>

      <section class="chart-card card">
        <div class="section-head">
          <div>
            <span class="section-eyebrow">Module Adoption</span>
            <h3>模块使用分布</h3>
          </div>
          <p>按启用租户数量观察能力覆盖面，能快速识别主销模块和边缘模块。</p>
        </div>
        <div ref="moduleChartRef" class="chart-shell" v-loading="loading" />
      </section>
    </div>

    <div class="lower-grid">
      <section class="spotlight-card card">
        <div class="section-head">
          <div>
            <span class="section-eyebrow">Focus</span>
            <h3>运营焦点</h3>
          </div>
        </div>

        <div class="spotlight-list">
          <article class="spotlight-item">
            <span>活跃租户占比</span>
            <strong>{{ activeRatio }}%</strong>
            <small>活跃租户 / 全部租户</small>
          </article>
          <article class="spotlight-item">
            <span>试用转化窗口</span>
            <strong>{{ statsDetail?.tenants.trial ?? 0 }}</strong>
            <small>当前试用租户仍需运营跟进</small>
          </article>
          <article class="spotlight-item">
            <span>最热模块</span>
            <strong>{{ hottestModule.name }}</strong>
            <small>{{ hottestModule.value }} 个租户正在使用</small>
          </article>
        </div>
      </section>

      <section class="registry-card card">
        <div class="section-head">
          <div>
            <span class="section-eyebrow">Registry</span>
            <h3>模块注册表快照</h3>
          </div>
          <el-tag round>{{ moduleStore.allModules.length }} 个模块</el-tag>
        </div>

        <div class="module-rows">
          <div v-for="module in moduleStore.allModules" :key="module.slug" class="module-row">
            <div class="module-primary">
              <strong>{{ module.display_name }}</strong>
              <span>{{ module.slug }}</span>
            </div>
            <div class="module-secondary">
              <span>{{ getModuleUsage(module.slug) }} 个租户</span>
              <el-tag round size="small">{{ module.permissions.length }} 项权限</el-tag>
            </div>
          </div>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  ArrowDown,
  ArrowUp,
  DataAnalysis,
  Files,
  OfficeBuilding,
  User,
} from '@element-plus/icons-vue'

import { platformApi, type PlatformStatsDetail } from '@/api/platform'
import { useModuleStore } from '@/stores/modules'

type EChartsModule = typeof import('echarts')
type EChartsInstance = import('echarts').ECharts

const moduleStore = useModuleStore()
const loading = ref(false)
const statsDetail = ref<PlatformStatsDetail | null>(null)
const timeRange = ref<7 | 30 | 90>(30)

const tenantChartRef = ref<HTMLElement | null>(null)
const moduleChartRef = ref<HTMLElement | null>(null)

let echartsLib: EChartsModule | null = null
let tenantChart: EChartsInstance | null = null
let moduleChart: EChartsInstance | null = null

const tenantSeries = computed(() => statsDetail.value?.tenant_series ?? [])

const tenantTrend = computed(() => {
  const series = tenantSeries.value
  if (series.length < 2) return 0
  const midpoint = Math.max(Math.floor(series.length / 2), 1)
  const previous = series.slice(0, midpoint).reduce((sum, item) => sum + item.new_tenants, 0)
  const current = series.slice(midpoint).reduce((sum, item) => sum + item.new_tenants, 0)
  return ratioTrend(current, previous)
})

const stats = computed(() => {
  const tenants = statsDetail.value?.tenants
  const totalUsers = statsDetail.value?.total_users ?? 0
  const totalTenants = tenants?.total ?? 0
  const activeTenants = tenants?.active ?? 0
  const trialTenants = tenants?.trial ?? 0
  const suspendedTenants = tenants?.suspended ?? 0

  return [
    {
      label: '租户总数',
      value: totalTenants.toString(),
      trend: tenantTrend.value,
      color: '#60a5fa',
      icon: OfficeBuilding,
      description: '平台当前已建立的租户数量',
    },
    {
      label: '活跃租户',
      value: activeTenants.toString(),
      trend: ratioTrend(activeTenants, Math.max(totalTenants - activeTenants, 0)),
      color: '#34d399',
      icon: DataAnalysis,
      description: '处于可正常运营状态的租户',
    },
    {
      label: '试用租户',
      value: trialTenants.toString(),
      trend: -ratioTrend(trialTenants, Math.max(totalTenants - trialTenants, 0)),
      color: '#fbbf24',
      icon: Files,
      description: '仍处在试用窗口、最值得跟进的租户',
    },
    {
      label: '暂停租户',
      value: suspendedTenants.toString(),
      trend: -ratioTrend(suspendedTenants, Math.max(totalTenants - suspendedTenants, 0)),
      color: '#f472b6',
      icon: User,
      description: `租户侧总账号 ${totalUsers} 个，可联动排查交付和留存`,
    },
  ]
})

const hottestModule = computed(() => {
  const moduleMap = statsDetail.value?.modules ?? {}
  const entries = Object.entries(moduleMap)
  if (entries.length === 0) {
    return { name: '暂无数据', value: 0 }
  }

  const [slug, value] = entries.sort((a, b) => b[1] - a[1])[0]
  const displayName =
    moduleStore.allModules.find((module) => module.slug === slug)?.display_name || slug
  return { name: displayName, value }
})

const activeRatio = computed(() => {
  const total = statsDetail.value?.tenants.total ?? 0
  const active = statsDetail.value?.tenants.active ?? 0
  if (total === 0) return 0
  return Math.round((active / total) * 100)
})

function ratioTrend(current: number, previous: number) {
  if (current === 0 && previous === 0) return 0
  if (previous === 0) return 100
  return Math.round(((current - previous) / previous) * 100)
}

function formatTrend(value: number) {
  const prefix = value >= 0 ? '+' : '-'
  return `${prefix}${Math.abs(value)}%`
}

function getModuleUsage(slug: string) {
  return statsDetail.value?.modules?.[slug] || 0
}

function formatSeriesDate(date: string) {
  return new Date(date).toLocaleDateString('zh-CN', {
    month: 'numeric',
    day: 'numeric',
  })
}

async function loadECharts() {
  if (!echartsLib) {
    echartsLib = await import('echarts')
  }
  return echartsLib
}

async function initCharts() {
  const echarts = await loadECharts()

  if (tenantChartRef.value && !tenantChart) {
    tenantChart = echarts.init(tenantChartRef.value)
  }

  if (moduleChartRef.value && !moduleChart) {
    moduleChart = echarts.init(moduleChartRef.value)
  }
}

async function updateTenantChart() {
  if (!statsDetail.value) return
  await initCharts()
  if (!tenantChart || !echartsLib) return

  const series = tenantSeries.value
  const dates = series.map((point) => formatSeriesDate(point.date))
  const totals = series.map((point) => point.total_tenants)
  const newTenants = series.map((point) => point.new_tenants)

  tenantChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: {
      top: 0,
      textStyle: { color: '#cbd5e1' },
    },
    grid: { left: 24, right: 18, top: 48, bottom: 26, containLabel: true },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.16)' } },
      axisLabel: { color: '#94a3b8' },
    },
    yAxis: [
      {
        type: 'value',
        minInterval: 1,
        splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.08)' } },
        axisLabel: { color: '#94a3b8' },
      },
      {
        type: 'value',
        minInterval: 1,
        splitLine: { show: false },
        axisLabel: { color: '#94a3b8' },
      },
    ],
    series: [
      {
        name: '累计租户',
        type: 'line',
        smooth: true,
        yAxisIndex: 0,
        symbol: 'circle',
        symbolSize: 7,
        data: totals,
        lineStyle: {
          width: 4,
          color: '#60a5fa',
        },
        itemStyle: {
          color: '#60a5fa',
          borderColor: '#0f172a',
          borderWidth: 2,
        },
        areaStyle: {
          color: new echartsLib.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(96, 165, 250, 0.35)' },
            { offset: 1, color: 'rgba(96, 165, 250, 0.02)' },
          ]),
        },
      },
      {
        name: '每日新增',
        type: 'bar',
        yAxisIndex: 1,
        barMaxWidth: 16,
        data: newTenants,
        itemStyle: {
          color: '#38bdf8',
          borderRadius: [8, 8, 0, 0],
        },
      },
    ],
  })
}

async function updateModuleChart() {
  await initCharts()
  if (!moduleChart) return

  const data = Object.entries(statsDetail.value?.modules ?? {})
    .map(([slug, value]) => ({
      name: moduleStore.allModules.find((module) => module.slug === slug)?.display_name || slug,
      value,
    }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 6)

  moduleChart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: '{b}<br/>{c} 个租户',
    },
    series: [
      {
        type: 'pie',
        radius: ['38%', '74%'],
        center: ['50%', '52%'],
        avoidLabelOverlap: false,
        label: {
          show: true,
          color: '#dbe4f0',
          formatter: '{b}',
        },
        labelLine: {
          lineStyle: { color: 'rgba(148, 163, 184, 0.34)' },
        },
        itemStyle: {
          borderWidth: 4,
          borderColor: '#0f172a',
        },
        data,
      },
    ],
    color: ['#38bdf8', '#34d399', '#f59e0b', '#f472b6', '#a78bfa', '#fb7185'],
  })
}

async function renderCharts() {
  await nextTick()
  await updateTenantChart()
  await updateModuleChart()
}

async function fetchData() {
  loading.value = true
  try {
    const res = await platformApi.getStatsDetail(timeRange.value)
    statsDetail.value = res.data
    await renderCharts()
  } finally {
    loading.value = false
  }
}

function handleResize() {
  tenantChart?.resize()
  moduleChart?.resize()
}

watch(timeRange, () => {
  fetchData()
})

watch(
  () => statsDetail.value,
  () => {
    renderCharts()
  },
)

onMounted(async () => {
  await fetchData()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  tenantChart?.dispose()
  moduleChart?.dispose()
})
</script>

<style scoped>
.dashboard-page {
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.hero-panel {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  padding: 26px 28px;
  background:
    radial-gradient(circle at top left, rgba(59, 130, 246, 0.22), transparent 26%),
    radial-gradient(circle at bottom right, rgba(244, 63, 94, 0.16), transparent 18%),
    linear-gradient(135deg, rgba(15, 23, 42, 0.96), rgba(30, 41, 59, 0.92));
}

.hero-copy {
  max-width: 680px;
}

.hero-eyebrow,
.section-eyebrow {
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: #94a3b8;
}

.hero-copy h2 {
  margin: 8px 0 10px;
  font-size: 34px;
}

.hero-copy p,
.section-head p {
  color: #a5b4cc;
}

.hero-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 14px;
  flex-wrap: wrap;
}

.hero-stat {
  min-width: 120px;
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  background: rgba(15, 23, 42, 0.64);
}

.hero-stat strong {
  display: block;
  font-size: 28px;
  line-height: 1;
}

.hero-stat span {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  color: #90a2bf;
}

.range-switch {
  border-radius: 999px;
  overflow: hidden;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.stat-card {
  padding: 20px;
  background: linear-gradient(180deg, rgba(30, 41, 59, 0.92), rgba(15, 23, 42, 0.92));
}

.stat-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  color: #94a3b8;
  font-size: 13px;
}

.stat-chip {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 14px;
}

.stat-value {
  display: block;
  margin: 18px 0 10px;
  font-size: 36px;
  line-height: 1;
}

.stat-card p {
  color: #90a2bf;
  font-size: 13px;
}

.stat-trend {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 14px;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(34, 197, 94, 0.12);
  color: #86efac;
}

.stat-trend.negative {
  background: rgba(239, 68, 68, 0.12);
  color: #fca5a5;
}

.insight-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 0.95fr);
  gap: 18px;
}

.chart-card,
.spotlight-card,
.registry-card {
  padding: 22px;
}

.section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.section-head h3 {
  margin-top: 6px;
  font-size: 24px;
}

.chart-shell {
  height: 330px;
}

.lower-grid {
  display: grid;
  grid-template-columns: 360px minmax(0, 1fr);
  gap: 18px;
}

.spotlight-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.spotlight-item {
  padding: 16px 18px;
  border-radius: 18px;
  background: rgba(15, 23, 42, 0.5);
  border: 1px solid rgba(148, 163, 184, 0.1);
}

.spotlight-item span,
.spotlight-item small {
  color: #94a3b8;
}

.spotlight-item strong {
  display: block;
  margin: 10px 0 6px;
  font-size: 30px;
}

.module-rows {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.module-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 16px;
  border-radius: 18px;
  background: rgba(15, 23, 42, 0.48);
  border: 1px solid rgba(148, 163, 184, 0.08);
}

.module-primary {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.module-primary strong {
  font-size: 15px;
}

.module-primary span {
  color: #94a3b8;
  font-size: 12px;
}

.module-secondary {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #c8d4e8;
}

@media (max-width: 1180px) {
  .stats-grid,
  .lower-grid,
  .insight-grid {
    grid-template-columns: 1fr;
  }

  .hero-panel {
    flex-direction: column;
  }

  .hero-actions {
    justify-content: flex-start;
  }
}

@media (max-width: 760px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
