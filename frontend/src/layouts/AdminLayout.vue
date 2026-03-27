<template>
  <div class="admin-layout">
    <aside class="admin-sidebar">
      <div class="sidebar-glow sidebar-glow--top" />
      <div class="sidebar-glow sidebar-glow--bottom" />

      <button class="admin-brand" type="button" @click="router.push('/admin/dashboard')">
        <div class="brand-mark">
          <el-icon><Monitor /></el-icon>
        </div>
        <div class="brand-copy">
          <span class="brand-eyebrow">Platform Command</span>
          <strong class="brand-title">运营控制台</strong>
          <span class="brand-sub">多租户平台运营与版本编排</span>
        </div>
      </button>

      <nav class="admin-nav">
        <router-link
          v-for="item in adminNav"
          :key="item.path"
          :to="item.path"
          class="admin-nav-item"
          active-class="admin-nav-item--active"
        >
          <span class="nav-icon">
            <el-icon><component :is="item.icon" /></el-icon>
          </span>
          <span class="nav-copy">
            <span class="nav-title">{{ item.title }}</span>
            <span class="nav-desc">{{ item.description }}</span>
          </span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div class="footer-panel">
          <span class="footer-label">当前身份</span>
          <strong class="footer-role">Super Admin</strong>
        </div>
        <router-link to="/" class="switch-link">
          <el-icon><Back /></el-icon>
          <span>切换到租户视图</span>
        </router-link>
      </div>
    </aside>

    <div class="admin-main">
      <header class="admin-topbar glass">
        <div class="topbar-copy">
          <span class="topbar-eyebrow">Operations Hub</span>
          <h1 class="topbar-title">{{ route.meta.title ?? '运营控制台' }}</h1>
        </div>

        <div class="topbar-right">
          <div class="status-pill">
            <span class="status-dot" />
            <span>平台运行中</span>
          </div>
          <el-tag type="danger" effect="dark" round>Super Admin</el-tag>

          <el-dropdown trigger="click" @command="handleCmd">
            <button class="user-chip" type="button">
              <el-avatar :size="34" class="user-avatar">
                {{ userStore.profile?.username?.[0]?.toUpperCase() ?? 'A' }}
              </el-avatar>
              <span class="user-meta">
                <strong>{{ userStore.profile?.full_name || userStore.profile?.username }}</strong>
                <span>{{ userStore.profile?.username }}</span>
              </span>
              <el-icon><ArrowDown /></el-icon>
            </button>

            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <main class="admin-content">
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import {
  ArrowDown,
  Back,
  DataAnalysis,
  Grid,
  Monitor,
  OfficeBuilding,
  SwitchButton,
  Tickets,
} from '@element-plus/icons-vue'

import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const adminNav = [
  {
    title: '运营总览',
    description: '监控平台增长与模块热度',
    path: '/admin/dashboard',
    icon: DataAnalysis,
  },
  {
    title: '租户管理',
    description: '查看租户状态与套餐分配',
    path: '/admin/tenants',
    icon: OfficeBuilding,
  },
  {
    title: '套餐管理',
    description: '设计商业套餐与模块组合',
    path: '/admin/plans',
    icon: Tickets,
  },
  {
    title: '模块注册表',
    description: '管理模块启停、版本和热度',
    path: '/admin/modules',
    icon: Grid,
  },
]

