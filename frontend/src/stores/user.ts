/**
 * User Store (Pinia)
 * Manages: auth tokens, current user profile, permissions
 * Scoped by user type: 'platform' (super admin) or 'tenant' (org user)
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, type UserProfile } from '@/api/auth'

const TOKEN_KEY = 'ec_access_token'
const REFRESH_KEY = 'ec_refresh_token'

export const useUserStore = defineStore('user', () => {
    // ── State ──────────────────────────────────────────────────────────────────
    const accessToken = ref<string | null>(localStorage.getItem(TOKEN_KEY))
    const refreshToken = ref<string | null>(localStorage.getItem(REFRESH_KEY))
    const profile = ref<UserProfile | null>(null)
    const permissions = ref<string[]>([])

    // ── Getters ────────────────────────────────────────────────────────────────
    const isLoggedIn = computed(() => !!accessToken.value)
    const isPlatformAdmin = computed(() => profile.value?.scope === 'platform')
    const tenantId = computed(() => profile.value?.tenant_id)

    const hasPermission = (code: string) => permissions.value.includes(code)

    // ── Actions ────────────────────────────────────────────────────────────────
    async function login(email: string, password: string) {
        const res = await authApi.login({ email, password })
        const tokens = (res as any).data ?? res
        setTokens(tokens.access_token, tokens.refresh_token)
        await fetchProfile()
    }

    async function fetchProfile() {
        const res = await authApi.me()
        const userProfile = (res as any).data ?? res
        profile.value = userProfile
        permissions.value = userProfile.permissions ?? []
    }

    async function refreshAccessToken() {
        if (!refreshToken.value) throw new Error('No refresh token')
        const res = await authApi.refresh(refreshToken.value)
        const tokens = (res as any).data ?? res
        setTokens(tokens.access_token, tokens.refresh_token)
    }

    function setTokens(access: string, refresh: string) {
        accessToken.value = access
        refreshToken.value = refresh
        localStorage.setItem(TOKEN_KEY, access)
        localStorage.setItem(REFRESH_KEY, refresh)
    }

    function logout() {
        accessToken.value = null
        refreshToken.value = null
        profile.value = null
        permissions.value = []
        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem(REFRESH_KEY)
    }

    function getToken() {
        return accessToken.value
    }

    return {
        accessToken, refreshToken, profile, permissions,
        isLoggedIn, isPlatformAdmin, tenantId,
        hasPermission, login, fetchProfile, refreshAccessToken,
        setTokens, logout, getToken,
    }
})
