<template>
  <section class="plans-page">
    <header class="hero-panel card">
      <div class="hero-copy">
        <span class="hero-eyebrow">Commercial Packaging</span>
        <h2>套餐矩阵</h2>
        <p>统一管理价格层级、资源上限和功能打包方式，让销售口径、交付边界和升级路径始终一致。</p>
      </div>

      <div class="hero-actions">
        <div class="hero-stat">
          <strong>{{ plans.length }}</strong>
          <span>当前套餐</span>
        </div>
        <div class="hero-stat">
          <strong>{{ activeTenantCoverage }}</strong>
          <span>活跃租户覆盖</span>
        </div>
        <el-button type="primary" size="large" :icon="Plus" @click="openCreate">
          新建套餐
        </el-button>
      </div>
    </header>

    <div class="summary-grid">
      <article class="summary-card card">
        <span class="summary-label">企业版</span>
        <strong>{{ planCountByTier.enterprise }}</strong>
        <p>适合深度运营和高配额租户，通常承担平台的大客户成交。</p>
      </article>
      <article class="summary-card card">
        <span class="summary-label">标准版</span>
        <strong>{{ planCountByTier.standard }}</strong>
        <p>最适合作为主力成交层，兼顾价格带与功能密度。</p>
      </article>
      <article class="summary-card card">
        <span class="summary-label">免费版</span>
        <strong>{{ planCountByTier.free }}</strong>
        <p>用于体验、演示和轻量引流，负责承接最早期的转化。</p>
      </article>
      <article class="summary-card card">
        <span class="summary-label">平均模块数</span>
        <strong>{{ avgModulesPerPlan }}</strong>
        <p>反映套餐打包厚度，避免销售层级之间过于拥挤或过于稀薄。</p>
      </article>
    </div>

    <div class="plans-grid">
      <article
        v-for="plan in plans"
        :key="plan.id"
        class="plan-card"
        :class="`plan-card--${plan.tier}`"
      >
        <div class="plan-chrome">
          <div class="plan-badge">
            <el-icon><Tickets /></el-icon>
          </div>
          <div class="plan-heading">
            <div class="plan-title-row">
              <h3>{{ plan.name }}</h3>
              <el-tag :type="tierTagType(plan.tier)" effect="dark" round>{{ tierLabel(plan.tier) }}</el-tag>
            </div>
            <p>{{ plan.description || '尚未补充套餐定位，建议补齐适用机构、升级理由和约束边界。' }}</p>
          </div>
        </div>

        <div class="plan-metrics">
          <div class="metric-pill">
            <span>API 限速</span>
            <strong>{{ plan.rate_limit_rpm }} 次/分</strong>
          </div>
          <div class="metric-pill">
            <span>最大用户</span>
            <strong>{{ plan.max_users }}</strong>
          </div>
          <div class="metric-pill">
            <span>最大患者</span>
            <strong>{{ plan.max_patients }}</strong>
          </div>
          <div class="metric-pill">
            <span>覆盖租户</span>
            <strong>{{ plan.tenant_count }}</strong>
          </div>
          <div class="metric-pill">
            <span>活跃租户</span>
            <strong>{{ plan.active_tenant_count }}</strong>
          </div>
        </div>

        <div class="plan-section">
          <div class="section-title">
            <span>功能包</span>
            <small>{{ parseModules(plan.included_modules).length }} 个模块</small>
          </div>
          <div class="module-cloud">
            <el-tag
              v-for="slug in parseModules(plan.included_modules)"
              :key="slug"
              size="small"
              round
            >
              {{ getModuleName(slug) }}
            </el-tag>
            <span v-if="parseModules(plan.included_modules).length === 0" class="empty-hint">
              暂未配置模块
            </span>
          </div>
        </div>

        <footer class="plan-footer">
          <div class="plan-density">
            <span>配置强度</span>
            <div class="density-bar">
              <span :style="{ width: densityWidth(plan) }" />
            </div>
          </div>
          <div class="plan-actions">
            <el-button size="small" @click="openEdit(plan)">编辑</el-button>
            <el-button size="small" type="danger" plain @click="handleDelete(plan)">删除</el-button>
          </div>
        </footer>
      </article>

      <el-empty
        v-if="!loading && plans.length === 0"
        description="还没有套餐，先创建一个默认商业方案。"
        class="empty-block"
      />
    </div>

    <el-dialog v-model="showCreate" width="680px" class="plan-dialog" destroy-on-close>
      <template #header>
        <div class="dialog-header">
          <span class="hero-eyebrow">Create Plan</span>
          <h3>新建套餐</h3>
        </div>
      </template>

      <el-form
        ref="createFormRef"
        :model="createForm"
        label-position="top"
        :rules="formRules"
        class="plan-form"
      >
        <div class="form-grid">
          <el-form-item label="套餐名称" prop="name">
            <el-input v-model="createForm.name" placeholder="例如：标准版、旗舰版" />
          </el-form-item>
          <el-form-item label="套餐等级" prop="tier">
            <el-select v-model="createForm.tier" style="width: 100%">
              <el-option label="免费版" value="free" />
              <el-option label="标准版" value="standard" />
              <el-option label="企业版" value="enterprise" />
            </el-select>
          </el-form-item>
        </div>

        <div class="form-grid form-grid--triple">
          <el-form-item label="API 限速">
            <el-input-number v-model="createForm.rate_limit_rpm" :min="10" :max="10000" style="width: 100%" />
          </el-form-item>
          <el-form-item label="最大用户">
            <el-input-number v-model="createForm.max_users" :min="1" :max="10000" style="width: 100%" />
          </el-form-item>
          <el-form-item label="最大患者">
            <el-input-number v-model="createForm.max_patients" :min="1" :max="100000" style="width: 100%" />
          </el-form-item>
        </div>

        <el-form-item label="套餐说明">
          <el-input
            v-model="createForm.description"
            type="textarea"
            :rows="3"
            placeholder="说明适用机构、升级价值和限制边界"
          />
        </el-form-item>

        <el-form-item label="包含模块">
          <el-checkbox-group v-model="createForm.selectedModules" class="module-selector">
            <label v-for="module in allModules" :key="module.slug" class="module-option">
              <el-checkbox :label="module.slug">{{ module.display_name }}</el-checkbox>
              <small>{{ module.slug }}</small>
            </label>
          </el-checkbox-group>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="createPlan">创建套餐</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showEdit" width="680px" class="plan-dialog" destroy-on-close>
      <template #header>
        <div class="dialog-header">
          <span class="hero-eyebrow">Edit Plan</span>
          <h3>编辑套餐</h3>
        </div>
      </template>

      <el-form ref="editFormRef" :model="editForm" label-position="top" class="plan-form">
        <div class="form-grid">
          <el-form-item label="套餐名称">
            <el-input v-model="editForm.name" />
          </el-form-item>
          <el-form-item label="套餐等级">
            <el-select v-model="editForm.tier" style="width: 100%">
              <el-option label="免费版" value="free" />
              <el-option label="标准版" value="standard" />
              <el-option label="企业版" value="enterprise" />
            </el-select>
          </el-form-item>
        </div>

        <div class="form-grid form-grid--triple">
          <el-form-item label="API 限速">
            <el-input-number v-model="editForm.rate_limit_rpm" :min="10" :max="10000" style="width: 100%" />
          </el-form-item>
          <el-form-item label="最大用户">
            <el-input-number v-model="editForm.max_users" :min="1" :max="10000" style="width: 100%" />
          </el-form-item>
          <el-form-item label="最大患者">
            <el-input-number v-model="editForm.max_patients" :min="1" :max="100000" style="width: 100%" />
          </el-form-item>
        </div>

        <el-form-item label="套餐说明">
          <el-input v-model="editForm.description" type="textarea" :rows="3" />
        </el-form-item>

        <el-form-item label="包含模块">
          <el-checkbox-group v-model="editForm.selectedModules" class="module-selector">
            <label v-for="module in allModules" :key="module.slug" class="module-option">
              <el-checkbox :label="module.slug">{{ module.display_name }}</el-checkbox>
              <small>{{ module.slug }}</small>
            </label>
          </el-checkbox-group>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showEdit = false">取消</el-button>
        <el-button type="primary" :loading="editing" @click="updatePlan">保存修改</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Tickets } from '@element-plus/icons-vue'

