<template>
  <span class="status-badge" :class="tone"><i />{{ label || status }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ status?: string; label?: string }>()

const tone = computed(() => {
  const status = (props.status || 'Unknown').toLowerCase()
  if (['healthy', 'succeeded', 'approved', 'active', 'configured'].includes(status)) return 'success'
  if (['failed', 'rejected'].includes(status)) return 'danger'
  if (['degraded', 'pending'].includes(status)) return 'warning'
  if (['running', 'progressing'].includes(status)) return 'info'
  return 'neutral'
})
</script>

<style scoped>
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid transparent;
  font-size: 12px;
  line-height: 1;
  font-weight: 700;
  color: var(--muted);
  background: var(--surface-soft);
}

.status-badge i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
}

.status-badge.success {
  color: var(--success);
  background: rgba(22, 163, 74, 0.1);
  border-color: rgba(22, 163, 74, 0.1);
}

.status-badge.danger {
  color: var(--danger);
  background: rgba(220, 38, 38, 0.1);
  border-color: rgba(220, 38, 38, 0.1);
}

.status-badge.warning {
  color: var(--warning);
  background: rgba(217, 119, 6, 0.1);
  border-color: rgba(217, 119, 6, 0.1);
}

.status-badge.info {
  color: var(--info);
  background: rgba(37, 99, 235, 0.1);
  border-color: rgba(37, 99, 235, 0.1);
}
</style>
