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
      </el-select>
      <el-button :icon="Refresh" @click="fetchTenants">刷新</el-button>
    </div>

    <!-- Table -->
    <el-card>
      <el-table :data="tenants" v-loading="loading" stripe>
        <el-table-column prop="name" label="租户名称" min-width="150" />
        <el-table-column prop="slug" label="Slug" width="140" />
        <el-table-column prop="contact_email" label="联系邮箱" min-width="180" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openModules(row)">模块配置</el-button>
            <el-button size="small" type="danger" plain @click="suspend(row)">暂停</el-button>
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
      <el-form :model="createForm" label-width="110px">
        <el-form-item label="机构名称" required>
          <el-input v-model="createForm.name" placeholder="例：阳光养老院" />
        </el-form-item>
        <el-form-item label="Slug" required>
          <el-input v-model="createForm.slug" placeholder="例：sunshine-care（唯一标识）" />
        </el-form-item>
        <el-form-item label="联系邮箱" required>
          <el-input v-model="createForm.contact_email" type="email" />
        </el-form-item>
        <el-form-item label="套餐">
          <el-select v-model="createForm.plan_id" placeholder="选择套餐">
            <el-option label="免费版" value="free" />
            <el-option label="标准版" value="standard" />
            <el-option label="企业版" value="enterprise" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="createTenant">确认创建</el-button>
      </template>
    </el-dialog>

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
import { ref, reactive, onMounted } from 'vue'
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/utils/request'
import { useModuleStore } from '@/stores/modules'

const moduleStore = useModuleStore()
const allModules = computed(() => moduleStore.allModules)

import { computed } from 'vue'

const tenants = ref<any[]>([])
const loading = ref(false)
const search = ref('')
const statusFilter = ref('')
const page = ref(1)
const pageSize = 20
const total = ref(0)

const showCreate = ref(false)
const creating = ref(false)
const createForm = reactive({ name: '', slug: '', contact_email: '', plan_id: '' })

const showModules = ref(false)
const savingModules = ref(false)
const selectedModules = ref<string[]>([])
const currentTenant = ref<any>(null)

async function fetchTenants() {
  loading.value = true
  try {
    const res: any = await request.get('/tenants', { params: { page: page.value, page_size: pageSize } })
    tenants.value = res.data ?? []
    total.value = res.meta?.total ?? 0
  } catch {
    tenants.value = []
  } finally {
    loading.value = false
  }
}

async function createTenant() {
  creating.value = true
  try {
    await request.post('/tenants', createForm)
    ElMessage.success('租户创建成功')
    showCreate.value = false
    fetchTenants()
  } finally {
    creating.value = false
  }
}

function openModules(tenant: any) {
  currentTenant.value = tenant
  selectedModules.value = []
  showModules.value = true
}

async function saveModules() {
  savingModules.value = true
  try {
    await request.put(`/tenants/${currentTenant.value.id}/modules`, { module_slugs: selectedModules.value })
    ElMessage.success('模块配置已保存')
    showModules.value = false
  } finally {
    savingModules.value = false
  }
}

async function suspend(tenant: any) {
  await ElMessageBox.confirm(`确认暂停租户 "${tenant.name}"？`, '警告', { type: 'warning' })
  ElMessage.success('操作成功')
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

onMounted(fetchTenants)
</script>

<style scoped>
.admin-page { display: flex; flex-direction: column; gap: 20px; }
.page-head { display: flex; align-items: center; justify-content: space-between; }
.page-head h2 { font-size: 22px; font-weight: 700; }
.filter-bar { display: flex; gap: 12px; flex-wrap: wrap; }
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
.dialog-sub { margin-bottom: 16px; color: var(--text-secondary); }
.module-checks { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
</style>
