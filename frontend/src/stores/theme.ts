/**
 * Theme Store (Pinia) - White-label customization engine
 * Tenants can override brand colors and logo at runtime.
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

interface RGB {
    r: number
    g: number
    b: number
}

function clamp(value: number) {
    return Math.max(0, Math.min(255, Math.round(value)))
}

function parseColor(input: string): RGB | null {
    const value = input.trim()
    const shortHex = /^#([\da-f]{3})$/i.exec(value)
    if (shortHex) {
        const [r, g, b] = shortHex[1].split('')
        return {
            r: parseInt(`${r}${r}`, 16),
            g: parseInt(`${g}${g}`, 16),
            b: parseInt(`${b}${b}`, 16),
        }
    }

    const longHex = /^#([\da-f]{6})$/i.exec(value)
    if (longHex) {
        return {
            r: parseInt(longHex[1].slice(0, 2), 16),
            g: parseInt(longHex[1].slice(2, 4), 16),
            b: parseInt(longHex[1].slice(4, 6), 16),
        }
    }

    const rgb = /^rgba?\(([^)]+)\)$/i.exec(value)
    if (rgb) {
        const [r, g, b] = rgb[1]
            .split(',')
            .slice(0, 3)
            .map((part) => Number.parseFloat(part.trim()))
        if ([r, g, b].every((channel) => Number.isFinite(channel))) {
            return { r, g, b } as RGB
        }
    }

    return null
}

function mixColors(base: RGB, target: RGB, weight: number): RGB {
    return {
        r: clamp(base.r + (target.r - base.r) * weight),
        g: clamp(base.g + (target.g - base.g) * weight),
        b: clamp(base.b + (target.b - base.b) * weight),
    }
}

function toCssRgb(color: RGB): string {
    return `rgb(${color.r}, ${color.g}, ${color.b})`
}

function buildThemeColors(primaryColor: string | null | undefined) {
    if (!primaryColor) {
        return { ...DEFAULT_THEME }
    }

    const parsed = parseColor(primaryColor)
    if (!parsed) {
        return { ...DEFAULT_THEME }
    }

    return {
        brandName: DEFAULT_THEME.brandName,
        logoUrl: DEFAULT_THEME.logoUrl,
        primaryColor,
        primaryLight: toCssRgb(mixColors(parsed, { r: 255, g: 255, b: 255 }, 0.3)),
        primaryDark: toCssRgb(mixColors(parsed, { r: 0, g: 0, b: 0 }, 0.2)),
    }
}

export const useThemeStore = defineStore('theme', () => {
    const theme = ref<TenantTheme>(
        JSON.parse(localStorage.getItem(THEME_KEY) ?? 'null') ?? { ...DEFAULT_THEME },
    )

    function applyTheme(nextTheme: TenantTheme) {
        theme.value = nextTheme
        const root = document.documentElement
        root.style.setProperty('--brand-primary', nextTheme.primaryColor)
        root.style.setProperty('--brand-primary-light', nextTheme.primaryLight)
        root.style.setProperty('--brand-primary-dark', nextTheme.primaryDark)
        root.style.setProperty('--el-color-primary', nextTheme.primaryColor)
        localStorage.setItem(THEME_KEY, JSON.stringify(nextTheme))
    }

    function applyFromTenantData(data: {
        brand_name?: string | null
        logo_url?: string | null
        primary_color?: string | null
    }) {
        const palette = buildThemeColors(data.primary_color)
        applyTheme({
            brandName: data.brand_name ?? DEFAULT_THEME.brandName,
            logoUrl: data.logo_url ?? null,
            primaryColor: palette.primaryColor,
            primaryLight: palette.primaryLight,
            primaryDark: palette.primaryDark,
        })
    }

    function resetTheme() {
        applyTheme({ ...DEFAULT_THEME })
    }

    applyTheme(theme.value)

    return { theme, applyTheme, applyFromTenantData, resetTheme }
})
