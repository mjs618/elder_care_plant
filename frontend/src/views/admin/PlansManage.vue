<template>
  <div class="admin-page">
    <div class="page-head">
      <h2>套餐管理</h2>
      <el-button type="primary" :icon="Plus" @click="showCreate = true">新建套餐</el-button>
    </div>

    <div class="plans-grid">
      <div v-for="plan in plans" :key="plan.id" class="plan-card card">
        <div class="plan-header" :class="`tier-${plan.tier}`">
          <el-icon size="28" color="white"><Tickets /></el-icon>
          <div>
            <div class="plan-name">{{ plan.name }}</div>
            <el-tag size="small" :type="tierTagType(plan.tier)" effect="dark">{{ tierLabel(plan.tier) }}</el-tag>
          </div>
        </div>
        <div class="plan-body">
          <div class="plan-stat"><span>限速</span><strong>{{ plan.rate_limit_rpm }} 次/分</strong></div>
          <div class="plan-stat"><span>最大用户</span><strong>{{ plan.max_users }}</strong></div>
          <div class="plan-stat"><span>最大患者</span><strong>{{ plan.max_patients }}</strong></div>
          <div class="plan-modules">
            <el-tag
              v-for="slug in parseModules(plan.included_modules)"
              :key="slug"
              size="small"
              style="margin:2px"
            >{{ getModuleName(slug) }}</el-tag>
            <span v-if="!plan.included_modules" style="color: var(--text-muted); font-size: 12px;">无包含模块</span>
          </div>
        </div>
        <div class="plan-actions">
          <el-button size="small" @click="openEdit(plan)">编辑</el-button>
          <el-button size="small" type="danger" plain @click="handleDelete(plan)">删除</el-button>
        </div>
      </div>

      <!-- Loading/empty -->
      <el-card v-if="!loading && plans.length === 0" class="empty-card">
        <el-empty description="暂无套餐，点击右上角创建" />
      </el-card>
    </div>

    <!-- Create dialog -->
    <el-dialog v-model="showCreate" title="新建套餐" width="520px">
      <el-form :model="createForm" label-width="120px" :rules="formRules" ref="createFormRef">
        <el-form-item label="套餐名称" prop="name" required>
          <el-input v-model="createForm.name" placeholder="例如：标准版" />
        </el-form-item>
        <el-form-item label="套餐等级" prop="tier" required>
          <el-select v-model="createForm.tier" style="width:100%">
            <el-option label="免费 (Free)" value="free" />
            <el-option label="标准 (Standard)" value="standard" />
            <el-option label="企业 (Enterprise)" value="enterprise" />
          </el-select>
        </el-form-item>
        <el-form-item label="限速 (次/分)">
          <el-input-number v-model="createForm.rate_limit_rpm" :min="10" :max="10000" />
        </el-form-item>
        <el-form-item label="最大用户数">
          <el-input-number v-model="createForm.max_users" :min="1" :max="10000" />
        </el-form-item>
        <el-form-item label="最大患者数">
          <el-input-number v-model="createForm.max_patients" :min="1" :max="100000" />
        </el-form-item>
        <el-form-item label="包含模块">
          <el-checkbox-group v-model="createForm.selectedModules">
            <div class="module-checks">
              <el-checkbox v-for="m in allModules" :key="m.slug" :label="m.slug">
                {{ m.display_name }}
              </el-checkbox>
            </div>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="createForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="createPlan">创建</el-button>
      </template>
    </el-dialog>

    <!-- Edit dialog -->
    <el-dialog v-model="showEdit" title="编辑套餐" width="520px">
      <el-form :model="editForm" label-width="120px" ref="editFormRef">
        <el-form-item label="套餐名称">
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="套餐等级">
          <el-select v-model="editForm.tier" style="width:100%">
            <el-option label="免费 (Free)" value="free" />
            <el-option label="标准 (Standard)" value="standard" />
            <el-option label="企业 (Enterprise)" value="enterprise" />
          </el-select>
        </el-form-item>
        <el-form-item label="限速 (次/分)">
          <el-input-number v-model="editForm.rate_limit_rpm" :min="10" :max="10000" />
        </el-form-item>
        <el-form-item label="最大用户数">
          <el-input-number v-model="editForm.max_users" :min="1" :max="10000" />
        </el-form-item>
        <el-form-item label="最大患者数">
          <el-input-number v-model="editForm.max_patients" :min="1" :max="100000" />
        </el-form-item>
        <el-form-item label="包含模块">
          <el-checkbox-group v-model="editForm.selectedModules">
            <div class="module-checks">
              <el-checkbox v-for="m in allModules" :key="m.slug" :label="m.slug">
                {{ m.display_name }}
              </el-checkbox>
            </div>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="editForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEdit = false">取消</el-button>
        <el-button type="primary" :loading="editing" @click="updatePlan">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { Plus, Tickets } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useModuleStore } from '@/stores/modules'
import { platformApi, type Plan, type CreatePlanRequest, type UpdatePlanRequest } from '@/api/platform'

const moduleStore = useModuleStore()
const allModules = computed(() => moduleStore.allModules)

