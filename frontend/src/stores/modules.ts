/**
 * Module / Permission Store (Pinia)
 * Fetches the tenant's activated modules from the backend,
 * then builds the dynamic sidebar navigation accordingly.
 * This is the core of the "pluggable frontend" architecture.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { modulesApi, type ModuleInfo } from '@/api/auth'

// Navigation item generated from module registry
export interface NavItem {
    slug: string
    title: string
    icon: string
    path: string
    children?: NavItem[]
}

// Module slug → icon + base route mapping
const MODULE_META: Record<string, { icon: string; path: string; children?: { title: string; path: string }[] }> = {
    patient_mgmt: {
        icon: 'User',
        path: '/patients',
        children: [
            { title: '患者列表', path: '/patients/list' },
            { title: '健康档案', path: '/patients/health-records' },
        ],
    },
    assessment: {
        icon: 'EditPen',
        path: '/assessments',
        children: [
            { title: '评估列表', path: '/assessments/list' },
            { title: '新增评估', path: '/assessments/new' },
        ],
    },
    health_monitoring: {
        icon: 'Monitor',
        path: '/health',
        children: [
            { title: '生命体征', path: '/health/vitals' },
            { title: '用药管理', path: '/health/medications' },
        ],
    },
    ai_chat: {
        icon: 'ChatLineRound',
        path: '/ai',
        children: [
            { title: 'AI健康问答', path: '/ai/chat' },
        ],
    },
    knowledge_base: {
        icon: 'Reading',
        path: '/knowledge',
        children: [
            { title: '知识文档', path: '/knowledge/docs' },
            { title: '知识审核', path: '/knowledge/review' },
        ],
    },
    learning_center: {
        icon: 'GraduationCap',
        path: '/learning',
        children: [
            { title: '课程中心', path: '/learning/courses' },
            { title: '考试中心', path: '/learning/exams' },
        ],
    },
    reservation: {
        icon: 'Calendar',
        path: '/reservations',
    },
    care_facility: {
        icon: 'OfficeBuilding',
        path: '/facilities',
    },
}

export const useModuleStore = defineStore('modules', () => {
    const allModules = ref<ModuleInfo[]>([])
    const activeSlugs = ref<Set<string>>(new Set())
    const isLoaded = ref(false)

    // Build navigation from active modules
    const navItems = computed<NavItem[]>(() => {
        return allModules.value
            .filter((m) => activeSlugs.value.has(m.slug))
            .map((m) => {
                const meta = MODULE_META[m.slug]
                return {
                    slug: m.slug,
                    title: m.display_name,
                    icon: meta?.icon ?? 'Grid',
                    path: meta?.path ?? `/${m.slug}`,
                    children: meta?.children?.map((c) => ({
                        slug: `${m.slug}_${c.path}`,
                        title: c.title,
                        icon: '',
                        path: c.path,
                    })),
                }
            })
    })

    async function loadModules(tenantActiveSlugs?: string[]) {
        const res = await modulesApi.list()
        allModules.value = (res as any).data ?? res
        // For platform admins all modules visible; for tenants use their active set
        activeSlugs.value = new Set(tenantActiveSlugs ?? allModules.value.map((m) => m.slug))
        isLoaded.value = true
    }

    function hasModule(slug: string) {
        return activeSlugs.value.has(slug)
    }

    return { allModules, activeSlugs, isLoaded, navItems, loadModules, hasModule }
})
