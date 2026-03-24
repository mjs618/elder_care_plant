<template>
  <div class="module-page">
    <div class="page-head">
      <h2>患者列表</h2>
      <el-button type="primary" :icon="Plus">新增患者</el-button>
    </div>
    <el-card class="table-card">
      <el-empty description="患者数据加载中，此模块需连接后端患者服务" />
    </el-card>
  </div>
</template>
<script setup lang="ts">
import { Plus } from '@element-plus/icons-vue'
</script>
<style scoped>
.module-page { display: flex; flex-direction: column; gap: 20px; }
.page-head { display: flex; align-items: center; justify-content: space-between; }
.page-head h2 { font-size: 22px; font-weight: 700; }
.table-card { padding: 8px; }
</style>
