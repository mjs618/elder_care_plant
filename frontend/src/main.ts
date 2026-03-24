/**
 * Elder Care Platform — Application Entry Point
 * Wires together: Vue app, Pinia, Vue Router, Element Plus,
 * ECharts, and the Axios auth interceptors.
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'

import App from './App.vue'
import router from './router'
import '@/assets/styles/index.css'
import { setupRequestInterceptors } from '@/utils/request'

// ── Bootstrap ─────────────────────────────────────────────────────────────────
const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(ElementPlus)

// Register all Element Plus icons globally
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, component)
}

// Wire Axios token injection AFTER pinia is installed
// We import the store here (post-pinia) so it's safe to use
import('@/stores/user').then(({ useUserStore }) => {
    const userStore = useUserStore()
    setupRequestInterceptors(
        () => userStore.getToken(),
        () => {
            userStore.logout()
            router.push('/login')
        },
    )
})

app.mount('#app')