import { platformApi, type CreatePlanRequest, type Plan, type UpdatePlanRequest } from '@/api/platform'
import { useModuleStore } from '@/stores/modules'

const moduleStore = useModuleStore()
const allModules = computed(() => moduleStore.allModules)

const plans = ref<Plan[]>([])
const loading = ref(false)

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
  selectedModules: [] as string[],
})

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
  selectedModules: [] as string[],
})
const editingPlanId = ref('')

const formRules = {
  name: [{ required: true, message: '请输入套餐名称', trigger: 'blur' }],
  tier: [{ required: true, message: '请选择套餐等级', trigger: 'change' }],
}

const planCountByTier = computed(() => ({
  enterprise: plans.value.filter((plan) => plan.tier === 'enterprise').length,
  standard: plans.value.filter((plan) => plan.tier === 'standard').length,
  free: plans.value.filter((plan) => plan.tier === 'free').length,
}))

const avgModulesPerPlan = computed(() => {
  if (plans.value.length === 0) return 0
  const total = plans.value.reduce((sum, plan) => sum + parseModules(plan.included_modules).length, 0)
  return Math.round((total / plans.value.length) * 10) / 10
})

const activeTenantCoverage = computed(() => {
  return plans.value.reduce((sum, plan) => sum + plan.active_tenant_count, 0)
})

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

