<template>
  <el-card class="profile-card" shadow="never">
    <div class="avatar-box">
      <el-avatar :size="80" style="background: var(--brand-primary); font-size: 32px">
        {{ patient?.full_name?.[0] || '?' }}
      </el-avatar>
      <h3>{{ patient?.full_name || '未知' }}</h3>
      <el-tag :type="patient?.gender === 'M' ? 'primary' : 'danger'" effect="plain">
        {{ patient?.gender === 'M' ? '爷爷' : patient?.gender === 'F' ? '奶奶' : '未知' }}
      </el-tag>
    </div>
    
    <div class="meta-list">
      <div class="meta-item">
        <span class="label">年龄</span>
        <span class="val">{{ patient?.age || '未知' }} 岁</span>
      </div>
      <div class="meta-item">
        <span class="label">房间排床</span>
        <span class="val">{{ patient?.room_number || '-' }} - {{ patient?.bed_number || '-' }}</span>
      </div>
      <div class="meta-item">
        <span class="label">联系方式</span>
        <span class="val">{{ patient?.contact_phone || '无记录' }}</span>
      </div>
      <div class="meta-item">
        <span class="label">紧急联系人</span>
        <span class="val">{{ patient?.emergency_contact || '无记录' }} ({{ patient?.emergency_phone || '-' }})</span>
      </div>
      <div class="meta-item">
        <span class="label">身份证号</span>
        <span class="val">{{ patient?.id_card_num || '无记录' }}</span>
      </div>
      <div class="meta-item">
        <span class="label">入驻日期</span>
        <span class="val">{{ patient?.created_at?.split('T')[0] || '-' }}</span>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import type { Patient } from '@/api/patients'

defineProps<{
  patient: Patient | null
}>()
</script>

<style scoped>
.profile-card { height: 100%; text-align: center; }
.avatar-box { margin-bottom: 24px; }
.avatar-box h3 { margin: 12px 0 6px; font-size: 18px; font-weight: 600; }

.meta-list { text-align: left; }
.meta-item {
  display: flex;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px dashed var(--border-subtle);
}
.meta-item:last-child { border-bottom: none; }
.meta-item .label { color: var(--text-secondary); font-size: 14px; }
.meta-item .val { font-weight: 500; font-size: 14px; color: var(--text-primary); max-width: 60%; text-align: right; }
</style>
