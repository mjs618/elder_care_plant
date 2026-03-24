<template>
  <div class="error-page">
    <div class="error-content">
      <div class="error-code gradient-text">404</div>
      <h2 class="error-title">页面不存在</h2>
      <p class="error-sub">您访问的页面不存在，请检查链接或返回首页。</p>
      <el-button type="primary" @click="router.push('/')">回到首页</el-button>
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
</style>
