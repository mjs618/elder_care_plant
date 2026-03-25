/**
 * Module / Permission Store (Pinia)
 * Fetches the tenant's activated modules from the backend,
 * then builds the dynamic sidebar navigation accordingly.
 * This is the core of the "pluggable frontend" architecture.
 * 
 * UI metadata (icon, path, children) is now sourced from backend module registry,
 * ensuring single source of truth for module definitions.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { modulesApi, type ModuleInfo } from '@/api/auth'

export interface NavItem {
    slug: string
    title: string
    icon: string
    path: string
    children?: NavItem[]
}

export const useModuleStore = defineStore('modules', () => {
    const allModules = ref<ModuleInfo[]>([])
    const activeSlugs = ref<Set<string>>(new Set())
    const isLoaded = ref(false)

    const navItems = computed<NavItem[]>(() => {
        return allModules.value
            .filter((m) => activeSlugs.value.has(m.slug))
            .map((m) => {
                const uiMeta = m.ui_meta
                return {
                    slug: m.slug,
                    title: m.display_name,
                    icon: uiMeta?.icon ?? 'Grid',
                    path: uiMeta?.path ?? `/${m.slug}`,
                    children: uiMeta?.children?.map((c) => ({
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
        activeSlugs.value = new Set(tenantActiveSlugs ?? allModules.value.map((m) => m.slug))
        isLoaded.value = true
    }

    function hasModule(slug: string) {
        return activeSlugs.value.has(slug)
    }

    return { allModules, activeSlugs, isLoaded, navItems, loadModules, hasModule }
})
