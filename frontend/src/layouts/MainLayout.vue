<template>
  <div class="main-layout">
    <!-- Sidebar -->
    <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <!-- Brand Logo -->
      <div class="sidebar-brand" @click="router.push('/dashboard')">
        <img v-if="themeStore.theme.logoUrl" :src="themeStore.theme.logoUrl" class="brand-logo" />
        <el-icon v-else class="brand-icon"><Heart /></el-icon>
        <span v-if="!sidebarCollapsed" class="brand-name">{{ themeStore.theme.brandName }}</span>
      </div>

      <!-- Navigation -->
      <nav class="sidebar-nav">
        <!-- Dashboard always visible -->
        <router-link to="/dashboard" class="nav-item" active-class="nav-item--active">
          <el-icon><HomeFilled /></el-icon>
          <span v-if="!sidebarCollapsed">工作台</span>
        </router-link>

        <!-- Dynamic module navigation -->
        <template v-for="item in moduleStore.navItems" :key="item.slug">
          <template v-if="item.children?.length">
            <div
              class="nav-group"
              :class="{ 'nav-group--open': openGroups.has(item.slug) }"
              @click="toggleGroup(item.slug)"
            >
              <el-icon><component :is="item.icon" /></el-icon>
              <span v-if="!sidebarCollapsed">{{ item.title }}</span>
              <el-icon v-if="!sidebarCollapsed" class="nav-group-arrow">
                <ArrowDown />
              </el-icon>
            </div>
            <transition name="nav-expand">
              <div v-if="!sidebarCollapsed && openGroups.has(item.slug)" class="nav-children">
                <router-link
                  v-for="child in item.children"
                  :key="child.path"
                  :to="child.path"
                  class="nav-child"
                  active-class="nav-child--active"
                >
                  {{ child.title }}
                </router-link>
              </div>
            </transition>
          </template>
          <router-link
            v-else
            :to="item.path"
            class="nav-item"
            active-class="nav-item--active"
          >
            <el-icon><component :is="item.icon" /></el-icon>
            <span v-if="!sidebarCollapsed">{{ item.title }}</span>
          </router-link>
        </template>
      </nav>

      <!-- Bottom links -->
      <div class="sidebar-bottom">
        <router-link to="/settings" class="nav-item" active-class="nav-item--active">
          <el-icon><Setting /></el-icon>
          <span v-if="!sidebarCollapsed">系统设置</span>
        </router-link>
      </div>
    </aside>

    <!-- Main area -->
    <div class="main-area">
      <!-- Top bar -->
      <header class="topbar glass">
        <div class="topbar-left">
          <el-button text circle @click="sidebarCollapsed = !sidebarCollapsed">
            <el-icon size="20"><Expand v-if="sidebarCollapsed" /><Fold v-else /></el-icon>
          </el-button>
          <!-- Breadcrumb -->
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="route.meta.title">{{ route.meta.title }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="topbar-right">
          <!-- Plan badge -->
          <el-tag size="small" type="info" class="plan-badge">
            {{ userStore.isPlatformAdmin ? '超级管理员' : '租户用户' }}
          </el-tag>
          <!-- User menu -->
          <el-dropdown trigger="click" @command="handleUserCmd">
            <div class="user-avatar">
              <el-avatar :size="34" style="background: var(--brand-primary)">
                {{ userStore.profile?.username?.[0]?.toUpperCase() ?? 'U' }}
              </el-avatar>
              <span class="user-name">{{ userStore.profile?.username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="admin" v-if="userStore.isPlatformAdmin">
                  <el-icon><Setting /></el-icon> 运营控制台
                </el-dropdown-item>
                <el-dropdown-item command="tenant" v-if="userStore.isPlatformAdmin">
                  <el-icon><SwitchButton /></el-icon> 切换到租户视图
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon> 退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- Page content -->
      <main class="page-content">
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
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useModuleStore } from '@/stores/modules'
import { useThemeStore } from '@/stores/theme'
import {
  HomeFilled, Setting, ArrowDown, Expand, Fold,
  MagicStick, SwitchButton,
} from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const moduleStore = useModuleStore()
const themeStore = useThemeStore()

const sidebarCollapsed = ref(false)
const openGroups = reactive(new Set<string>())

function toggleGroup(slug: string) {
  if (openGroups.has(slug)) openGroups.delete(slug)
  else openGroups.add(slug)
}

async function handleUserCmd(cmd: string) {
  if (cmd === 'admin') router.push('/admin')
  else if (cmd === 'tenant') router.push('/')
  else if (cmd === 'logout') {
    await ElMessageBox.confirm('确认退出登录？', '退出', { type: 'warning' })
    userStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.main-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--bg-base);
}

/* ── Sidebar ──────────────────────────────────────────────────────────────── */
.sidebar {
  width: var(--sidebar-width);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--bg-surface);
  border-right: 1px solid var(--border-subtle);
  transition: width var(--transition-base);
  overflow: hidden;
}
.sidebar.collapsed { width: var(--sidebar-collapsed); }

.sidebar-brand {
  height: var(--topbar-height);
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 16px;
  cursor: pointer;
  border-bottom: 1px solid var(--border-subtle);
  overflow: hidden;
}
.brand-logo { width: 32px; height: 32px; border-radius: var(--radius-sm); object-fit: cover; }
.brand-icon { font-size: 28px; color: var(--brand-primary); flex-shrink: 0; }
.brand-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  white-space: nowrap;
  background: linear-gradient(135deg, var(--brand-primary), var(--brand-accent));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.sidebar-nav { flex: 1; overflow-y: auto; padding: 12px 8px; }

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: all var(--transition-fast);
  cursor: pointer;
  margin-bottom: 2px;
}
.nav-item:hover { background: var(--bg-elevated); color: var(--text-primary); }
.nav-item--active {
  background: rgba(59, 130, 246, 0.15);
  color: var(--brand-primary);
}
.nav-item--active .el-icon { color: var(--brand-primary); }

.nav-group {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
  margin-bottom: 2px;
}
.nav-group:hover { background: var(--bg-elevated); color: var(--text-primary); }
.nav-group-arrow { margin-left: auto; transition: transform var(--transition-fast); }
.nav-group--open .nav-group-arrow { transform: rotate(180deg); }

.nav-children { padding-left: 36px; }
.nav-child {
  display: block;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 13px;
  transition: all var(--transition-fast);
  margin-bottom: 1px;
}
.nav-child:hover { color: var(--text-primary); background: var(--bg-elevated); }
.nav-child--active { color: var(--brand-primary); background: rgba(59,130,246,0.1); }

.nav-expand-enter-active, .nav-expand-leave-active {
  transition: all var(--transition-fast);
  overflow: hidden;
}
.nav-expand-enter-from, .nav-expand-leave-to { opacity: 0; max-height: 0; }
.nav-expand-enter-to, .nav-expand-leave-from { opacity: 1; max-height: 200px; }

.sidebar-bottom { padding: 8px; border-top: 1px solid var(--border-subtle); }

/* ── Main area ────────────────────────────────────────────────────────────── */
.main-area { flex: 1; display: flex; flex-direction: column; overflow: hidden; }

.topbar {
  height: var(--topbar-height);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--content-pad);
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}
.topbar-left, .topbar-right { display: flex; align-items: center; gap: 16px; }

.plan-badge { border-radius: var(--radius-full); }

.user-avatar {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: var(--radius-md);
  transition: background var(--transition-fast);
}
.user-avatar:hover { background: var(--bg-elevated); }
.user-name { font-size: 14px; font-weight: 500; color: var(--text-primary); }

.page-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--content-pad);
  background: var(--bg-base);
}
</style>
