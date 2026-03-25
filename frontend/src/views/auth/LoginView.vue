<template>
  <div class="login-page">
    <!-- Background gradient blobs -->
    <div class="bg-blob bg-blob-1" />
    <div class="bg-blob bg-blob-2" />

    <div class="login-card glass">
      <!-- Brand -->
      <div class="login-brand">
        <div class="brand-circle">
          <el-icon size="36" color="white"><MagicStick /></el-icon>
        </div>
        <h1 class="login-title gradient-text">老年照顾平台</h1>
        <p class="login-sub">专业的老年护理综合管理系统</p>
      </div>

      <!-- Form -->
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        class="login-form"
        @submit.prevent="handleLogin"
      >
        <el-form-item prop="email">
          <el-input
            v-model="form.email"
            size="large"
            placeholder="邮箱地址"
            :prefix-icon="Message"
            autocomplete="email"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            size="large"
            type="password"
            placeholder="密码"
            :prefix-icon="Lock"
            show-password
            autocomplete="current-password"
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <el-button
          type="primary"
          size="large"
          class="login-btn"
          :loading="loading"
          @click="handleLogin"
        >
          {{ loading ? '登录中...' : '登 录' }}
        </el-button>
      </el-form>

      <p class="login-footer">
        <el-icon><InfoFilled /></el-icon>
        如需注册或获取账号请联系管理员
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { type FormInstance } from 'element-plus'
import { MagicStick, Message, Lock, InfoFilled } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { useModuleStore } from '@/stores/modules'

const router = useRouter()
const userStore = useUserStore()
const moduleStore = useModuleStore()

const formRef = ref<FormInstance>()
const loading = ref(false)
const form = reactive({ 
  email: 'tenant@eldercare.com', 
  password: 'Tenant123!' 
})

const rules = {
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  await formRef.value?.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      await userStore.login(form.email, form.password)
      await moduleStore.loadModules()
      // Platform admins go to the admin console
      if (userStore.isPlatformAdmin) router.push('/admin/dashboard')
      else router.push('/dashboard')
    } catch (e) {
      // Axios error interceptor already shows the UI error message
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-base);
  position: relative;
  overflow: hidden;
}

/* Animated gradient blobs */
.bg-blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.18;
  animation: blob-drift 12s ease-in-out infinite alternate;
}
.bg-blob-1 {
  width: 500px; height: 500px;
  background: radial-gradient(circle, var(--brand-primary), transparent);
  top: -100px; left: -100px;
}
.bg-blob-2 {
  width: 400px; height: 400px;
  background: radial-gradient(circle, var(--brand-accent), transparent);
  bottom: -80px; right: -80px;
  animation-delay: -6s;
}
@keyframes blob-drift {
  from { transform: translate(0, 0) scale(1); }
  to   { transform: translate(40px, 30px) scale(1.1); }
}

.login-card {
  width: 420px;
  padding: 48px 40px;
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  position: relative;
  z-index: 1;
}

.login-brand {
  text-align: center;
  margin-bottom: 36px;
}
.brand-circle {
  width: 72px; height: 72px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--brand-primary), var(--brand-accent));
  display: flex; align-items: center; justify-content: center;
  margin: 0 auto 16px;
  box-shadow: var(--shadow-glow);
}
.login-title {
  font-size: 24px;
  font-weight: 800;
  margin-bottom: 6px;
}
.login-sub { color: var(--text-secondary); font-size: 14px; }

.login-form { margin-bottom: 16px; }
.login-form :deep(.el-input__wrapper) {
  background: var(--bg-elevated);
  border-color: var(--border-default);
}
.login-btn { width: 100%; margin-top: 8px; font-size: 16px; letter-spacing: 2px; }

.login-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: var(--text-muted);
  font-size: 12px;
  margin-top: 8px;
  text-align: center;
}
</style>
