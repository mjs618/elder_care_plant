<template>
  <div class="admin-page">
    <div class="page-head">
      <div class="head-left">
        <h2>模块注册表</h2>
        <el-tag type="info">共 {{ modules.length }} 个模块</el-tag>
        <el-tag v-if="enabledCount > 0" type="success">{{ enabledCount }} 个启用</el-tag>
        <el-tag v-if="disabledCount > 0" type="danger">{{ disabledCount }} 个禁用</el-tag>
      </div>
      <div class="head-right">
        <el-button :icon="Refresh" @click="fetchModules" :loading="loading">刷新</el-button>
      </div>
    </div>

    <!-- Module Stats Overview -->
    <div class="stats-row">
      <el-card class="stat-card" shadow="never">
        <div class="stat-value">{{ totalTenantUsage }}</div>
        <div class="stat-label">模块总使用次数</div>
      </el-card>
      <el-card class="stat-card" shadow="never">
        <div class="stat-value">{{ avgTenantsPerModule }}</div>
        <div class="stat-label">平均每模块租户数</div>
      </el-card>
      <el-card class="stat-card" shadow="never">
        <div class="stat-value">{{ mostPopularModule }}</div>
        <div class="stat-label">最热门模块</div>
      </el-card>
    </div>

    <!-- Filter Bar -->
    <div class="filter-bar">
      <el-input v-model="search" placeholder="搜索模块名称..." :prefix-icon="Search" style="width: 280px" clearable />
      <el-select v-model="statusFilter" placeholder="状态筛选" style="width: 140px" clearable>
        <el-option label="全部" value="" />
        <el-option label="已启用" value="enabled" />
        <el-option label="已禁用" value="disabled" />
      </el-select>
      <el-select v-model="sortBy" placeholder="排序方式" style="width: 160px">
        <el-option label="按名称" value="name" />
        <el-option label="按使用数" value="usage" />
        <el-option label="按版本" value="version" />
      </el-select>
    </div>

    <!-- Modules Grid -->
    <div class="modules-grid">
      <div v-for="mod in filteredModules" :key="mod.slug" class="mod-card card" :class="{ disabled: !mod.is_enabled }">
        <div class="mod-head">
          <div class="mod-icon" :class="{ disabled: !mod.is_enabled }">
            <el-icon size="22" color="white"><Grid /></el-icon>
          </div>
          <div class="mod-title">
            <div class="mod-name">{{ mod.display_name }}</div>
            <code class="mod-slug">{{ mod.slug }}</code>
          </div>
          <div class="mod-badges">
            <el-tag size="small" :type="mod.is_enabled ? 'success' : 'danger'" effect="dark">
              {{ mod.is_enabled ? '已启用' : '已禁用' }}
            </el-tag>
            <el-tag size="small" type="info" class="mod-ver">v{{ mod.version }}</el-tag>
          </div>
        </div>

        <p class="mod-desc">{{ mod.description }}</p>

        <!-- Usage Stats -->
        <div class="mod-usage">
          <div class="usage-item">
            <el-icon><User /></el-icon>
            <span>{{ mod.tenant_count }} 个租户使用</span>
          </div>
          <div class="usage-item">
            <el-icon><Lock /></el-icon>
            <span>{{ mod.permissions.length }} 个权限</span>
          </div>
        </div>

        <!-- Permissions -->
        <div class="mod-perms">
          <span class="perms-label">权限：</span>
          <el-tag v-for="p in mod.permissions.slice(0, 3)" :key="p" size="small" type="info" class="perm-tag">
            {{ p }}
          </el-tag>
          <el-tag v-if="mod.permissions.length > 3" size="small" type="info">+{{ mod.permissions.length - 3 }}</el-tag>
        </div>

        <!-- API Info -->
        <div class="mod-api">
          <code class="api-path">{{ mod.router_prefix }}</code>
        </div>

        <!-- Actions -->
        <div class="mod-actions">
          <el-button size="small" @click="viewDetail(mod)">详情</el-button>
          <el-button size="small" @click="viewStats(mod)">统计</el-button>
          <el-button size="small" type="primary" @click="openVersionEdit(mod)">版本</el-button>
          <el-switch
            v-model="mod.is_enabled"
            :active-text="mod.is_enabled ? '启用' : '禁用'"
            inline-prompt
            :loading="toggling[mod.slug]"
            @change="toggleModule(mod)"
          />
        </div>
      </div>

      <el-empty v-if="filteredModules.length === 0" description="暂无模块数据" />
    </div>

    <!-- Detail Drawer -->
    <el-drawer v-model="showDetail" title="模块详情" size="600px">
      <div v-if="currentModule" class="module-detail">
        <div class="detail-section">
          <h4>基本信息</h4>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="模块标识">{{ currentModule.slug }}</el-descriptions-item>
            <el-descriptions-item label="显示名称">{{ currentModule.display_name }}</el-descriptions-item>
            <el-descriptions-item label="当前版本">v{{ currentModule.version }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="currentModule.is_enabled ? 'success' : 'danger'">
                {{ currentModule.is_enabled ? '已启用' : '已禁用' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="API前缀">{{ currentModule.router_prefix }}</el-descriptions-item>
            <el-descriptions-item label="描述">{{ currentModule.description }}</el-descriptions-item>
          </el-descriptions>
        </div>

        <div class="detail-section">
          <h4>UI配置</h4>
          <el-descriptions :column="1" border v-if="currentModule.ui_meta">
            <el-descriptions-item label="图标">{{ currentModule.ui_meta.icon }}</el-descriptions-item>
            <el-descriptions-item label="路径">{{ currentModule.ui_meta.path }}</el-descriptions-item>
            <el-descriptions-item label="子菜单">
              <el-tag v-for="child in currentModule.ui_meta.children" :key="child.path" size="small" style="margin: 2px;">
                {{ child.title }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
          <el-empty v-else description="无UI配置" />
        </div>

        <div class="detail-section">
          <h4>权限列表</h4>
          <div class="perm-list">
            <el-tag v-for="perm in currentModule.permissions" :key="perm" size="small" type="info" style="margin: 4px;">
              {{ perm }}
            </el-tag>
          </div>
        </div>
      </div>
    </el-drawer>

    <!-- Stats Dialog -->
    <el-dialog v-model="showStats" title="模块使用统计" width="500px">
      <div v-if="currentStats" class="stats-content">
        <div class="stat-row">
          <div class="stat-item">
            <div class="stat-num">{{ currentStats.active_tenants }}</div>
            <div class="stat-label">活跃租户</div>
          </div>
          <div class="stat-item">
            <div class="stat-num">{{ currentStats.total_tenants }}</div>
            <div class="stat-label">总租户数</div>
          </div>
          <div class="stat-item">
            <div class="stat-num">{{ currentStats.recent_activations }}</div>
            <div class="stat-label">近30天新增</div>
          </div>
        </div>
        <el-divider />
        <div class="stats-chart">
          <div ref="statsChartRef" class="chart-container"></div>
        </div>
      </div>
    </el-dialog>

    <!-- Version Edit Dialog -->
    <el-dialog v-model="showVersionEdit" title="更新模块版本" width="500px">
      <div v-if="editingModule" class="version-edit">
        <p class="edit-subtitle">模块：<strong>{{ editingModule.display_name }}</strong></p>
        <p class="edit-subtitle">当前版本：v{{ editingModule.version }}</p>

        <el-form :model="versionForm" label-width="100px">
          <el-form-item label="新版本号" required>
            <el-input v-model="versionForm.version" placeholder="例如：1.2.0" />
          </el-form-item>
          <el-form-item label="更新日志">
            <el-input
              v-model="versionForm.changelog"
              type="textarea"
              :rows="4"
              placeholder="描述本次版本更新的内容..."
            />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="showVersionEdit = false">取消</el-button>
        <el-button type="primary" :loading="savingVersion" @click="saveVersion">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { Grid, Search, Refresh, User, Lock } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { modulesApi, type ModuleInfo, type ModuleDetail, type ModuleStats } from '@/api/modules'
import * as echarts from 'echarts'

const loading = ref(false)
const modules = ref<ModuleInfo[]>([])
const search = ref('')
const statusFilter = ref('')
const sortBy = ref('name')
const toggling = ref<Record<string, boolean>>({})

// Detail drawer
const showDetail = ref(false)
const currentModule = ref<ModuleDetail | null>(null)

// Stats dialog
const showStats = ref(false)
const currentStats = ref<ModuleStats | null>(null)
const statsChartRef = ref<HTMLElement>()
let statsChart: echarts.ECharts | null = null

// Version edit
const showVersionEdit = ref(false)
const editingModule = ref<ModuleInfo | null>(null)
const savingVersion = ref(false)
const versionForm = ref({
  version: '',
  changelog: ''
})

// Computed stats
const enabledCount = computed(() => modules.value.filter(m => m.is_enabled).length)
const disabledCount = computed(() => modules.value.filter(m => !m.is_enabled).length)
const totalTenantUsage = computed(() => modules.value.reduce((sum, m) => sum + m.tenant_count, 0))
const avgTenantsPerModule = computed(() => {
  if (modules.value.length === 0) return 0
  return Math.round(totalTenantUsage.value / modules.value.length)
})
const mostPopularModule = computed(() => {
  if (modules.value.length === 0) return '-'
  const popular = modules.value.reduce((max, m) => m.tenant_count > max.tenant_count ? m : max, modules.value[0])
  return popular?.display_name || '-'
})

// Filtered and sorted modules
const filteredModules = computed(() => {
  let result = [...modules.value]

  // Search filter
  if (search.value) {
    const keyword = search.value.toLowerCase()
    result = result.filter(m =>
      m.display_name.toLowerCase().includes(keyword) ||
      m.slug.toLowerCase().includes(keyword) ||
      m.description.toLowerCase().includes(keyword)
    )
  }

  // Status filter
  if (statusFilter.value === 'enabled') {
    result = result.filter(m => m.is_enabled)
  } else if (statusFilter.value === 'disabled') {
    result = result.filter(m => !m.is_enabled)
  }

  // Sort
  result.sort((a, b) => {
    switch (sortBy.value) {
      case 'usage':
        return b.tenant_count - a.tenant_count
      case 'version':
        return b.version.localeCompare(a.version)
      case 'name':
      default:
        return a.display_name.localeCompare(b.display_name)
    }
  })

  return result
})

async function fetchModules() {
  loading.value = true
  try {
    const res = await modulesApi.getModules(true)
    modules.value = res.data ?? []
  } catch (error) {
    console.error('Failed to fetch modules:', error)
    ElMessage.error('获取模块列表失败')
  } finally {
    loading.value = false
  }
}

async function viewDetail(mod: ModuleInfo) {
  currentModule.value = null
  showDetail.value = true
  try {
    const res = await modulesApi.getModule(mod.slug)
    currentModule.value = res.data
  } catch (error) {
    ElMessage.error('获取模块详情失败')
  }
}

async function viewStats(mod: ModuleInfo) {
  currentStats.value = null
  showStats.value = true
  try {
    const res = await modulesApi.getModuleStats(mod.slug)
    currentStats.value = res.data
    await nextTick()
    initStatsChart()
  } catch (error) {
    ElMessage.error('获取模块统计失败')
  }
}

async function toggleModule(mod: ModuleInfo) {
  const newStatus = !mod.is_enabled
  const action = newStatus ? '启用' : '禁用'

  try {
    await ElMessageBox.confirm(
      `确认${action}模块 "${mod.display_name}"？`,
      '确认操作',
      { type: 'warning' }
    )

    toggling.value[mod.slug] = true
    await modulesApi.updateModuleStatus(mod.slug, { is_enabled: newStatus })
    ElMessage.success(`模块已${action}`)
    mod.is_enabled = newStatus
  } catch (e) {
    // Cancelled or error, revert the switch
    mod.is_enabled = !newStatus
  } finally {
    toggling.value[mod.slug] = false
  }
}

function initStatsChart() {
  if (!statsChartRef.value || !currentStats.value) return

  statsChart = echarts.init(statsChartRef.value)

  const option: echarts.EChartsOption = {
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: [
        { value: currentStats.value.active_tenants, name: '活跃租户' },
        { value: currentStats.value.total_tenants - currentStats.value.active_tenants, name: '非活跃租户' }
      ],
      itemStyle: {
        borderRadius: 6,
        borderColor: '#fff',
        borderWidth: 2
      }
    }]
  }

  statsChart.setOption(option)
}

function openVersionEdit(mod: ModuleInfo) {
  editingModule.value = mod
  versionForm.value = {
    version: mod.version,
    changelog: ''
  }
  showVersionEdit.value = true
}

async function saveVersion() {
  if (!editingModule.value) return

  if (!versionForm.value.version) {
    ElMessage.error('请输入版本号')
    return
  }

  savingVersion.value = true
  try {
    await modulesApi.updateModuleVersion(editingModule.value.slug, {
      version: versionForm.value.version,
      changelog: versionForm.value.changelog
    })
    ElMessage.success('版本更新成功')
    showVersionEdit.value = false

    // Update local data
    const mod = modules.value.find(m => m.slug === editingModule.value?.slug)
    if (mod) {
      mod.version = versionForm.value.version
    }
  } catch (error) {
    console.error('Failed to update version:', error)
    ElMessage.error('版本更新失败')
  } finally {
    savingVersion.value = false
  }
}

onMounted(() => {
  fetchModules()
})
</script>

<style scoped>
.admin-page { display: flex; flex-direction: column; gap: 20px; }

.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.head-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.head-left h2 { font-size: 22px; font-weight: 700; }

.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.stat-card {
  text-align: center;
  padding: 20px;
}

.stat-card .stat-value {
  font-size: 28px;
  font-weight: 800;
  color: var(--brand-primary);
}

.stat-card .stat-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 8px;
}

.filter-bar {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.modules-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px;
}

.mod-card {
  padding: 20px;
  transition: all 0.3s;
}

.mod-card.disabled {
  opacity: 0.7;
  background: var(--bg-muted);
}

.mod-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.mod-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-md);
  flex-shrink: 0;
  background: linear-gradient(135deg, var(--brand-primary), var(--brand-accent));
  display: flex;
  align-items: center;
  justify-content: center;
}

