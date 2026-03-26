<template>
  <div class="patient-search-bar">
    <el-input
      :model-value="modelValue"
      @update:model-value="$emit('update:modelValue', $event)"
      placeholder="搜索姓名、身份证或房间号"
      prefix-icon="Search"
      clearable
      @keyup.enter="$emit('search')"
      @clear="$emit('search')"
      style="width: 260px; margin-right: 16px"
    />
    <el-button type="primary" icon="Plus" @click="$emit('add')">新增患者</el-button>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: string
}>()

defineEmits<{
  'update:modelValue': [value: string]
  'search': []
  'add': []
}>()
</script>

<style scoped>
.patient-search-bar {
  display: flex;
  align-items: center;
}
</style>
