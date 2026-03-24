<template>
  <div class="admin-layout">
    <!-- Admin Sidebar -->
    <aside class="admin-sidebar">
      <div class="admin-brand">
        <el-icon class="brand-icon"><Monitor /></el-icon>
        <div>
          <div class="brand-title">运营控制台</div>
          <div class="brand-sub">平台超级管理员</div>
        </div>
      </div>
      <nav class="admin-nav">
        <router-link
          v-for="item in adminNav"
          :key="item.path"
          :to="item.path"
          class="admin-nav-item"
          active-class="admin-nav-item--active"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.title }}</span>
        </router-link>
      </nav>
      <div class="admin-sidebar-bottom">
        <router-link to="/" class="admin-nav-item">
          <el-icon><Back /></el-icon>
          <span>切换到租户视图</span>
        </router-link>
      </div>
    </aside>
    <!-- Admin Content -->
    <div class="admin-main">
      <header class="admin-topbar glass">
        <span class="admin-topbar-title">{{ route.meta.title ?? '运营控制台' }}</span>
        <div class="topbar-right">
          <el-tag type="danger" size="small">Super Admin</el-tag>
          <el-dropdown trigger="click" @command="handleCmd">
            <div class="user-avatar">
              <el-avatar :size="32" style="background: var(--color-danger)">
                {{ userStore.profile?.username?.[0]?.toUpperCase() ?? 'A' }}
              </el-avatar>
              <span>{{ userStore.profile?.username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">
                  <el-icon><SwitchButton /></el-icon>退出登录
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
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { Monitor, DataAnalysis, OfficeBuilding, Tickets, Grid, Back, ArrowDown, SwitchButton } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const adminNav = [
  { title: '运营总览', path: '/admin/dashboard', icon: DataAnalysis },
  { title: '租户管理', path: '/admin/tenants', icon: OfficeBuilding },
  { title: '套餐管理', path: '/admin/plans', icon: Tickets },
  { title: '模块注册表', path: '/admin/modules', icon: Grid },
]

async function handleCmd(cmd: string) {
  if (cmd === 'logout') {
    await ElMessageBox.confirm('确认退出？', '退出', { type: 'warning' })
    userStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.admin-layout { display: flex; height: 100vh; overflow: hidden; }

.admin-sidebar {
  width: 220px;
  flex-shrink: 0;
  background: #0B111E;
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
}

.admin-brand {
  height: var(--topbar-height);
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 16px;
  border-bottom: 1px solid var(--border-subtle);
}
.brand-icon { font-size: 28px; color: var(--color-danger); }
.brand-title { font-size: 14px; font-weight: 700; color: var(--text-primary); }
.brand-sub { font-size: 11px; color: var(--color-danger); }

.admin-nav { flex: 1; padding: 12px 8px; }
.admin-nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 2px;
  transition: all var(--transition-fast);
}
.admin-nav-item:hover { background: var(--bg-elevated); color: var(--text-primary); }
.admin-nav-item--active {
  background: rgba(239, 68, 68, 0.15);
  color: var(--color-danger);
}

.admin-sidebar-bottom { padding: 8px; border-top: 1px solid var(--border-subtle); }

.admin-main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.admin-topbar {
  height: var(--topbar-height);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  border-bottom: 1px solid var(--border-subtle);
}
.admin-topbar-title { font-size: 18px; font-weight: 700; color: var(--text-primary); }
.topbar-right { display: flex; align-items: center; gap: 12px; }
.user-avatar {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  transition: background var(--transition-fast);
}
.user-avatar:hover { background: var(--bg-elevated); }

.admin-content { flex: 1; overflow-y: auto; padding: 24px; }
</style>
