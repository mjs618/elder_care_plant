<template>
  <div class="module-page">
    <div class="page-head">
      <h2>用药管理</h2>
      <el-button type="primary" :icon="Plus">新增用药</el-button>
    </div>
    <el-card><el-empty description="用药计划 — 连接后端后显示药品与用药提醒" /></el-card>
  </div>
</template>
<script setup lang="ts">
import { Plus } from '@element-plus/icons-vue'
</script>
<style scoped>
.module-page { display: flex; flex-direction: column; gap: 20px; }
.page-head { display: flex; align-items: center; justify-content: space-between; }
.page-head h2 { font-size: 22px; font-weight: 700; }
</style>
