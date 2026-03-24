<template>
  <div class="dashboard">
    <!-- Welcome header -->
    <div class="welcome-header">
      <div>
        <h2 class="welcome-title">
          早上好，<span class="gradient-text">{{ userStore.profile?.username }}</span> 👋
        </h2>
        <p class="welcome-sub">{{ dayjs().format('YYYY年MM月DD日 dddd') }}</p>
      </div>
      <el-tag type="success" size="large" round>系统运行正常</el-tag>
    </div>

    <!-- KPI Cards -->
    <div class="kpi-grid">
      <div v-for="kpi in kpiCards" :key="kpi.label" class="kpi-card card">
        <div class="kpi-icon" :style="{ background: kpi.gradient }">
          <el-icon size="24" color="white"><component :is="kpi.icon" /></el-icon>
        </div>
        <div class="kpi-info">
          <div class="kpi-value">{{ kpi.value }}</div>
          <div class="kpi-label">{{ kpi.label }}</div>
        </div>
        <div class="kpi-trend" :class="kpi.trend > 0 ? 'up' : 'down'">
          <el-icon><component :is="kpi.trend > 0 ? 'Top' : 'Bottom'" /></el-icon>
          {{ Math.abs(kpi.trend) }}%
        </div>
      </div>
    </div>

    <!-- Active modules -->
    <div class="section-header">
      <h3 class="section-title">已开通功能模块</h3>
    </div>
    <div class="modules-grid">
      <router-link
        v-for="item in moduleStore.navItems"
        :key="item.slug"
        :to="item.children?.[0]?.path ?? item.path"
        class="module-card card"
      >
        <el-icon size="28" :style="{ color: 'var(--brand-primary)' }">
          <component :is="item.icon" />
        </el-icon>
        <div class="module-name">{{ item.title }}</div>
        <el-tag size="small" type="success">已激活</el-tag>
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import dayjs from 'dayjs'
import 'dayjs/locale/zh-cn'
import { useUserStore } from '@/stores/user'
import { useModuleStore } from '@/stores/modules'
import { User, EditPen, Monitor, ChatLineRound } from '@element-plus/icons-vue'

dayjs.locale('zh-cn')
const userStore = useUserStore()
const moduleStore = useModuleStore()

const kpiCards = [
  { label: '在管患者', value: '—', trend: 5.2, icon: User, gradient: 'linear-gradient(135deg,#3B82F6,#8B5CF6)' },
  { label: '本月评估', value: '—', trend: 12.1, icon: EditPen, gradient: 'linear-gradient(135deg,#10B981,#3B82F6)' },
  { label: '健康预警', value: '—', trend: -3.5, icon: Monitor, gradient: 'linear-gradient(135deg,#F59E0B,#EF4444)' },
  { label: 'AI问答次数', value: '—', trend: 8.0, icon: ChatLineRound, gradient: 'linear-gradient(135deg,#8B5CF6,#10B981)' },
]
</script>

<style scoped>
.dashboard { display: flex; flex-direction: column; gap: 28px; }

.welcome-header { display: flex; align-items: center; justify-content: space-between; }
.welcome-title { font-size: 26px; font-weight: 700; margin-bottom: 4px; }
.welcome-sub { color: var(--text-secondary); font-size: 14px; }

.kpi-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; }
.kpi-card {
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  transition: transform var(--transition-base), box-shadow var(--transition-base);
}
.kpi-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
.kpi-icon {
  width: 52px; height: 52px;
  border-radius: var(--radius-md);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.kpi-info { flex: 1; }
.kpi-value { font-size: 28px; font-weight: 700; color: var(--text-primary); line-height: 1; }
.kpi-label { font-size: 13px; color: var(--text-secondary); margin-top: 4px; }
.kpi-trend { display: flex; align-items: center; gap: 2px; font-size: 13px; font-weight: 600; }
.kpi-trend.up { color: var(--color-success); }
.kpi-trend.down { color: var(--color-danger); }

.section-header { display: flex; align-items: center; justify-content: space-between; }
.section-title { font-size: 18px; font-weight: 700; color: var(--text-primary); }

.modules-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }
.module-card {
  padding: 20px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  transition: all var(--transition-base);
  cursor: pointer;
}
.module-card:hover { transform: translateY(-3px); box-shadow: var(--shadow-md); border-color: var(--brand-primary); }
.module-name { font-size: 14px; font-weight: 600; color: var(--text-primary); }
</style>
