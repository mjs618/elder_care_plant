<template>
  <div class="admin-page">
    <div class="page-head">
      <h2>租户管理</h2>
      <el-button type="primary" :icon="Plus" @click="showCreate = true">新建租户</el-button>
    </div>

    <!-- Filters -->
    <div class="filter-bar">
      <el-input v-model="search" placeholder="搜索租户名称 / Slug..." :prefix-icon="Search" style="width:280px" clearable />
      <el-select v-model="statusFilter" placeholder="状态" style="width:140px" clearable>
        <el-option label="激活" value="active" />
        <el-option label="试用" value="trial" />
        <el-option label="暂停" value="suspended" />
        <el-option label="已取消" value="cancelled" />
      </el-select>
      <el-button :icon="Refresh" @click="fetchTenants">刷新</el-button>
    </div>

    <!-- Table -->
    <el-card>
      <el-table :data="filteredTenants" v-loading="loading" stripe>
        <el-table-column prop="name" label="租户名称" min-width="150" />
        <el-table-column prop="slug" label="Slug" width="140" />
        <el-table-column prop="contact_email" label="联系邮箱" min-width="180" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="viewDetail(row)">详情</el-button>
            <el-button size="small" type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" @click="openModules(row)">模块</el-button>
            <el-dropdown size="small" style="margin-left: 8px;">
              <el-button size="small">
                更多<el-icon class="el-icon--right"><arrow-down /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="handleStatusChange(row, 'active')" v-if="row.status !== 'active'">激活</el-dropdown-item>
                  <el-dropdown-item @click="handleStatusChange(row, 'suspended')" v-if="row.status !== 'suspended'">暂停</el-dropdown-item>
                  <el-dropdown-item @click="handleStatusChange(row, 'cancelled')" v-if="row.status !== 'cancelled'">取消</el-dropdown-item>
                  <el-dropdown-item divided @click="handleDelete(row)" type="danger">删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination">
        <el-pagination
          :total="total"
          :page-size="pageSize"
          v-model:current-page="page"
          layout="total, prev, pager, next"
          @current-change="fetchTenants"
        />
      </div>
    </el-card>

    <!-- Create dialog -->
    <el-dialog v-model="showCreate" title="新建租户" width="500px">
      <el-form :model="createForm" label-width="110px" :rules="formRules" ref="createFormRef">
        <el-form-item label="机构名称" prop="name" required>
          <el-input v-model="createForm.name" placeholder="例：阳光养老院" />
        </el-form-item>
        <el-form-item label="Slug" prop="slug" required>
          <el-input v-model="createForm.slug" placeholder="例：sunshine-care（唯一标识）" />
        </el-form-item>
        <el-form-item label="联系邮箱" prop="contact_email" required>
          <el-input v-model="createForm.contact_email" type="email" />
        </el-form-item>
        <el-form-item label="套餐" prop="plan_id">
          <el-select v-model="createForm.plan_id" placeholder="选择套餐" style="width: 100%">
            <el-option v-for="plan in plans" :key="plan.id" :label="plan.name" :value="plan.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="createTenant">确认创建</el-button>
      </template>
    </el-dialog>

    <!-- Edit dialog -->
    <el-dialog v-model="showEdit" title="编辑租户" width="500px">
      <el-form :model="editForm" label-width="110px" ref="editFormRef">
        <el-form-item label="机构名称">
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="联系邮箱">
          <el-input v-model="editForm.contact_email" type="email" />
        </el-form-item>
        <el-form-item label="品牌名称">
          <el-input v-model="editForm.brand_name" placeholder="自定义品牌名称" />
        </el-form-item>
        <el-form-item label="主题色">
          <el-color-picker v-model="editForm.primary_color" />
        </el-form-item>
        <el-form-item label="套餐">
          <el-select v-model="editForm.plan_id" placeholder="选择套餐" style="width: 100%">
            <el-option v-for="plan in plans" :key="plan.id" :label="plan.name" :value="plan.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEdit = false">取消</el-button>
        <el-button type="primary" :loading="editing" @click="updateTenant">保存</el-button>
      </template>
    </el-dialog>

    <!-- Detail drawer -->
    <el-drawer v-model="showDetail" title="租户详情" size="600px">
      <div v-if="currentTenant" class="tenant-detail">
        <div class="detail-section">
          <h4>基本信息</h4>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="租户ID">{{ currentTenant.id }}</el-descriptions-item>
            <el-descriptions-item label="机构名称">{{ currentTenant.name }}</el-descriptions-item>
            <el-descriptions-item label="Slug">{{ currentTenant.slug }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="statusTagType(currentTenant.status)">{{ statusLabel(currentTenant.status) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="联系邮箱">{{ currentTenant.contact_email }}</el-descriptions-item>
            <el-descriptions-item label="品牌名称">{{ currentTenant.brand_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatDate(currentTenant.created_at) }}</el-descriptions-item>
          </el-descriptions>
        </div>

        <div class="detail-section">
          <h4>套餐信息</h4>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="套餐名称">{{ currentTenant.plan?.name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="套餐等级">
              <el-tag size="small" :type="tierTagType(currentTenant.plan?.tier)">{{ tierLabel(currentTenant.plan?.tier) }}</el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <div class="detail-section">
          <h4>使用情况</h4>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="用户数量">{{ currentTenant.user_count }} 人</el-descriptions-item>
            <el-descriptions-item label="已激活模块">{{ currentTenant.active_modules?.length || 0 }} 个</el-descriptions-item>
          </el-descriptions>
        </div>

        <div class="detail-section">
          <h4>已激活模块</h4>
          <div class="module-tags">
            <el-tag v-for="slug in currentTenant.active_modules" :key="slug" size="small" style="margin: 4px;">
              {{ getModuleName(slug) }}
            </el-tag>
            <span v-if="!currentTenant.active_modules?.length" style="color: var(--text-muted);">暂无激活模块</span>
          </div>
        </div>
      </div>
    </el-drawer>

    <!-- Module config dialog -->
    <el-dialog v-model="showModules" title="模块配置" width="520px">
      <p class="dialog-sub">租户：<strong>{{ currentTenant?.name }}</strong></p>
      <el-checkbox-group v-model="selectedModules">
        <div class="module-checks">
          <el-checkbox
            v-for="m in allModules"
            :key="m.slug"
            :label="m.slug"
          >{{ m.display_name }}</el-checkbox>
        </div>
      </el-checkbox-group>
      <template #footer>
        <el-button @click="showModules = false">取消</el-button>
        <el-button type="primary" :loading="savingModules" @click="saveModules">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { Plus, Search, Refresh, ArrowDown } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useModuleStore } from '@/stores/modules'
import { tenantsApi, type Tenant, type TenantDetail } from '@/api/tenants'
import { platformApi, type Plan } from '@/api/platform'

const moduleStore = useModuleStore()
const allModules = computed(() => moduleStore.allModules)

const tenants = ref<Tenant[]>([])
const loading = ref(false)
const search = ref('')
const statusFilter = ref('')
const page = ref(1)
const pageSize = 20
const total = ref(0)

const plans = ref<Plan[]>([])

// Filtered tenants
const filteredTenants = computed(() => {
  let result = tenants.value
  
  if (search.value) {
    const keyword = search.value.toLowerCase()
    result = result.filter(t => 
      t.name.toLowerCase().includes(keyword) || 
      t.slug.toLowerCase().includes(keyword)
    )
  }
  
  if (statusFilter.value) {
    result = result.filter(t => t.status === statusFilter.value)
  }
  
  return result
})

// Create
const showCreate = ref(false)
const creating = ref(false)
const createFormRef = ref()
const createForm = reactive({ name: '', slug: '', contact_email: '', plan_id: '' })

const formRules = {
  name: [{ required: true, message: '请输入机构名称', trigger: 'blur' }],
  slug: [{ required: true, message: '请输入Slug', trigger: 'blur' }],
  contact_email: [
    { required: true, message: '请输入联系邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ]
}

// Edit
const showEdit = ref(false)
const editing = ref(false)
const editFormRef = ref()
const editForm = reactive({ name: '', contact_email: '', brand_name: '', primary_color: '', plan_id: '' })
const editingTenantId = ref('')

// Detail
const showDetail = ref(false)
const currentTenant = ref<TenantDetail | null>(null)

// Modules
const showModules = ref(false)
const savingModules = ref(false)
const selectedModules = ref<string[]>([])

async function fetchTenants() {
  loading.value = true
  try {
    const res: any = await tenantsApi.getTenants(page.value, pageSize)
    tenants.value = res.data?.items ?? []
    total.value = res.data?.total ?? 0
  } catch {
    tenants.value = []
    total.value = 0
  } finally {
    loading.value = false
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

async function createTenant() {
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return
  
  creating.value = true
  try {
    await tenantsApi.createTenant(createForm)
    ElMessage.success('租户创建成功')
    showCreate.value = false
    createFormRef.value?.resetFields()
    fetchTenants()
  } finally {
    creating.value = false
  }
}

function viewDetail(row: Tenant) {
  currentTenant.value = null
  showDetail.value = true
  // Fetch full detail
  tenantsApi.getTenant(row.id).then(res => {
    currentTenant.value = res.data
  })
}

function openEdit(row: Tenant) {
  editingTenantId.value = row.id
  editForm.name = row.name
  editForm.contact_email = row.contact_email
  editForm.brand_name = ''
  editForm.primary_color = ''
  editForm.plan_id = ''
  showEdit.value = true
}

async function updateTenant() {
  editing.value = true
  try {
    await tenantsApi.updateTenant(editingTenantId.value, editForm)
    ElMessage.success('租户更新成功')
    showEdit.value = false
    fetchTenants()
  } finally {
    editing.value = false
  }
}

async function handleStatusChange(tenant: Tenant, status: string) {
  const actionMap: Record<string, string> = {
    active: '激活',
    suspended: '暂停',
    cancelled: '取消'
  }
  
  try {
    await ElMessageBox.confirm(
      `确认${actionMap[status]}租户 "${tenant.name}"？`,
      '确认操作',
      { type: 'warning' }
    )
    
    await tenantsApi.updateTenantStatus(tenant.id, { status: status as any })
    ElMessage.success(`租户已${actionMap[status]}`)
    fetchTenants()
  } catch (e) {
    // Cancelled
  }
}

async function handleDelete(tenant: Tenant) {
  try {
    await ElMessageBox.confirm(
      `确认删除租户 "${tenant.name}"？此操作不可恢复！`,
      '危险操作',
      { type: 'error', confirmButtonClass: 'el-button--danger' }
    )
    
    await tenantsApi.deleteTenant(tenant.id)
    ElMessage.success('租户已删除')
    fetchTenants()
  } catch (e) {
    // Cancelled
  }
}

function openModules(tenant: Tenant) {
  currentTenant.value = null
  selectedModules.value = []
  showModules.value = true
  
  // Fetch current modules
  tenantsApi.getTenant(tenant.id).then(res => {
    currentTenant.value = res.data
    selectedModules.value = res.data.active_modules ?? []
  })
}

async function saveModules() {
  if (!currentTenant.value) return
  
  savingModules.value = true
  try {
    await tenantsApi.updateTenantModules(currentTenant.value.id, {
      module_slugs: selectedModules.value
    })
    ElMessage.success('模块配置已保存')
    showModules.value = false
  } finally {
    savingModules.value = false
  }
}

function statusLabel(s: string) {
  return { active: '激活', trial: '试用', suspended: '暂停', cancelled: '已取消' }[s] ?? s
}

function statusTagType(s: string): 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined {
  const map: Record<string, 'primary' | 'success' | 'warning' | 'info' | 'danger'> = {
    active: 'success', trial: 'warning', suspended: 'danger', cancelled: 'info'
  }
  return map[s]
}

function tierLabel(t?: string) {
  return { free: '免费版', standard: '标准版', enterprise: '企业版' }[t || ''] ?? t
}

function tierTagType(t?: string): 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined {
  const map: Record<string, 'primary' | 'success' | 'warning' | 'info'> = {
    free: 'info', standard: 'success', enterprise: 'warning'
  }
  return map[t || '']
}

function getModuleName(slug: string) {
  const mod = allModules.value.find(m => m.slug === slug)
  return mod?.display_name || slug
}

function formatDate(dateStr?: string) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(() => {
  fetchTenants()
  fetchPlans()
})
</script>

<style scoped>
.admin-page { display: flex; flex-direction: column; gap: 20px; }
.page-head { display: flex; align-items: center; justify-content: space-between; }
.page-head h2 { font-size: 22px; font-weight: 700; }
.filter-bar { display: flex; gap: 12px; flex-wrap: wrap; }
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
.dialog-sub { margin-bottom: 16px; color: var(--text-secondary); }
.module-checks { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }

.tenant-detail { padding: 20px; }
.detail-section { margin-bottom: 24px; }
.detail-section h4 { font-size: 14px; font-weight: 700; margin-bottom: 12px; color: var(--text-primary); }
.module-tags { display: flex; flex-wrap: wrap; gap: 4px; }
</style>
