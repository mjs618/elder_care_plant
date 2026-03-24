<template>
  <div class="admin-dashboard">
    <div class="page-header">
      <h2 class="page-title">运营总览</h2>
      <el-tag type="danger">平台超级管理员视图</el-tag>
    </div>

    <!-- Stats -->
    <div class="stats-grid">
      <div v-for="s in stats" :key="s.label" class="stat-card card">
        <div class="stat-num" :style="{ color: s.color }">{{ s.value }}</div>
        <div class="stat-label">{{ s.label }}</div>
      </div>
    </div>

    <!-- Active modules list -->
    <div class="card modules-list">
      <div class="list-header">
        <h3>已注册业务模块</h3>
        <el-tag size="small">{{ moduleStore.allModules.length }} 个</el-tag>
      </div>
      <el-table :data="moduleStore.allModules" size="small" style="width: 100%">
        <el-table-column prop="slug" label="模块标识" width="180" />
        <el-table-column prop="display_name" label="显示名称" />
        <el-table-column prop="version" label="版本" width="80" />
        <el-table-column label="权限数" width="80">
          <template #default="{ row }">{{ row.permissions.length }}</template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default>
            <el-tag size="small" type="success">已注册</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useModuleStore } from '@/stores/modules'

const moduleStore = useModuleStore()

const stats = [
  { label: '租户总数', value: '—', color: 'var(--brand-primary)' },
  { label: '套餐总数', value: '—', color: 'var(--color-success)' },
  { label: '业务模块', value: moduleStore.allModules.length, color: 'var(--brand-accent)' },
  { label: '在线 API', value: '正常', color: 'var(--color-success)' },
]
</script>

<style scoped>
.admin-dashboard { display: flex; flex-direction: column; gap: 24px; }
.page-header { display: flex; align-items: center; gap: 12px; }
.page-title { font-size: 24px; font-weight: 700; }
.stats-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 16px; }
.stat-card { padding: 24px; text-align: center; }
.stat-num { font-size: 36px; font-weight: 800; }
.stat-label { font-size: 13px; color: var(--text-secondary); margin-top: 6px; }
.modules-list { padding: 20px; }
.list-header { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
.list-header h3 { font-size: 16px; font-weight: 700; }
</style>
