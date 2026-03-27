/**
 * Vue Router — Dual-Mode Dynamic Routing
 *
 * Route structure:
 *   /login          → Public
 *   /               → MainLayout  (Tenant admin console)
 *   /admin/*        → AdminLayout (Platform super-admin console)
 *
 * Navigation Guard:
 *   - Unauthenticated → /login
 *   - Tenant user accessing /admin/* → 403
 *   - After login: loads modules and injects tenant dynamic routes
 */
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'

// ── Static routes (always available) ──────────────────────────────────────────
const staticRoutes: RouteRecordRaw[] = [
    {
        path: '/login',
        name: 'Login',
        component: () => import('@/views/auth/LoginView.vue'),
        meta: { public: true, title: '登录' },
    },
    {
        path: '/403',
        name: 'Forbidden',
        component: () => import('@/views/errors/ForbiddenView.vue'),
        meta: { public: true, title: '无权访问' },
    },
    {
        path: '/404',
        name: 'NotFound',
        component: () => import('@/views/errors/NotFoundView.vue'),
        meta: { public: true, title: '页面不存在' },
    },
    // Platform Super Admin Console
    {
        path: '/admin',
        component: () => import('@/layouts/AdminLayout.vue'),
        meta: { requiresAuth: true, requiresPlatformAdmin: true },
        children: [
            {
                path: '',
                redirect: '/admin/dashboard',
            },
            {
                path: 'dashboard',
                name: 'AdminDashboard',
                component: () => import('@/views/admin/AdminDashboard.vue'),
                meta: { title: '运营总览', icon: 'DataAnalysis' },
            },
            {
                path: 'tenants',
                name: 'TenantsManage',
                component: () => import('@/views/admin/TenantsManage.vue'),
                meta: { title: '租户管理', icon: 'OfficeBuilding' },
            },
            {
                path: 'plans',
                name: 'PlansManage',
                component: () => import('@/views/admin/PlansManage.vue'),
                meta: { title: '套餐管理', icon: 'Tickets' },
            },
            {
                path: 'modules',
                name: 'ModulesRegistry',
                component: () => import('@/views/admin/ModulesRegistry.vue'),
                meta: { title: '模块注册表', icon: 'Grid' },
            },
        ],
    },
    // Tenant Console (main app shell — dynamic children added after login)
    {
        path: '/',
        component: () => import('@/layouts/MainLayout.vue'),
        meta: { requiresAuth: true },
        children: [
            {
                path: '',
                redirect: '/dashboard',
            },
            {
                path: 'dashboard',
                name: 'Dashboard',
                component: () => import('@/views/tenant/DashboardView.vue'),
                meta: { title: '工作台', icon: 'HomeFilled' },
            },
            // Business module routes — registered dynamically after login
            {
                path: 'patients',
                component: () => import('@/views/tenant/patients/PatientsLayout.vue'),
                children: [
                    { path: '', redirect: 'list' },
                    { path: 'list', name: 'PatientList', component: () => import('@/views/tenant/patients/PatientList.vue'), meta: { title: '患者列表', module: 'patient_mgmt' } },
                    { path: 'health-records', name: 'HealthRecords', component: () => import('@/views/tenant/patients/HealthRecords.vue'), meta: { title: '健康档案', module: 'patient_mgmt' } },
                ],
            },
            {
                path: 'assessments',
                component: () => import('@/views/tenant/assessments/AssessmentsLayout.vue'),
                children: [
                    { path: '', redirect: 'list' },
                    { path: 'list', name: 'AssessmentList', component: () => import('@/views/tenant/assessments/AssessmentList.vue'), meta: { title: '评估列表', module: 'assessment' } },
                ],
            },
            {
                path: 'health',
                component: () => import('@/views/tenant/health/HealthLayout.vue'),
                children: [
                    { path: '', redirect: 'vitals' },
                    { path: 'vitals', name: 'Vitals', component: () => import('@/views/tenant/health/VitalsView.vue'), meta: { title: '生命体征', module: 'health_monitoring' } },
                    { path: 'medications', name: 'Medications', component: () => import('@/views/tenant/health/MedicationsView.vue'), meta: { title: '用药管理', module: 'health_monitoring' } },
                ],
            },
            {
                path: 'ai',
                children: [
                    { path: 'chat', name: 'AIChat', component: () => import('@/views/tenant/ai/AIChatView.vue'), meta: { title: 'AI健康问答', module: 'ai_chat' } },
                ],
            },
            {
                path: 'knowledge',
                children: [
                    { path: 'docs', name: 'KnowledgeDocs', component: () => import('@/views/tenant/knowledge/KnowledgeDocs.vue'), meta: { title: '知识文档', module: 'knowledge_base' } },
                ],
            },
            {
                path: 'learning',
                children: [
                    { path: 'courses', name: 'Courses', component: () => import('@/views/tenant/learning/CoursesView.vue'), meta: { title: '课程中心', module: 'learning_center' } },
                ],
            },
            {
                path: 'settings',
                name: 'Settings',
                component: () => import('@/views/tenant/SettingsView.vue'),
                meta: { title: '系统设置', icon: 'Setting' },
            },
        ],
    },
    // Catch-all
    { path: '/:pathMatch(.*)*', redirect: '/404' },
]

const router = createRouter({
    history: createWebHistory(),
    routes: staticRoutes,
    scrollBehavior: () => ({ top: 0 }),
})

// ── Navigation Guard ──────────────────────────────────────────────────────────
NProgress.configure({ showSpinner: false })

router.beforeEach(async (to, _from, next) => {
    NProgress.start()

    // Lazy import to avoid circular dependency with main.ts
    const { useUserStore } = await import('@/stores/user')
    const { useModuleStore } = await import('@/stores/modules')
    const userStore = useUserStore()
    const moduleStore = useModuleStore()

    // Public routes — allow through
    if (to.meta.public) return next()

    // Not authenticated → login
    if (!userStore.isLoggedIn) return next('/login')

    // Load user profile on first navigation after token restore
    if (!userStore.profile) {
        try {
            await userStore.fetchProfile()
        } catch {
            userStore.clearSession()
            return next('/login')
        }
    }

    // Load module registry once
    if (!moduleStore.isLoaded) {
        await moduleStore.loadModules()
    }

    // Platform admin only routes
    if (to.meta.requiresPlatformAdmin && !userStore.isPlatformAdmin) {
        return next('/403')
    }

    // Module-gated routes
    const requiredModule = to.meta.module as string | undefined
    if (requiredModule && !userStore.isPlatformAdmin && !moduleStore.hasModule(requiredModule)) {
        return next('/403')
    }

    next()
})

router.afterEach(() => NProgress.done())

export default router
