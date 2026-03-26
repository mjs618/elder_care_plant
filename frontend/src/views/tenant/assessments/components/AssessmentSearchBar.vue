<template>
  <div class="assessment-search-bar">
    <el-input
      :model-value="modelValue"
      @update:model-value="$emit('update:modelValue', $event)"
      placeholder="搜索长者姓名、评估人或备注"
      prefix-icon="Search"
      clearable
      @keyup.enter="$emit('search')"
      @clear="$emit('search')"
      style="width: 250px; margin-right: 16px"
    />
    <el-button type="primary" icon="Plus" @click="$emit('add')">新建评估</el-button>
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
.assessment-search-bar {
  display: flex;
  align-items: center;
}
</style>
