import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
    plugins: [
        vue(),
        AutoImport({
            imports: ['vue', 'vue-router', 'pinia'],
            resolvers: [ElementPlusResolver()],
            dts: 'src/auto-imports.d.ts',
        }),
        Components({
            resolvers: [ElementPlusResolver()],
            dts: 'src/components.d.ts',
        }),
    ],
    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./src', import.meta.url)),
        },
    },
    server: {
        port: 5173,
        proxy: {
            '/api': {
                target: 'http://localhost:8000',
                changeOrigin: true,
            },
            '/health': {
                target: 'http://localhost:8000',
                changeOrigin: true,
            },
        },
    },
    build: {
        target: 'es2022',
        minify: 'terser',
        terserOptions: {
            compress: {
                drop_console: true,
                drop_debugger: true,
            },
        },
        rollupOptions: {
            output: {
                manualChunks(id) {
                    if (!id.includes('node_modules')) {
                        return
                    }

                    const normalizedId = id.replace(/\\/g, '/')

                    if (
                        normalizedId.includes('/node_modules/vue/') ||
                        normalizedId.includes('/node_modules/vue-router/') ||
                        normalizedId.includes('/node_modules/pinia/')
                    ) {
                        return 'vue-vendor'
                    }

                    if (
                        normalizedId.includes('/node_modules/axios/') ||
                        normalizedId.includes('/node_modules/dayjs/') ||
                        normalizedId.includes('/node_modules/nprogress/')
                    ) {
                        return 'utils'
                    }
                },
            },
        },
        chunkSizeWarningLimit: 500,
        sourcemap: false,
        reportCompressedSize: true,
    },
    optimizeDeps: {
        include: ['vue', 'vue-router', 'pinia', 'element-plus', 'axios'],
    },
})