.mod-icon.disabled {
  background: linear-gradient(135deg, #9ca3af, #6b7280);
}

.mod-title { flex: 1; min-width: 0; }

.mod-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

.mod-slug {
  font-size: 12px;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.mod-badges {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: flex-end;
}

.mod-ver { font-family: var(--font-mono); }

.mod-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 12px;
  line-height: 1.5;
  min-height: 40px;
}

.mod-usage {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
  padding: 8px 0;
  border-top: 1px solid var(--border-subtle);
  border-bottom: 1px solid var(--border-subtle);
}

.usage-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);
}

.mod-perms {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
  margin-bottom: 12px;
}

.perms-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-right: 4px;
}

.perm-tag {
  font-family: var(--font-mono);
  font-size: 11px;
}

.mod-api {
  margin-bottom: 12px;
}

.api-path {
  font-size: 12px;
  color: var(--text-muted);
  background: var(--bg-muted);
  padding: 4px 8px;
  border-radius: var(--radius-sm);
}

.mod-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: flex-end;
  padding-top: 12px;
  border-top: 1px solid var(--border-subtle);
}

/* Detail Drawer Styles */
.module-detail { padding: 20px; }

.detail-section { margin-bottom: 24px; }

.detail-section h4 {
  font-size: 14px;
  font-weight: 700;
  margin-bottom: 12px;
  color: var(--text-primary);
}

.perm-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

/* Stats Dialog Styles */
.stats-content { padding: 20px; }

.stat-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  text-align: center;
}

.stat-item .stat-num {
  font-size: 32px;
  font-weight: 800;
  color: var(--brand-primary);
}

.stat-item .stat-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.chart-container {
  height: 200px;
  margin-top: 20px;
}

/* Version Edit Styles */
.version-edit { padding: 10px 0; }

.edit-subtitle {
  margin-bottom: 16px;
  color: var(--text-secondary);
  font-size: 14px;
}
</style>
