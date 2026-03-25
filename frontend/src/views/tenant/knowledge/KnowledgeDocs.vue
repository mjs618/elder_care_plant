<template>
  <div class="module-page">
    <div class="page-head">
      <h2>知识文档</h2>
      <el-button type="primary" :icon="Upload">上传文档</el-button>
    </div>
    <div class="filter-bar">
      <el-input placeholder="搜索知识库..." :prefix-icon="Search" style="width:280px" />
      <el-select placeholder="文档状态" style="width:140px">
        <el-option label="全部" value="" />
        <el-option label="已发布" value="published" />
        <el-option label="审核中" value="reviewing" />
        <el-option label="草稿" value="draft" />
      </el-select>
    </div>
    <el-card><el-empty description="知识文档 — 连接后端后显示知识库文档列表" /></el-card>
  </div>
</template>
<script setup lang="ts">
import { Upload, Search } from '@element-plus/icons-vue'
</script>
<style scoped>
.module-page { display: flex; flex-direction: column; gap: 20px; }
.page-head { display: flex; align-items: center; justify-content: space-between; }
.page-head h2 { font-size: 22px; font-weight: 700; }
.filter-bar { display: flex; gap: 12px; }
</style>