async function handleCmd(cmd: string) {
  if (cmd !== 'logout') return

  await ElMessageBox.confirm('确认退出当前运营控制台？', '退出登录', {
    type: 'warning',
  })
  await userStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.admin-layout {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  min-height: 100vh;
  background:
    radial-gradient(circle at top right, rgba(244, 63, 94, 0.12), transparent 24%),
    radial-gradient(circle at 12% 18%, rgba(59, 130, 246, 0.12), transparent 20%),
    linear-gradient(180deg, #08101f 0%, #0f172a 44%, #111827 100%);
}

.admin-sidebar {
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 26px 18px 18px;
  border-right: 1px solid rgba(148, 163, 184, 0.12);
  background:
    linear-gradient(180deg, rgba(7, 14, 28, 0.96) 0%, rgba(11, 18, 33, 0.92) 100%);
}

.sidebar-glow {
  position: absolute;
  border-radius: 999px;
  filter: blur(70px);
  opacity: 0.4;
  pointer-events: none;
}

.sidebar-glow--top {
  top: -52px;
  left: -24px;
  width: 180px;
  height: 180px;
  background: rgba(59, 130, 246, 0.22);
}

.sidebar-glow--bottom {
  right: -36px;
  bottom: 88px;
  width: 170px;
  height: 170px;
  background: rgba(244, 63, 94, 0.18);
}

.admin-brand {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr);
  gap: 14px;
  margin-bottom: 24px;
  padding: 18px 16px;
  text-align: left;
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 22px;
  background: linear-gradient(145deg, rgba(15, 23, 42, 0.94), rgba(17, 24, 39, 0.8));
  cursor: pointer;
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 52px;
  height: 52px;
  border-radius: 18px;
  color: #fff;
  background: linear-gradient(145deg, #ef4444, #fb7185);
  box-shadow: 0 18px 30px rgba(239, 68, 68, 0.28);
}

.brand-mark :deep(.el-icon) {
  font-size: 26px;
}

.brand-copy {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.brand-eyebrow,
.topbar-eyebrow,
.footer-label {
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(148, 163, 184, 0.74);
}

.brand-title {
  font-size: 22px;
  line-height: 1.1;
  color: #f8fafc;
}

.brand-sub {
  font-size: 13px;
  color: #9fb0ca;
}

.admin-nav {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
}

.admin-nav-item {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
  padding: 14px 14px 14px 12px;
  text-decoration: none;
  border: 1px solid transparent;
  border-radius: 18px;
  color: #ced8ea;
  transition: transform var(--transition-fast), border-color var(--transition-fast), background var(--transition-fast);
}

.admin-nav-item:hover {
  transform: translateX(4px);
  border-color: rgba(148, 163, 184, 0.14);
  background: rgba(15, 23, 42, 0.46);
}

.admin-nav-item--active {
  border-color: rgba(244, 63, 94, 0.18);
  background: linear-gradient(90deg, rgba(127, 29, 29, 0.46), rgba(30, 41, 59, 0.18));
  box-shadow: inset 0 0 0 1px rgba(244, 63, 94, 0.06);
}

.nav-icon {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border-radius: 14px;
  color: #f8fafc;
  background: rgba(30, 41, 59, 0.84);
}

.admin-nav-item--active .nav-icon {
  background: linear-gradient(145deg, rgba(239, 68, 68, 0.88), rgba(251, 113, 133, 0.9));
}

.nav-copy {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.nav-title {
  font-size: 15px;
  font-weight: 700;
  color: #f8fafc;
}

.nav-desc {
  font-size: 12px;
  color: #90a2bf;
}

.sidebar-footer {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-top: 18px;
  border-top: 1px solid rgba(148, 163, 184, 0.12);
}

.footer-panel {
  padding: 14px 16px;
  border-radius: 18px;
  background: rgba(15, 23, 42, 0.68);
  border: 1px solid rgba(148, 163, 184, 0.12);
}

.footer-role {
  display: block;
  margin-top: 4px;
  color: #f8fafc;
  font-size: 15px;
}

.switch-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  border-radius: 16px;
  color: #c6d3e5;
  text-decoration: none;
  background: rgba(15, 23, 42, 0.44);
  transition: background var(--transition-fast), transform var(--transition-fast);
}

.switch-link:hover {
  background: rgba(30, 41, 59, 0.78);
  transform: translateX(2px);
}

.admin-main {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.admin-topbar {
  position: sticky;
  top: 0;
  z-index: 5;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 82px;
  padding: 18px 28px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
  background: rgba(8, 14, 28, 0.64);
}

.topbar-copy {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.topbar-title {
  font-size: 28px;
  line-height: 1.1;
  color: #f8fafc;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 999px;
  color: #d7e6f8;
  background: rgba(15, 23, 42, 0.72);
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #22c55e;
  box-shadow: 0 0 0 6px rgba(34, 197, 94, 0.14);
}

.user-chip {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px 6px 6px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 999px;
  color: #f8fafc;
  background: rgba(15, 23, 42, 0.72);
  cursor: pointer;
}

.user-avatar {
  background: linear-gradient(145deg, #ef4444, #fb7185);
}

.user-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  line-height: 1.15;
}

.user-meta strong {
  font-size: 14px;
}

.user-meta span {
  font-size: 12px;
  color: #93a4c0;
}

.admin-content {
  flex: 1;
  overflow: auto;
  padding: 28px;
}

@media (max-width: 1100px) {
  .admin-layout {
    grid-template-columns: 1fr;
  }

  .admin-sidebar {
    padding-bottom: 20px;
    border-right: 0;
    border-bottom: 1px solid rgba(148, 163, 184, 0.12);
  }

  .admin-nav {
    flex-direction: row;
    overflow: auto;
    padding-bottom: 8px;
  }

  .admin-nav-item {
    min-width: 230px;
  }

  .sidebar-footer {
    display: none;
  }
}

@media (max-width: 760px) {
  .admin-topbar {
    flex-direction: column;
    align-items: stretch;
  }

  .topbar-right {
    justify-content: space-between;
    flex-wrap: wrap;
  }

  .admin-content {
    padding: 18px;
  }
}
</style>
