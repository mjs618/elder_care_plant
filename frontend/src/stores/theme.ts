/**
 * Theme Store (Pinia) — White-label customization engine
 * Tenants can override brand colors and logo at runtime.
 * Applies changes by patching CSS variables on document.documentElement.
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface TenantTheme {
    brandName: string
    logoUrl: string | null
    primaryColor: string
    primaryLight: string
    primaryDark: string
}

const DEFAULT_THEME: TenantTheme = {
    brandName: '老年照顾平台',
    logoUrl: null,
    primaryColor: '#3B82F6',
    primaryLight: '#60A5FA',
    primaryDark: '#1D4ED8',
}

const THEME_KEY = 'ec_tenant_theme'

export const useThemeStore = defineStore('theme', () => {
    const theme = ref<TenantTheme>(
        JSON.parse(localStorage.getItem(THEME_KEY) ?? 'null') ?? { ...DEFAULT_THEME },
    )

    function applyTheme(t: TenantTheme) {
        theme.value = t
        const root = document.documentElement
        root.style.setProperty('--brand-primary', t.primaryColor)
        root.style.setProperty('--brand-primary-light', t.primaryLight)
        root.style.setProperty('--brand-primary-dark', t.primaryDark)
        root.style.setProperty('--el-color-primary', t.primaryColor)
        localStorage.setItem(THEME_KEY, JSON.stringify(t))
    }

    function applyFromTenantData(data: {
        brand_name?: string | null
        logo_url?: string | null
        primary_color?: string | null
    }) {
        applyTheme({
            brandName: data.brand_name ?? DEFAULT_THEME.brandName,
            logoUrl: data.logo_url ?? null,
            primaryColor: data.primary_color ?? DEFAULT_THEME.primaryColor,
            primaryLight: data.primary_color
                ? `${data.primary_color}CC` // 80% opacity as light variant fallback
                : DEFAULT_THEME.primaryLight,
            primaryDark: DEFAULT_THEME.primaryDark,
        })
    }

    function resetTheme() {
        applyTheme({ ...DEFAULT_THEME })
    }

    // Apply persisted theme on store init
    applyTheme(theme.value)

    return { theme, applyTheme, applyFromTenantData, resetTheme }
})
