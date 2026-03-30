<template>
  <section class="modules-page">
    <header class="hero-panel card">
      <div class="hero-copy">
        <span class="hero-eyebrow">Capability Registry</span>
        <h2>模块注册表</h2>
        <p>查看模块启停状态、版本、租户覆盖和权限规模，作为产品组合与版本发布的统一控制面板。</p>
      </div>

      <div class="hero-actions">
        <div class="hero-stat">
          <strong>{{ modules.length }}</strong>
          <span>注册模块</span>
        </div>
        <div class="hero-stat">
          <strong>{{ enabledCount }}</strong>
          <span>已启用模块</span>
        </div>
        <el-button :icon="Refresh" :loading="loading" @click="fetchModules">刷新注册表</el-button>
      </div>
    </header>

    <div class="summary-grid">
      <article class="summary-card card">
        <span class="summary-label">模块总使用量</span>
        <strong>{{ totalTenantUsage }}</strong>
        <p>所有模块在租户中的累计启用总和，可以直接看出能力面铺开的范围。</p>
      </article>
      <article class="summary-card card">
        <span class="summary-label">平均覆盖租户</span>
        <strong>{{ avgTenantsPerModule }}</strong>
        <p>反映模块平均触达面，过低通常意味着模块定位或授权策略有问题。</p>
      </article>
      <article class="summary-card card">
        <span class="summary-label">最热模块</span>
        <strong>{{ mostPopularModule }}</strong>
        <p>当前租户覆盖范围最大的模块，通常也是最强的商业抓手。</p>
      </article>
      <article class="summary-card card">
        <span class="summary-label">已禁用模块</span>
        <strong>{{ disabledCount }}</strong>
        <p>这些模块已停止向租户分配，适合结合版本计划继续清理。</p>
      </article>
    </div>

    <div class="control-bar card">
      <div class="control-field">
        <span>搜索模块</span>
        <el-input v-model="search" placeholder="模块名、slug 或描述" :prefix-icon="Search" clearable />
      </div>
      <div class="control-field">
        <span>状态筛选</span>
        <el-select v-model="statusFilter" placeholder="全部状态" clearable>
          <el-option label="已启用" value="enabled" />
          <el-option label="已禁用" value="disabled" />
        </el-select>
      </div>
      <div class="control-field">
        <span>排序方式</span>
        <el-select v-model="sortBy" placeholder="按名称排序">
          <el-option label="按名称" value="name" />
          <el-option label="按使用量" value="usage" />
          <el-option label="按版本" value="version" />
        </el-select>
      </div>
    </div>

    <div class="modules-grid">
      <article v-for="mod in filteredModules" :key="mod.slug" class="module-card">
        <div class="module-head">
          <div class="module-icon" :class="{ disabled: !mod.is_enabled }">
            <el-icon><Grid /></el-icon>
          </div>
          <div class="module-title">
            <div class="module-title-row">
              <h3>{{ mod.display_name }}</h3>
              <el-tag :type="mod.is_enabled ? 'success' : 'danger'" effect="dark" round>
                {{ mod.is_enabled ? '已启用' : '已禁用' }}
              </el-tag>
            </div>
            <code>{{ mod.slug }}</code>
          </div>
        </div>

        <p class="module-desc">{{ mod.description || '尚未补充模块说明。' }}</p>

        <div class="metric-grid">
          <div class="metric-pill">
            <span>租户覆盖</span>
            <strong>{{ mod.tenant_count }}</strong>
          </div>
          <div class="metric-pill">
            <span>权限数</span>
            <strong>{{ mod.permissions.length }}</strong>
          </div>
          <div class="metric-pill">
            <span>版本</span>
            <strong>v{{ mod.version }}</strong>
          </div>
        </div>

        <div class="module-section">
          <div class="section-title">
            <span>权限快照</span>
            <small>{{ mod.permissions.length }} 项</small>
          </div>
          <div class="module-cloud">
            <el-tag v-for="permission in mod.permissions.slice(0, 4)" :key="permission" round size="small">
              {{ permission }}
            </el-tag>
            <el-tag v-if="mod.permissions.length > 4" round size="small">
              +{{ mod.permissions.length - 4 }}
            </el-tag>
          </div>
        </div>

        <div class="module-section">
          <div class="section-title">
            <span>API 前缀</span>
          </div>
          <code class="api-prefix">{{ mod.router_prefix }}</code>
        </div>

        <footer class="module-footer">
          <div class="footer-actions">
            <el-button size="small" @click="viewDetail(mod)">详情</el-button>
            <el-button size="small" @click="viewStats(mod)">统计</el-button>
            <el-button size="small" type="primary" @click="openVersionEdit(mod)">版本</el-button>
          </div>
          <el-switch
            v-model="mod.is_enabled"
            inline-prompt
            :active-text="mod.is_enabled ? '启用' : '禁用'"
            :loading="toggling[mod.slug]"
            @change="toggleModule(mod)"
          />
        </footer>
      </article>

      <el-empty
        v-if="filteredModules.length === 0"
        description="没有符合条件的模块。"
        class="empty-block"
      />
    </div>

    <el-drawer v-model="showDetail" size="620px" destroy-on-close>
      <template #header>
        <div class="drawer-header">
          <span class="hero-eyebrow">Module Detail</span>
          <h3>{{ currentModule?.display_name || '模块详情' }}</h3>
        </div>
      </template>

      <div v-if="currentModule" class="detail-panel">
        <section class="detail-card card">
          <el-descriptions :column="1" border>
            <el-descriptions-item label="模块标识">{{ currentModule.slug }}</el-descriptions-item>
            <el-descriptions-item label="当前版本">v{{ currentModule.version }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="currentModule.is_enabled ? 'success' : 'danger'" round>
                {{ currentModule.is_enabled ? '已启用' : '已禁用' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="API 前缀">{{ currentModule.router_prefix }}</el-descriptions-item>
            <el-descriptions-item label="模块说明">{{ currentModule.description || '暂无说明' }}</el-descriptions-item>
          </el-descriptions>
        </section>

        <section class="detail-card card">
          <div class="detail-head">
            <h4>UI 元数据</h4>
          </div>
          <el-descriptions v-if="currentModule.ui_meta" :column="1" border>
            <el-descriptions-item label="图标">{{ currentModule.ui_meta.icon }}</el-descriptions-item>
            <el-descriptions-item label="路由">{{ currentModule.ui_meta.path }}</el-descriptions-item>
            <el-descriptions-item label="子导航">
              <el-tag
                v-for="child in currentModule.ui_meta.children"
                :key="child.path"
                round
                size="small"
              >
                {{ child.title }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
          <el-empty v-else description="未配置前端 UI 元数据" />
        </section>

        <section class="detail-card card">
          <div class="detail-head">
            <h4>权限列表</h4>
          </div>
          <div class="module-cloud">
            <el-tag v-for="permission in currentModule.permissions" :key="permission" round size="small">
              {{ permission }}
            </el-tag>
          </div>
        </section>
      </div>
    </el-drawer>

    <el-dialog v-model="showStats" width="560px" destroy-on-close>
      <template #header>
        <div class="dialog-header">
          <span class="hero-eyebrow">Module Analytics</span>
          <h3>{{ currentStats?.display_name || '模块统计' }}</h3>
        </div>
      </template>

      <div v-if="currentStats" class="stats-dialog">
        <div class="stats-grid">
          <article class="stats-box card">
            <span>活跃租户</span>
            <strong>{{ currentStats.active_tenants }}</strong>
          </article>
          <article class="stats-box card">
            <span>总租户数</span>
            <strong>{{ currentStats.total_tenants }}</strong>
          </article>
          <article class="stats-box card">
            <span>30 天新增</span>
            <strong>{{ currentStats.recent_activations }}</strong>
          </article>
        </div>
        <div ref="statsChartRef" class="chart-shell" />
      </div>
    </el-dialog>

    <el-dialog v-model="showVersionEdit" width="560px" destroy-on-close>
      <template #header>
        <div class="dialog-header">
          <span class="hero-eyebrow">Version Control</span>
          <h3>更新模块版本</h3>
          <p>{{ editingModule?.display_name }}</p>
        </div>
      </template>

      <el-form :model="versionForm" label-position="top" class="version-form">
        <el-form-item label="新版本号">
          <el-input v-model="versionForm.version" placeholder="例如：1.2.0" />
        </el-form-item>
        <el-form-item label="更新日志">
          <el-input
            v-model="versionForm.changelog"
            type="textarea"
            :rows="4"
            placeholder="说明本次版本更新内容"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showVersionEdit = false">取消</el-button>
        <el-button type="primary" :loading="savingVersion" @click="saveVersion">保存版本</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Grid, Refresh, Search } from '@element-plus/icons-vue'

import { modulesApi, type ModuleDetail, type ModuleInfo, type ModuleStats } from '@/api/modules'

type EChartsModule = typeof import('echarts')
type EChartsInstance = import('echarts').ECharts

const loading = ref(false)
const modules = ref<ModuleInfo[]>([])
const search = ref('')
const statusFilter = ref('')
const sortBy = ref('name')
const toggling = ref<Record<string, boolean>>({})

const showDetail = ref(false)
const currentModule = ref<ModuleDetail | null>(null)

const showStats = ref(false)
const currentStats = ref<ModuleStats | null>(null)
const statsChartRef = ref<HTMLElement | null>(null)
let echartsLib: EChartsModule | null = null
let statsChart: EChartsInstance | null = null

const showVersionEdit = ref(false)
const editingModule = ref<ModuleInfo | null>(null)
const savingVersion = ref(false)
const versionForm = ref({
  version: '',
  changelog: '',
})

const enabledCount = computed(() => modules.value.filter((module) => module.is_enabled).length)
const disabledCount = computed(() => modules.value.filter((module) => !module.is_enabled).length)
const totalTenantUsage = computed(() => modules.value.reduce((sum, module) => sum + module.tenant_count, 0))
const avgTenantsPerModule = computed(() => {
  if (modules.value.length === 0) return 0
  return Math.round((totalTenantUsage.value / modules.value.length) * 10) / 10
})
const mostPopularModule = computed(() => {
  if (modules.value.length === 0) return '暂无数据'
  return [...modules.value].sort((a, b) => b.tenant_count - a.tenant_count)[0]?.display_name || '暂无数据'
})

const filteredModules = computed(() => {
  let result = [...modules.value]

  if (search.value) {
    const keyword = search.value.toLowerCase()
    result = result.filter(
      (module) =>
        module.display_name.toLowerCase().includes(keyword) ||
        module.slug.toLowerCase().includes(keyword) ||
        (module.description || '').toLowerCase().includes(keyword),
    )
  }

  if (statusFilter.value === 'enabled') {
    result = result.filter((module) => module.is_enabled)
  } else if (statusFilter.value === 'disabled') {
    result = result.filter((module) => !module.is_enabled)
  }

  result.sort((left, right) => {
    switch (sortBy.value) {
      case 'usage':
        return right.tenant_count - left.tenant_count
      case 'version':
        return right.version.localeCompare(left.version)
      case 'name':
      default:
        return left.display_name.localeCompare(right.display_name)
    }
  })

  return result
})

async function fetchModules() {
  loading.value = true
  try {
    const res = await modulesApi.getModules(true)
    modules.value = res.data ?? []
  } catch {
    ElMessage.error('获取模块列表失败')
  } finally {
    loading.value = false
  }
}

async function viewDetail(module: ModuleInfo) {
  currentModule.value = null
  showDetail.value = true
  const res = await modulesApi.getModule(module.slug)
  currentModule.value = res.data
}

async function loadECharts() {
  if (!echartsLib) {
    echartsLib = await import('echarts')
  }
  return echartsLib
}

async function initStatsChart() {
  if (!statsChartRef.value || !currentStats.value) return
  const echarts = await loadECharts()
  statsChart?.dispose()
  statsChart = echarts.init(statsChartRef.value)
  statsChart.setOption({
    tooltip: { trigger: 'item' },
    color: ['#38bdf8', '#a78bfa'],
    series: [
      {
        type: 'pie',
        radius: ['42%', '74%'],
        data: [
          { value: currentStats.value.active_tenants, name: '活跃租户' },
          {
            value: Math.max(currentStats.value.total_tenants - currentStats.value.active_tenants, 0),
            name: '非活跃租户',
          },
        ],
        itemStyle: {
          borderColor: '#0f172a',
          borderWidth: 4,
        },
        label: { color: '#dbe4f0' },
      },
    ],
  })
}

async function viewStats(module: ModuleInfo) {
  currentStats.value = null
  showStats.value = true
  const res = await modulesApi.getModuleStats(module.slug)
  currentStats.value = res.data
  await nextTick()
  await initStatsChart()
}

async function toggleModule(module: ModuleInfo) {
  const targetStatus = !module.is_enabled
  try {
    await ElMessageBox.confirm(
      `确认${targetStatus ? '启用' : '禁用'}模块“${module.display_name}”？`,
      '模块状态变更',
      { type: 'warning' },
    )

    toggling.value[module.slug] = true
    await modulesApi.updateModuleStatus(module.slug, { is_enabled: targetStatus })
    module.is_enabled = targetStatus
    ElMessage.success('模块状态已更新')
  } catch {
    module.is_enabled = !targetStatus
  } finally {
    toggling.value[module.slug] = false
  }
}

function openVersionEdit(module: ModuleInfo) {
  editingModule.value = module
  versionForm.value = {
    version: module.version,
    changelog: '',
  }
  showVersionEdit.value = true
}

async function saveVersion() {
  if (!editingModule.value || !versionForm.value.version) {
    ElMessage.error('请输入版本号')
    return
  }

  savingVersion.value = true
  try {
    await modulesApi.updateModuleVersion(editingModule.value.slug, {
      version: versionForm.value.version,
      changelog: versionForm.value.changelog,
    })
    const target = modules.value.find((module) => module.slug === editingModule.value?.slug)
    if (target) {
      target.version = versionForm.value.version
    }
    ElMessage.success('模块版本已更新')
    showVersionEdit.value = false
  } finally {
    savingVersion.value = false
  }
}

onMounted(fetchModules)

onBeforeUnmount(() => {
  statsChart?.dispose()
})
</script>

<style scoped>
.modules-page {
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.hero-panel {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  padding: 26px 28px;
  background:
    radial-gradient(circle at top left, rgba(8, 145, 178, 0.22), transparent 24%),
    linear-gradient(135deg, rgba(15, 23, 42, 0.96), rgba(30, 41, 59, 0.92));
}

.hero-copy {
  max-width: 700px;
}

.hero-eyebrow,
.summary-label {
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
.dialog-header p {
  color: #a5b4cc;
}

.hero-actions {
  display: flex;
  gap: 14px;
  align-items: center;
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

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.summary-card {
  padding: 20px;
  background: linear-gradient(180deg, rgba(30, 41, 59, 0.92), rgba(15, 23, 42, 0.92));
}

.summary-card strong {
  display: block;
  margin: 10px 0 8px;
  font-size: 30px;
}

.summary-card p {
  font-size: 13px;
  color: #90a2bf;
}

.control-bar {
  display: grid;
  grid-template-columns: 1.5fr 220px 220px;
  gap: 14px;
  padding: 18px;
}

.control-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.control-field span {
  font-size: 13px;
  color: #94a3b8;
}

.modules-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
  gap: 18px;
}

.module-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 22px;
  border-radius: 24px;
  border: 1px solid rgba(148, 163, 184, 0.12);
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.94), rgba(30, 41, 59, 0.92));
  box-shadow: 0 18px 42px rgba(2, 6, 23, 0.24);
}

.module-head {
  display: flex;
  gap: 14px;
}

.module-icon {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  border-radius: 16px;
  color: #fff;
  background: linear-gradient(145deg, #06b6d4, #0284c7);
}

.module-icon.disabled {
  background: linear-gradient(145deg, #64748b, #475569);
}

.module-title {
  flex: 1;
  min-width: 0;
}

.module-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.module-title-row h3 {
  font-size: 22px;
  line-height: 1.1;
}

.module-title code {
  display: inline-block;
  margin-top: 8px;
  color: #94a3b8;
}

.module-desc {
  color: #a5b4cc;
  min-height: 44px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.metric-pill {
  padding: 12px;
  border-radius: 16px;
  background: rgba(15, 23, 42, 0.48);
  border: 1px solid rgba(148, 163, 184, 0.08);
}

.metric-pill span {
  display: block;
  font-size: 12px;
  color: #94a3b8;
}

.metric-pill strong {
  display: block;
  margin-top: 8px;
  font-size: 20px;
}

.module-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.section-title {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: #cbd5e1;
  font-size: 14px;
}

.section-title small {
  color: #94a3b8;
}

.module-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.api-prefix {
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(15, 23, 42, 0.58);
  color: #94a3b8;
}

.module-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-top: auto;
  padding-top: 14px;
  border-top: 1px solid rgba(148, 163, 184, 0.1);
}

.footer-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.empty-block {
  grid-column: 1 / -1;
  padding: 40px 0;
}

.drawer-header h3,
.dialog-header h3 {
  margin-top: 6px;
  font-size: 24px;
}

.detail-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.detail-card {
  padding: 20px;
}

.detail-head {
  margin-bottom: 12px;
}

.detail-head h4 {
  font-size: 18px;
}

.stats-dialog {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.stats-box {
  padding: 18px;
  text-align: center;
}

.stats-box span {
  display: block;
  color: #94a3b8;
  font-size: 12px;
}

.stats-box strong {
  display: block;
  margin-top: 10px;
  font-size: 30px;
}

.chart-shell {
  height: 260px;
}

@media (max-width: 1080px) {
  .summary-grid,
  .control-bar {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .hero-panel {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 760px) {
  .summary-grid,
  .control-bar,
  .metric-grid,
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .module-footer {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