function openCreate() {
  showCreate.value = true
}

function parseModules(modulesStr: string | null) {
  if (!modulesStr) return []
  return modulesStr
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

function getModuleName(slug: string) {
  return allModules.value.find((module) => module.slug === slug)?.display_name || slug
}

function tierLabel(tier: string) {
  return {
    free: '免费版',
    standard: '标准版',
    enterprise: '企业版',
  }[tier] ?? tier
}

function tierTagType(tier: string): 'primary' | 'success' | 'warning' | 'info' | undefined {
  const map: Record<string, 'primary' | 'success' | 'warning' | 'info'> = {
    free: 'info',
    standard: 'success',
    enterprise: 'warning',
  }
  return map[tier]
}

function densityWidth(plan: Plan) {
  const densityScore = Math.min(
    100,
    parseModules(plan.included_modules).length * 10 + plan.max_users / 2 + plan.max_patients / 40,
  )
  return `${densityScore}%`
}

async function createPlan() {
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return

  creating.value = true
  try {
    const payload: CreatePlanRequest = {
      name: createForm.name,
      tier: createForm.tier,
      description: createForm.description,
      rate_limit_rpm: createForm.rate_limit_rpm,
      max_users: createForm.max_users,
      max_patients: createForm.max_patients,
      included_modules: createForm.selectedModules.join(','),
    }
    await platformApi.createPlan(payload)
    ElMessage.success('套餐创建成功')
    showCreate.value = false
    createFormRef.value?.resetFields()
    createForm.selectedModules = []
    await fetchPlans()
  } finally {
    creating.value = false
  }
}

function openEdit(plan: Plan) {
  editingPlanId.value = plan.id
  editForm.name = plan.name
  editForm.tier = plan.tier
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
    const payload: UpdatePlanRequest = {
      name: editForm.name,
      tier: editForm.tier,
      description: editForm.description,
      rate_limit_rpm: editForm.rate_limit_rpm,
      max_users: editForm.max_users,
      max_patients: editForm.max_patients,
      included_modules: editForm.selectedModules.join(','),
    }
    await platformApi.updatePlan(editingPlanId.value, payload)
    ElMessage.success('套餐更新成功')
    showEdit.value = false
    await fetchPlans()
  } finally {
    editing.value = false
  }
}

async function handleDelete(plan: Plan) {
  try {
    await ElMessageBox.confirm(`确认删除套餐“${plan.name}”？`, '删除套餐', {
      type: 'warning',
    })
    await platformApi.deletePlan(plan.id)
    ElMessage.success('套餐已删除')
    await fetchPlans()
  } catch {
    // ignore cancel
  }
}

onMounted(fetchPlans)
</script>

<style scoped>
.plans-page {
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
  overflow: hidden;
  position: relative;
  background:
    radial-gradient(circle at top left, rgba(245, 158, 11, 0.24), transparent 26%),
    linear-gradient(135deg, rgba(15, 23, 42, 0.96), rgba(30, 41, 59, 0.92));
}

.hero-panel::after {
  content: '';
  position: absolute;
  inset: auto -50px -70px auto;
  width: 220px;
  height: 220px;
  border-radius: 50%;
  background: rgba(59, 130, 246, 0.14);
  filter: blur(40px);
}

.hero-copy,
.hero-actions {
  position: relative;
  z-index: 1;
}

.hero-copy {
  max-width: 620px;
}

.hero-eyebrow {
  display: inline-block;
  margin-bottom: 8px;
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: #94a3b8;
}