const plans = ref<Plan[]>([])
const loading = ref(false)

// Create
const showCreate = ref(false)
const creating = ref(false)
const createFormRef = ref()
const createForm = reactive({
  name: '',
  tier: 'standard' as const,
  rate_limit_rpm: 60,
  max_users: 10,
  max_patients: 100,
  description: '',
  selectedModules: [] as string[]
})

const formRules = {
  name: [{ required: true, message: '请输入套餐名称', trigger: 'blur' }],
  tier: [{ required: true, message: '请选择套餐等级', trigger: 'change' }]
}

// Edit
const showEdit = ref(false)
const editing = ref(false)
const editFormRef = ref()
const editForm = reactive({
  name: '',
  tier: 'standard' as 'free' | 'standard' | 'enterprise',
  rate_limit_rpm: 60,
  max_users: 10,
  max_patients: 100,
  description: '',
  selectedModules: [] as string[]
})
const editingPlanId = ref('')

async function fetchPlans() {
  loading.value = true
  try {
    const res = await platformApi.getPlans()
    plans.value = res.data ?? []
  } catch {
    plans.value = []
  } finally {
    loading.value = false
  }
}

function parseModules(modulesStr: string | null): string[] {
  if (!modulesStr) return []
  return modulesStr.split(',').filter(Boolean)
}

function getModuleName(slug: string): string {
  const mod = allModules.value.find(m => m.slug === slug)
  return mod?.display_name || slug
}

async function createPlan() {
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return

  creating.value = true
  try {
    const data: CreatePlanRequest = {
      name: createForm.name,
      tier: createForm.tier,
      description: createForm.description,
      rate_limit_rpm: createForm.rate_limit_rpm,
      max_users: createForm.max_users,
      max_patients: createForm.max_patients,
      included_modules: createForm.selectedModules.join(',')
    }
    await platformApi.createPlan(data)
    ElMessage.success('套餐创建成功')
    showCreate.value = false
    createFormRef.value?.resetFields()
    createForm.selectedModules = []
    fetchPlans()
  } finally {
    creating.value = false
  }
}

function openEdit(plan: Plan) {
  editingPlanId.value = plan.id
  editForm.name = plan.name
  editForm.tier = plan.tier as 'free' | 'standard' | 'enterprise'
  editForm.rate_limit_rpm = plan.rate_limit_rpm
  editForm.max_users = plan.max_users
  editForm.max_patients = plan.max_patients
  editForm.description = plan.description || ''
  editForm.selectedModules = parseModules(plan.included_modules)
  showEdit.value = true
}

async function updatePlan() {
  editing.value = true
  try {
    const data: UpdatePlanRequest = {
      name: editForm.name,
      tier: editForm.tier,
      description: editForm.description,
      rate_limit_rpm: editForm.rate_limit_rpm,
      max_users: editForm.max_users,
      max_patients: editForm.max_patients,
      included_modules: editForm.selectedModules.join(',')
    }
    await platformApi.updatePlan(editingPlanId.value, data)
    ElMessage.success('套餐更新成功')
    showEdit.value = false
    fetchPlans()
  } finally {
    editing.value = false
  }
}

async function handleDelete(plan: Plan) {
  try {
    await ElMessageBox.confirm(
      `确认删除套餐 "${plan.name}"？`,
      '确认删除',
      { type: 'warning' }
    )
    await platformApi.deletePlan(plan.id)
    ElMessage.success('套餐已删除')
    fetchPlans()
  } catch (e) {
    // Cancelled or error
  }
}

function tierLabel(t: string) {
  return { free: '免费版', standard: '标准版', enterprise: '企业版' }[t] ?? t
}

function tierTagType(t: string): 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined {
  const map: Record<string, 'primary' | 'success' | 'warning' | 'info'> = {
    free: 'info', standard: 'success', enterprise: 'warning'
  }
  return map[t]
}

onMounted(fetchPlans)
</script>

<style scoped>
.admin-page { display: flex; flex-direction: column; gap: 20px; }
.page-head { display: flex; align-items: center; justify-content: space-between; }
.page-head h2 { font-size: 22px; font-weight: 700; }
.plans-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }
.plan-card { overflow: hidden; padding: 0; display: flex; flex-direction: column; }
.plan-header {
  display: flex; align-items: center; gap: 14px;
  padding: 20px 20px 16px;
  background: linear-gradient(135deg, #334155, #1E293B);
}
.plan-header.tier-enterprise {
  background: linear-gradient(135deg, #B45309, #92400E);
}
.plan-header.tier-free {
  background: linear-gradient(135deg, #475569, #64748B);
}
.plan-name { font-size: 16px; font-weight: 700; color: white; margin-bottom: 4px; }
.plan-body { padding: 16px 20px; flex: 1; }
.plan-stat { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid var(--border-subtle); font-size: 14px; }
.plan-stat span { color: var(--text-secondary); }
.plan-modules { margin-top: 12px; }
.plan-actions { padding: 12px 20px; border-top: 1px solid var(--border-subtle); display: flex; gap: 8px; justify-content: flex-end; }
.empty-card { grid-column: 1 / -1; }
.module-checks { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
</style>
