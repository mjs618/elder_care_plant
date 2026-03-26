<template>
  <el-table :data="patients" v-loading="loading" stripe>
    <el-table-column prop="full_name" label="姓名" min-width="120" />
    <el-table-column label="性别" width="80">
      <template #default="{ row }">
        <el-tag :type="row.gender === 'M' ? 'primary' : row.gender === 'F' ? 'danger' : 'info'" size="small">
          {{ row.gender === 'M' ? '男' : row.gender === 'F' ? '女' : '其他' }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column prop="age" label="年龄" width="80" />
    <el-table-column prop="id_card_num" label="身份证号" min-width="180" />
    <el-table-column prop="room_number" label="房间号" width="120" />
    <el-table-column prop="bed_number" label="床位" width="100" />
    <el-table-column prop="emergency_contact" label="紧急联系人" min-width="120" />
    <el-table-column prop="emergency_phone" label="紧急电话" min-width="140" />
    
    <el-table-column label="操作" width="220" fixed="right">
      <template #default="{ row }">
        <el-button type="primary" link icon="EditPen" @click="$emit('edit', row)">编辑</el-button>
        <el-button type="primary" link icon="View" @click="$emit('view', row.id)">档案</el-button>
        <el-popconfirm title="确定要删除该患者吗？此操作不可逆。" @confirm="$emit('delete', row.id)" confirm-button-type="danger">
          <template #reference>
            <el-button type="danger" link icon="Delete">删除</el-button>
          </template>
        </el-popconfirm>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup lang="ts">
import type { Patient } from '@/api/patients'

defineProps<{
  patients: Patient[]
  loading: boolean
}>()

defineEmits<{
  'edit': [patient: Patient]
  'view': [id: string]
  'delete': [id: string]
}>()
</script>
