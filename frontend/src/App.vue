<template>
  <router-view />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useThemeStore } from '@/stores/theme'

// Re-apply persisted theme on app load
const themeStore = useThemeStore()
onMounted(() => themeStore.applyTheme(themeStore.theme))
</script>
