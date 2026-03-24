<template>
  <div class="error-page">
    <div class="error-content">
      <div class="error-code gradient-text">403</div>
      <h2 class="error-title">无权访问</h2>
      <p class="error-sub">您没有权限访问此页面，或该功能模块未包含在当前套餐中。</p>
      <div class="error-actions">
        <el-button type="primary" @click="router.back()">返回上一页</el-button>
        <el-button @click="router.push('/')">回到首页</el-button>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { useRouter } from 'vue-router'
const router = useRouter()
</script>
<style scoped>
.error-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; }
.error-content { text-align: center; }
.error-code { font-size: 96px; font-weight: 900; line-height: 1; }
.error-title { font-size: 28px; font-weight: 700; margin: 16px 0 8px; }
.error-sub { color: var(--text-secondary); margin-bottom: 32px; }
.error-actions { display: flex; gap: 12px; justify-content: center; }
</style>
