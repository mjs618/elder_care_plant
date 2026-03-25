<template>
  <div class="module-page">
    <div class="page-head">
      <h2>课程中心</h2>
      <el-button type="primary" :icon="Plus">发布课程</el-button>
    </div>
    <div class="filter-bar">
      <el-input placeholder="搜索课程..." :prefix-icon="Search" style="width:260px" />
      <el-select placeholder="课程分类" style="width:160px">
        <el-option label="全部" value="" />
        <el-option label="护理技能" value="nursing" />
        <el-option label="疾病护理" value="disease" />
        <el-option label="康复训练" value="rehab" />
        <el-option label="心理关怀" value="psychology" />
      </el-select>
    </div>
    <el-card><el-empty description="课程中心 — 连接后端后展示课程卡片列表" /></el-card>
  </div>
</template>
<script setup lang="ts">
import { Plus, Search } from '@element-plus/icons-vue'
</script>
<style scoped>
.module-page { display: flex; flex-direction: column; gap: 20px; }
.page-head { display: flex; align-items: center; justify-content: space-between; }
.page-head h2 { font-size: 22px; font-weight: 700; }
.filter-bar { display: flex; gap: 12px; }
</style>
