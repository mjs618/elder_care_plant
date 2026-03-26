<template>
  <el-select
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    filterable
    placeholder="搜索或切换长者档案..."
    style="width: 280px"
  >
    <el-option
      v-for="p in patients"
      :key="p.id"
      :label="`${p.full_name} (${p.room_number || '待分配'})`"
      :value="p.id"
    />
  </el-select>
</template>

<script setup lang="ts">
import type { Patient } from '@/api/patients'

defineProps<{
  modelValue: string
  patients: Patient[]
}>()

defineEmits<{
  'update:modelValue': [value: string]
}>()
</script>
