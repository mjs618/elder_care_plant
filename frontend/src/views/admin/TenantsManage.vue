<template>
  <section class="tenants-page">
    <header class="hero-panel card">
      <div class="hero-copy">
        <span class="hero-eyebrow">Tenant Operations</span>
        <h2>租户舰桥</h2>
        <p>集中查看租户状态、套餐归属、品牌配置和模块开通情况，处理续费、停用和模块授权都会更直接。</p>
      </div>

      <div class="hero-actions">
        <div class="hero-stat">
          <strong>{{ statsDetail?.tenants.total ?? total }}</strong>
          <span>平台租户总量</span>
        </div>
        <div class="hero-stat">
          <strong>{{ statsDetail?.tenants.active ?? 0 }}</strong>
          <span>活跃租户</span>
        </div>
        <el-button type="primary" size="large" :icon="Plus" @click="showCreate = true">
          新建租户
        </el-button>
      </div>
    </header>

    <div class="summary-grid">
      <article class="summary-card card">
        <span class="summary-label">试用中</span>
        <strong>{{ statusCounts.trial }}</strong>
        <p>建议重点跟进试用期即将结束的机构，尽快推动转化或回收成本。</p>
      </article>
      <article class="summary-card card">
        <span class="summary-label">已暂停</span>
        <strong>{{ statusCounts.suspended }}</strong>
        <p>这类租户通常需要核查欠费、风控或人工停用原因。</p>
      </article>
      <article class="summary-card card">
        <span class="summary-label">已取消</span>
        <strong>{{ statusCounts.cancelled }}</strong>
        <p>适合与流失原因一起分析，判断产品组合与续费策略是否失衡。</p>
      </article>
      <article class="summary-card card">
        <span class="summary-label">筛选命中</span>
        <strong>{{ visibleTenantCount }}</strong>
        <p>这里展示的是当前搜索和状态条件下，真实命中的后端分页总量。</p>
      </article>
    </div>

    <div class="control-bar card">
      <div class="control-field">
        <span>搜索租户</span>
        <el-input v-model="search" placeholder="按名称、slug 或邮箱搜索" :prefix-icon="Search" clearable />
      </div>
      <div class="control-field">
        <span>状态筛选</span>
        <el-select v-model="statusFilter" placeholder="全部状态" clearable>
          <el-option label="活跃" value="active" />
          <el-option label="试用" value="trial" />
          <el-option label="暂停" value="suspended" />
          <el-option label="取消" value="cancelled" />
        </el-select>
      </div>
      <div class="control-actions">
        <el-button :icon="Refresh" @click="refreshAll">刷新列表</el-button>
      </div>
    </div>

    <section class="tenant-board card">
      <div class="board-head">
        <div>
          <h3>租户列表</h3>
          <p>当前筛选命中 {{ total }} 个租户，本页展示 {{ tenants.length }} 个。</p>
        </div>
      </div>

      <el-table :data="tenants" v-loading="loading" class="tenant-table">
        <el-table-column label="租户" min-width="260">
          <template #default="{ row }">
            <div class="tenant-cell">
              <div
                class="tenant-mark"
                :style="{ background: row.primary_color || tenantMark(row.status) }"
              >
                {{ row.name.slice(0, 1).toUpperCase() }}
              </div>
              <div class="tenant-meta">
                <strong>{{ row.name }}</strong>
                <span>{{ row.slug }}</span>
                <small>{{ row.plan?.name || '未分配套餐' }} · {{ formatDate(row.created_at, false) }}</small>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="contact_email" label="联系邮箱" min-width="220" />

        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" round>{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="操作" min-width="320" fixed="right">
          <template #default="{ row }">
            <div class="table-actions">
              <el-button size="small" @click="viewDetail(row)">详情</el-button>
              <el-button size="small" type="primary" @click="openEdit(row)">编辑</el-button>
              <el-button size="small" @click="openModules(row)">模块</el-button>
              <el-dropdown>
                <el-button size="small">
                  更多
                  <el-icon class="el-icon--right"><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item
                      v-if="row.status !== 'active'"
                      @click="handleStatusChange(row, 'active')"
                    >
                      设为活跃
                    </el-dropdown-item>
                    <el-dropdown-item
                      v-if="row.status !== 'suspended'"
                      @click="handleStatusChange(row, 'suspended')"
                    >
                      暂停租户
                    </el-dropdown-item>
                    <el-dropdown-item
                      v-if="row.status !== 'cancelled'"
                      @click="handleStatusChange(row, 'cancelled')"
                    >
                      取消租户
                    </el-dropdown-item>
                    <el-dropdown-item divided @click="handleDelete(row)">
                      删除租户
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="board-footer">
        <el-pagination
          v-model:current-page="page"
          :total="total"
          :page-size="pageSize"
          layout="total, prev, pager, next"
          @current-change="fetchTenants"
        />
      </div>
    </section>

    <el-dialog v-model="showCreate" width="620px" destroy-on-close>
      <template #header>
        <div class="dialog-header">
          <span class="hero-eyebrow">Create Tenant</span>
          <h3>新建租户</h3>
        </div>
      </template>

      <el-form
        ref="createFormRef"
        :model="createForm"
        label-position="top"
        :rules="formRules"
        class="tenant-form"
      >
        <div class="form-grid">
          <el-form-item label="机构名称" prop="name">
            <el-input v-model="createForm.name" placeholder="例如：阳光养老院" />
          </el-form-item>
          <el-form-item label="Slug" prop="slug">
            <el-input v-model="createForm.slug" placeholder="例如：sunshine-care" />
          </el-form-item>
        </div>
        <div class="form-grid">
          <el-form-item label="联系邮箱" prop="contact_email">
            <el-input v-model="createForm.contact_email" type="email" />
          </el-form-item>
          <el-form-item label="套餐" prop="plan_id">
            <el-select v-model="createForm.plan_id" placeholder="选择套餐" style="width: 100%">
              <el-option v-for="plan in plans" :key="plan.id" :label="plan.name" :value="plan.id" />
            </el-select>
          </el-form-item>
        </div>
      </el-form>

      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="createTenant">创建租户</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showEdit" width="620px" destroy-on-close>
      <template #header>
        <div class="dialog-header">
          <span class="hero-eyebrow">Edit Tenant</span>
          <h3>编辑租户</h3>
        </div>
      </template>

      <el-form ref="editFormRef" :model="editForm" label-position="top" class="tenant-form">
        <div class="form-grid">
          <el-form-item label="机构名称">
            <el-input v-model="editForm.name" />
          </el-form-item>
          <el-form-item label="联系邮箱">
            <el-input v-model="editForm.contact_email" type="email" />
          </el-form-item>
        </div>
        <div class="form-grid">
          <el-form-item label="品牌名称">
            <el-input v-model="editForm.brand_name" placeholder="例如：长青护理" />
          </el-form-item>
          <el-form-item label="套餐">
            <el-select v-model="editForm.plan_id" placeholder="选择套餐" style="width: 100%">
              <el-option v-for="plan in plans" :key="plan.id" :label="plan.name" :value="plan.id" />
            </el-select>
          </el-form-item>
        </div>

        <el-form-item label="品牌主色">
          <div class="color-field">
            <el-color-picker v-model="editForm.primary_color" />
            <span>{{ editForm.primary_color || '未设置' }}</span>
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showEdit = false">取消</el-button>
        <el-button type="primary" :loading="editing" @click="updateTenant">保存修改</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="showDetail" size="620px" destroy-on-close>
      <template #header>
        <div class="drawer-header">
          <span class="hero-eyebrow">Tenant Profile</span>
          <h3>{{ currentTenant?.name || '租户详情' }}</h3>
        </div>
      </template>

      <div v-if="currentTenant" class="detail-panel">
        <section class="detail-card card">
          <div class="detail-card-head">
            <div
              class="tenant-mark tenant-mark--large"
              :style="{ background: currentTenant.primary_color || tenantMark(currentTenant.status) }"
            >
              {{ currentTenant.name.slice(0, 1).toUpperCase() }}
            </div>
            <div>
              <h4>{{ currentTenant.name }}</h4>
              <p>{{ currentTenant.slug }}</p>
            </div>
          </div>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="联系邮箱">
              {{ currentTenant.contact_email }}
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="statusTagType(currentTenant.status)" round>
                {{ statusLabel(currentTenant.status) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="品牌名称">
              {{ currentTenant.brand_name || '未设置' }}
            </el-descriptions-item>
            <el-descriptions-item label="创建时间">
              {{ formatDate(currentTenant.created_at, true) }}
            </el-descriptions-item>
          </el-descriptions>
        </section>

        <section class="detail-grid">
          <article class="mini-detail card">
            <span>套餐</span>
            <strong>{{ currentTenant.plan?.name || '未配置' }}</strong>
            <small>{{ tierLabel(currentTenant.plan?.tier) }}</small>
          </article>
          <article class="mini-detail card">
            <span>用户数</span>
            <strong>{{ currentTenant.user_count }}</strong>
            <small>租户当前账号总量</small>
          </article>
          <article class="mini-detail card">
            <span>已开通模块</span>
            <strong>{{ currentTenant.active_modules?.length || 0 }}</strong>
            <small>可直接判断功能边界和交付范围</small>
          </article>
        </section>

        <section class="detail-card card">
          <div class="detail-section-head">
            <h4>已开通模块</h4>
          </div>
          <div class="module-cloud">
            <el-tag v-for="slug in currentTenant.active_modules" :key="slug" round>
              {{ getModuleName(slug) }}
            </el-tag>
            <span v-if="!currentTenant.active_modules?.length" class="empty-hint">暂无开通模块</span>
          </div>
        </section>
      </div>
    </el-drawer>

    <el-dialog v-model="showModules" width="680px" destroy-on-close>
      <template #header>
        <div class="dialog-header">
          <span class="hero-eyebrow">Module Assignment</span>
          <h3>租户模块配置</h3>
          <p>{{ currentTenant?.name || '正在加载租户信息' }}</p>
        </div>
      </template>

      <el-checkbox-group v-model="selectedModules" class="module-selector">
        <label v-for="module in allModules" :key="module.slug" class="module-option">
          <el-checkbox :label="module.slug">{{ module.display_name }}</el-checkbox>
          <small>{{ module.slug }}</small>
        </label>
      </el-checkbox-group>

      <template #footer>
        <el-button @click="showModules = false">取消</el-button>
        <el-button type="primary" :loading="savingModules" @click="saveModules">保存配置</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowDown, Plus, Refresh, Search } from '@element-plus/icons-vue'

import { platformApi, type Plan, type PlatformStatsDetail } from '@/api/platform'
import { tenantsApi, type Tenant, type TenantDetail, type TenantStatus } from '@/api/tenants'
import { useModuleStore } from '@/stores/modules'

const moduleStore = useModuleStore()
const allModules = computed(() => moduleStore.allModules)

const tenants = ref<Tenant[]>([])
const statsDetail = ref<PlatformStatsDetail | null>(null)
const loading = ref(false)
const search = ref('')
const statusFilter = ref<TenantStatus | ''>('')
const page = ref(1)
const pageSize = 20
const total = ref(0)
const plans = ref<Plan[]>([])

const showCreate = ref(false)
const creating = ref(false)
const createFormRef = ref()
const createForm = reactive({
  name: '',
  slug: '',
  contact_email: '',
  plan_id: '',
})

const showEdit = ref(false)
const editing = ref(false)
const editFormRef = ref()
const editForm = reactive({
  name: '',
  contact_email: '',
  brand_name: '',
  primary_color: '',
  plan_id: '',
})
const editingTenantId = ref('')

const showDetail = ref(false)
const currentTenant = ref<TenantDetail | null>(null)

const showModules = ref(false)
const savingModules = ref(false)
const selectedModules = ref<string[]>([])

let searchTimer: ReturnType<typeof setTimeout> | null = null

const formRules = {
  name: [{ required: true, message: '请输入机构名称', trigger: 'blur' }],
  slug: [{ required: true, message: '请输入 slug', trigger: 'blur' }],
  contact_email: [
    { required: true, message: '请输入联系邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效邮箱地址', trigger: 'blur' },
  ],
  plan_id: [{ required: true, message: '请选择套餐', trigger: 'change' }],
}

const statusCounts = computed(() => ({
  active: statsDetail.value?.tenants.active ?? 0,
  trial: statsDetail.value?.tenants.trial ?? 0,
  suspended: statsDetail.value?.tenants.suspended ?? 0,
  cancelled: statsDetail.value?.tenants.cancelled ?? 0,
}))

const visibleTenantCount = computed(() => total.value)

async function fetchTenants(targetPage: number = page.value) {
  page.value = targetPage
  loading.value = true
  try {
    const res = await tenantsApi.getTenants(page.value, pageSize, {
      search: search.value.trim() || undefined,
      status: statusFilter.value || undefined,
    })
    tenants.value = res.data?.items ?? []
    total.value = res.data?.total ?? 0
  } catch {
    tenants.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

async function fetchSummary() {
  try {
    const res = await platformApi.getStatsDetail(30)
    statsDetail.value = res.data
  } catch {
    statsDetail.value = null
  }
}

async function fetchPlans() {
  try {
    const res = await platformApi.getPlans()
    plans.value = res.data ?? []
  } catch {
    plans.value = []
  }
}

async function refreshAll() {
  await Promise.all([fetchTenants(page.value), fetchSummary(), fetchPlans()])
}

async function createTenant() {
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return

  creating.value = true
  try {
    await tenantsApi.createTenant(createForm)
    ElMessage.success('租户创建成功')
    showCreate.value = false
    createFormRef.value?.resetFields()
    await refreshAll()
  } finally {
    creating.value = false
  }
}

async function viewDetail(row: Tenant) {
  currentTenant.value = null
  showDetail.value = true
  const res = await tenantsApi.getTenant(row.id)
  currentTenant.value = res.data
}

async function openEdit(row: Tenant) {
  const detail = await tenantsApi.getTenant(row.id)
  const tenant = detail.data
  editingTenantId.value = tenant.id
  editForm.name = tenant.name
  editForm.contact_email = tenant.contact_email
  editForm.brand_name = tenant.brand_name || ''
  editForm.primary_color = tenant.primary_color || ''
  editForm.plan_id = tenant.plan?.id || ''
  showEdit.value = true
}

async function updateTenant() {
  editing.value = true
  try {
    await tenantsApi.updateTenant(editingTenantId.value, {
      name: editForm.name,
      contact_email: editForm.contact_email,
      brand_name: editForm.brand_name,
      primary_color: editForm.primary_color || undefined,
      plan_id: editForm.plan_id || undefined,
    })
    ElMessage.success('租户更新成功')
    showEdit.value = false
    await refreshAll()
  } finally {
    editing.value = false
  }
}

async function handleStatusChange(tenant: Tenant, status: Exclude<TenantStatus, 'trial'>) {
  const actionLabel = {
    active: '设为活跃',
    suspended: '暂停',
    cancelled: '取消',
  }[status]

  try {
    await ElMessageBox.confirm(`确认对租户“${tenant.name}”执行“${actionLabel}”？`, '租户状态变更', {
      type: 'warning',
    })
    await tenantsApi.updateTenantStatus(tenant.id, { status })
    ElMessage.success('租户状态已更新')
    await refreshAll()
  } catch {
    // ignore cancel
  }
}

async function handleDelete(tenant: Tenant) {
  try {
    await ElMessageBox.confirm(`确认删除租户“${tenant.name}”？此操作不可恢复。`, '删除租户', {
      type: 'warning',
    })
    await tenantsApi.deleteTenant(tenant.id)
    ElMessage.success('租户已删除')
    await refreshAll()
  } catch {
    // ignore cancel
  }
}

async function openModules(tenant: Tenant) {
  currentTenant.value = null
  selectedModules.value = []
  showModules.value = true
  const res = await tenantsApi.getTenant(tenant.id)
  currentTenant.value = res.data
  selectedModules.value = res.data.active_modules ?? []
}

async function saveModules() {
  if (!currentTenant.value) return
  savingModules.value = true
  try {
    await tenantsApi.updateTenantModules(currentTenant.value.id, {
      module_slugs: selectedModules.value,
    })
    ElMessage.success('模块配置已保存')
    showModules.value = false
    await refreshAll()
  } finally {
    savingModules.value = false
  }
}

function statusLabel(status: string) {
  return {
    active: '活跃',
    trial: '试用',
    suspended: '暂停',
    cancelled: '取消',
  }[status] ?? status
}

function statusTagType(
  status: string,
): 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined {
  const map: Record<string, 'primary' | 'success' | 'warning' | 'info' | 'danger'> = {
    active: 'success',
    trial: 'warning',
    suspended: 'danger',
    cancelled: 'info',
  }
  return map[status]
}

function tierLabel(tier?: string | null) {
  return {
    free: '免费版',
    standard: '标准版',
    enterprise: '企业版',
  }[tier || ''] ?? '未配置'
}

function getModuleName(slug: string) {
  return allModules.value.find((module) => module.slug === slug)?.display_name || slug
}

function formatDate(dateStr?: string | null, withTime: boolean = true) {
  if (!dateStr) return '未知'
  return new Date(dateStr).toLocaleString('zh-CN', withTime ? undefined : {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

function tenantMark(status: string) {
  return {
    active: 'linear-gradient(145deg, #22c55e, #16a34a)',
    trial: 'linear-gradient(145deg, #f59e0b, #f97316)',
    suspended: 'linear-gradient(145deg, #ef4444, #be123c)',
    cancelled: 'linear-gradient(145deg, #64748b, #475569)',
  }[status] || 'linear-gradient(145deg, #3b82f6, #2563eb)'
}

watch([search, statusFilter], () => {
  page.value = 1
  if (searchTimer) {
    clearTimeout(searchTimer)
  }
  searchTimer = setTimeout(() => {
    fetchTenants(1)
  }, 250)
})

onMounted(() => {
  refreshAll()
})

onBeforeUnmount(() => {
  if (searchTimer) {
    clearTimeout(searchTimer)
  }
})
</script>

<style scoped>
.tenants-page {
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
    radial-gradient(circle at top left, rgba(34, 197, 94, 0.2), transparent 26%),
    linear-gradient(135deg, rgba(15, 23, 42, 0.96), rgba(30, 41, 59, 0.92));
}

.hero-copy {
  max-width: 640px;
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

.hero-copy p {
  color: #a5b4cc;
}

.hero-actions {
  display: flex;
  align-items: center;
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
  color: #90a2bf;
  font-size: 13px;
}

.control-bar {
  display: grid;
  grid-template-columns: 1.4fr 220px auto;
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

.control-actions {
  display: flex;
  align-items: flex-end;
  justify-content: flex-end;
}

.tenant-board {
  padding: 20px;
}

.board-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.board-head h3 {
  font-size: 20px;
}

.board-head p {
  margin-top: 4px;
  color: #94a3b8;
}

.tenant-table :deep(.el-table__row td) {
  background: transparent;
}

.tenant-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.tenant-mark {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border-radius: 14px;
  color: #fff;
  font-weight: 800;
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.25);
}

.tenant-mark--large {
  width: 56px;
  height: 56px;
  border-radius: 18px;
  font-size: 22px;
}

.tenant-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.tenant-meta strong {
  font-size: 15px;
}

.tenant-meta span,
.tenant-meta small {
  font-size: 12px;
  color: #94a3b8;
}

.table-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.board-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 18px;
}

.dialog-header h3,
.drawer-header h3 {
  margin-top: 6px;
  font-size: 24px;
}

.dialog-header p {
  margin-top: 6px;
  color: #94a3b8;
}

.tenant-form {
  padding-top: 6px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.color-field {
  display: inline-flex;
  align-items: center;
  gap: 12px;
}

.detail-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.detail-card {
  padding: 20px;
}

.detail-card-head {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 16px;
}

.detail-card-head h4 {
  font-size: 22px;
}

.detail-card-head p {
  color: #94a3b8;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.mini-detail {
  padding: 18px;
}

.mini-detail span {
  font-size: 12px;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.mini-detail strong {
  display: block;
  margin: 10px 0 6px;
  font-size: 26px;
}

.mini-detail small {
  color: #90a2bf;
}

.detail-section-head {
  margin-bottom: 12px;
}

.detail-section-head h4 {
  font-size: 18px;
}

.module-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.module-selector {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  width: 100%;
}

.module-option {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 14px;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.12);
  background: rgba(15, 23, 42, 0.48);
}

.module-option small,
.empty-hint {
  color: #90a2bf;
}

@media (max-width: 1080px) {
  .summary-grid,
  .detail-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .hero-panel,
  .control-bar {
    grid-template-columns: 1fr;
  }

  .hero-panel {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 760px) {
  .summary-grid,
  .form-grid,
  .detail-grid,
  .module-selector {
    grid-template-columns: 1fr;
  }

  .control-actions {
    justify-content: stretch;
  }
}
</style>
