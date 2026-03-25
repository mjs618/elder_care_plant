<template>
  <div class="settings-page">
    <h2 class="page-title">系统设置</h2>

    <el-tabs tab-position="left" class="settings-tabs">
      <!-- 品牌设置 -->
      <el-tab-pane label="品牌定制" name="brand">
        <div class="settings-section">
          <h3>白标定制</h3>
          <p class="section-desc">自定义您的机构品牌，修改将实时生效。</p>
          <el-form :model="brandForm" label-width="120px" style="max-width:500px">
            <el-form-item label="机构名称">
              <el-input v-model="brandForm.brandName" placeholder="机构显示名称" />
            </el-form-item>
            <el-form-item label="主品牌色">
              <div class="color-picker-row">
                <el-color-picker v-model="brandForm.primaryColor" @change="applyPreview" />
                <el-input v-model="brandForm.primaryColor" style="width:140px" />
              </div>
            </el-form-item>
            <el-form-item label="Logo URL">
              <el-input v-model="brandForm.logoUrl" placeholder="https://..." />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveTheme">保存并应用</el-button>
              <el-button @click="resetTheme">恢复默认</el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>

      <!-- 账号设置 -->
      <el-tab-pane label="账号安全" name="account">
        <div class="settings-section">
          <h3>账号信息</h3>
          <el-form label-width="120px" style="max-width:500px">
            <el-form-item label="当前邮箱">
              <el-input :value="userStore.profile?.email" disabled />
            </el-form-item>
            <el-form-item label="用户名">
              <el-input :value="userStore.profile?.username" disabled />
            </el-form-item>
            <el-form-item label="修改密码">
              <el-button>点击修改密码</el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>

      <!-- 关于 -->
      <el-tab-pane label="关于系统" name="about">
        <div class="settings-section">
          <h3>系统信息</h3>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="系统名称">老年照顾平台 (Elder Care Platform)</el-descriptions-item>
            <el-descriptions-item label="版本">v0.1.0</el-descriptions-item>
            <el-descriptions-item label="架构">FastAPI + PostgreSQL + Vue 3 (商业化 SaaS)</el-descriptions-item>
            <el-descriptions-item label="用户角色">{{ userStore.isPlatformAdmin ? '平台超级管理员' : '租户用户' }}</el-descriptions-item>
          </el-descriptions>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { useThemeStore } from '@/stores/theme'

const userStore = useUserStore()
const themeStore = useThemeStore()

const brandForm = reactive({
  brandName: themeStore.theme.brandName,
  primaryColor: themeStore.theme.primaryColor,
  logoUrl: themeStore.theme.logoUrl ?? '',
})

function applyPreview(color: string | null) {
  if (!color) return
  document.documentElement.style.setProperty('--brand-primary', color)
  document.documentElement.style.setProperty('--el-color-primary', color)
}

function saveTheme() {
  themeStore.applyTheme({
    brandName: brandForm.brandName,
    primaryColor: brandForm.primaryColor,
    primaryLight: brandForm.primaryColor + '99',
    primaryDark: brandForm.primaryColor,
    logoUrl: brandForm.logoUrl || null,
  })
  ElMessage.success('品牌设置已保存')
}

function resetTheme() {
  themeStore.resetTheme()
  brandForm.brandName = themeStore.theme.brandName
  brandForm.primaryColor = themeStore.theme.primaryColor
  brandForm.logoUrl = ''
  ElMessage.success('已恢复默认主题')
}
</script>

<style scoped>
.settings-page { display: flex; flex-direction: column; gap: 24px; }
.page-title { font-size: 22px; font-weight: 700; }
.settings-tabs { min-height: 500px; }
.settings-section { padding: 0 24px; }
.settings-section h3 { font-size: 17px; font-weight: 700; margin-bottom: 8px; }
.section-desc { color: var(--text-secondary); font-size: 13px; margin-bottom: 24px; }
.color-picker-row { display: flex; align-items: center; gap: 12px; }
</style>
