<template>
  <div class="admin-page">
    <div class="page-head">
      <h2>模块注册表</h2>
      <el-tag>共 {{ moduleStore.allModules.length }} 个模块</el-tag>
    </div>

    <div class="modules-grid">
      <div v-for="mod in moduleStore.allModules" :key="mod.slug" class="mod-card card">
        <div class="mod-head">
          <div class="mod-icon">
            <el-icon size="22" color="white"><Grid /></el-icon>
          </div>
          <div>
            <div class="mod-name">{{ mod.display_name }}</div>
            <code class="mod-slug">{{ mod.slug }}</code>
          </div>
          <el-tag size="small" type="success" class="mod-ver">v{{ mod.version }}</el-tag>
        </div>
        <p class="mod-desc">{{ mod.description }}</p>
        <div class="mod-perms">
          <span class="perms-label">权限：</span>
          <el-tag
            v-for="p in mod.permissions"
            :key="p"
            size="small"
            type="info"
            style="margin: 2px; font-family: var(--font-mono); font-size: 11px;"
          >{{ p }}</el-tag>
        </div>
      </div>
    </div>

    <el-empty v-if="moduleStore.allModules.length === 0" description="模块列表加载中..." />
  </div>
</template>

<script setup lang="ts">
import { Grid } from '@element-plus/icons-vue'
import { useModuleStore } from '@/stores/modules'

const moduleStore = useModuleStore()
</script>

<style scoped>
.admin-page { display: flex; flex-direction: column; gap: 20px; }
.page-head { display: flex; align-items: center; gap: 12px; }
.page-head h2 { font-size: 22px; font-weight: 700; }
.modules-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
.mod-card { padding: 20px; }
.mod-head { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.mod-icon {
  width: 44px; height: 44px; border-radius: var(--radius-md); flex-shrink: 0;
  background: linear-gradient(135deg, var(--brand-primary), var(--brand-accent));
  display: flex; align-items: center; justify-content: center;
}
.mod-name { font-size: 15px; font-weight: 700; color: var(--text-primary); }
.mod-slug { font-size: 12px; color: var(--text-muted); font-family: var(--font-mono); }
.mod-ver { margin-left: auto; }
.mod-desc { font-size: 13px; color: var(--text-secondary); margin-bottom: 12px; line-height: 1.5; }
.mod-perms { display: flex; flex-wrap: wrap; align-items: center; gap: 2px; }
.perms-label { font-size: 12px; color: var(--text-muted); margin-right: 4px; }
</style>