.hero-copy h2 {
  font-size: 34px;
  line-height: 1;
  margin-bottom: 10px;
}

.hero-copy p {
  max-width: 560px;
  color: #a5b4cc;
}

.hero-actions {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.hero-stat {
  min-width: 120px;
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  background: rgba(15, 23, 42, 0.7);
}

.hero-stat strong {
  display: block;
  font-size: 28px;
  line-height: 1;
  color: #f8fafc;
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

.summary-label {
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #94a3b8;
}

.summary-card strong {
  display: block;
  margin: 10px 0 8px;
  font-size: 30px;
  line-height: 1;
}

.summary-card p {
  color: #90a2bf;
  font-size: 13px;
}

.plans-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 18px;
}

.plan-card {
  display: flex;
  flex-direction: column;
  min-height: 420px;
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 26px;
  overflow: hidden;
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.94), rgba(30, 41, 59, 0.92));
  box-shadow: 0 20px 45px rgba(2, 6, 23, 0.26);
}

.plan-card--enterprise {
  background:
    radial-gradient(circle at top left, rgba(245, 158, 11, 0.22), transparent 30%),
    linear-gradient(180deg, rgba(120, 53, 15, 0.28), rgba(30, 41, 59, 0.96));
}

.plan-card--standard {
  background:
    radial-gradient(circle at top left, rgba(34, 197, 94, 0.2), transparent 30%),
    linear-gradient(180deg, rgba(21, 128, 61, 0.15), rgba(30, 41, 59, 0.96));
}

.plan-card--free {
  background:
    radial-gradient(circle at top left, rgba(148, 163, 184, 0.2), transparent 30%),
    linear-gradient(180deg, rgba(71, 85, 105, 0.24), rgba(30, 41, 59, 0.96));
}

.plan-chrome {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  padding: 22px 22px 18px;
}

.plan-badge {
  display: grid;
  place-items: center;
  width: 50px;
  height: 50px;
  border-radius: 16px;
  background: rgba(248, 250, 252, 0.1);
  color: #fff;
  flex-shrink: 0;
}

.plan-heading {
  flex: 1;
  min-width: 0;
}

.plan-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.plan-title-row h3 {
  font-size: 22px;
  line-height: 1.1;
}

.plan-heading p {
  margin-top: 10px;
  font-size: 14px;
  color: #c2d0e4;
}

.plan-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  padding: 0 22px 16px;
}

.metric-pill {
  padding: 12px 12px 10px;
  border-radius: 16px;
  background: rgba(15, 23, 42, 0.52);
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
  font-size: 18px;
}

.plan-section {
  flex: 1;
  padding: 0 22px 18px;
}

.section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  font-size: 14px;
  color: #e2e8f0;
}

.section-title small {
  color: #90a2bf;
}

.module-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.empty-hint {
  color: #90a2bf;
  font-size: 13px;
}

.plan-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 22px 22px;
  border-top: 1px solid rgba(148, 163, 184, 0.12);
}

.plan-density {
  min-width: 0;
  flex: 1;
}

.plan-density span {
  display: inline-block;
  margin-bottom: 8px;
  font-size: 12px;
  color: #94a3b8;
}

.density-bar {
  height: 8px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.14);
  overflow: hidden;
}

.density-bar > span {
  display: block;
  height: 100%;
  margin: 0;
  border-radius: inherit;
  background: linear-gradient(90deg, #38bdf8, #f59e0b);
}

.plan-actions {
  display: flex;
  gap: 8px;
}

.empty-block {
  grid-column: 1 / -1;
  padding: 40px 0;
}

.dialog-header h3 {
  margin-top: 6px;
  font-size: 24px;
}

.plan-form {
  padding-top: 6px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.form-grid--triple {
  grid-template-columns: repeat(3, minmax(0, 1fr));
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

.module-option small {
  color: #90a2bf;
}

@media (max-width: 1080px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .hero-panel {
    flex-direction: column;
    align-items: flex-start;
  }

  .hero-actions {
    justify-content: flex-start;
  }
}

@media (max-width: 720px) {
  .summary-grid,
  .form-grid,
  .form-grid--triple,
  .module-selector,
  .plan-metrics {
    grid-template-columns: 1fr;
  }

  .plan-footer {
    flex-direction: column;
    align-items: stretch;
  }

  .plan-actions {
    justify-content: flex-end;
  }
}
</style>
