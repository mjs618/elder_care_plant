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
              v-for="slug in (plan.included_modules || '').split(',').filter(Boolean)"
              :key="slug"
              size="small"
              style="margin:2px"
            >{{ slug }}</el-tag>
            <span v-if="!plan.included_modules" style="color: var(--text-muted); font-size: 12px;">无包含模块</span>
          </div>
        </div>
      </div>

      <!-- Loading/empty -->
      <el-card v-if="!loading && plans.length === 0" class="empty-card">
        <el-empty description="暂无套餐，点击右上角创建" />
      </el-card>
    </div>

    <!-- Create dialog -->
    <el-dialog v-model="showCreate" title="新建套餐" width="520px">
      <el-form :model="form" label-width="120px">
        <el-form-item label="套餐名称" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="套餐等级" required>
          <el-select v-model="form.tier" style="width:100%">
            <el-option label="免费 (Free)" value="free" />
            <el-option label="标准 (Standard)" value="standard" />
            <el-option label="企业 (Enterprise)" value="enterprise" />
          </el-select>
        </el-form-item>
        <el-form-item label="限速 (次/分)"><el-input-number v-model="form.rate_limit_rpm" :min="10" /></el-form-item>
        <el-form-item label="最大用户数"><el-input-number v-model="form.max_users" :min="1" /></el-form-item>
        <el-form-item label="最大患者数"><el-input-number v-model="form.max_patients" :min="1" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="createPlan">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Plus, Tickets } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

const plans = ref<any[]>([])
const loading = ref(false)
const showCreate = ref(false)
const creating = ref(false)
const form = reactive({ name: '', tier: 'standard', rate_limit_rpm: 60, max_users: 10, max_patients: 100, description: '' })

async function fetchPlans() {
  loading.value = true
  try {
    const res: any = await request.get('/admin/plans')
    plans.value = res.data ?? []
  } catch { plans.value = [] }
  finally { loading.value = false }
}

async function createPlan() {
  creating.value = true
  try {
    await request.post('/admin/plans', form)
    ElMessage.success('套餐创建成功')
    showCreate.value = false
    fetchPlans()
  } finally { creating.value = false }
}

function tierLabel(t: string) { return { free: '免费版', standard: '标准版', enterprise: '企业版' }[t] ?? t }
function tierTagType(t: string) { return { free: '', standard: 'success', enterprise: 'warning' }[t] ?? '' as any }

onMounted(fetchPlans)
</script>

<style scoped>
.admin-page { display: flex; flex-direction: column; gap: 20px; }
.page-head { display: flex; align-items: center; justify-content: space-between; }
.page-head h2 { font-size: 22px; font-weight: 700; }
.plans-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.plan-card { overflow: hidden; padding: 0; }
.plan-header {
  display: flex; align-items: center; gap: 14px;
  padding: 20px 20px 16px;
  background: linear-gradient(135deg, #334155, #1E293B);
}
.tier-enterprise .plan-header, .plan-card:has(.tier-enterprise) .plan-header {
  background: linear-gradient(135deg, #B45309, #92400E);
}
.plan-name { font-size: 16px; font-weight: 700; color: white; margin-bottom: 4px; }
.plan-body { padding: 16px 20px; }
.plan-stat { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid var(--border-subtle); font-size: 14px; }
.plan-stat span { color: var(--text-secondary); }
.plan-modules { margin-top: 12px; }
.empty-card { grid-column: 1 / -1; }
</style>
