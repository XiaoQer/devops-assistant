<template>
  <div class="timeline">
    <button
      v-for="(task, index) in tasks"
      :key="task.name"
      :class="{ active: selected === task.name, failed: task.status === 'Failed' }"
      @click="$emit('select', task)"
    >
      <span class="node"><i>{{ task.status === 'Succeeded' ? '✓' : task.status === 'Failed' ? '×' : index + 1 }}</i></span>
      <div>
        <b>{{ task.task_name || task.name }}</b>
        <StatusBadge :status="task.status" />
      </div>
      <em v-if="index < tasks.length - 1" />
    </button>
  </div>
</template>

<script setup lang="ts">
import StatusBadge from '../common/StatusBadge.vue'

defineProps<{ tasks: any[]; selected?: string }>()
defineEmits<{ select: [any] }>()
</script>

<style scoped>
.timeline {
  display: flex;
  align-items: flex-start;
  padding: 24px;
  overflow: auto;
}

.timeline button {
  min-width: 180px;
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  border: 0;
  background: none;
  color: var(--text-2);
  text-align: left;
  padding: 0;
}

.node {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: rgba(22, 163, 74, 0.10);
  border: 1px solid rgba(22, 163, 74, 0.22);
  z-index: 1;
  flex-shrink: 0;
}

.node i {
  font-style: normal;
  color: var(--success);
  font-size: 13px;
  font-weight: 700;
}

.timeline button.failed .node {
  background: rgba(220, 38, 38, 0.10);
  border-color: rgba(220, 38, 38, 0.22);
}

.timeline button.failed .node i {
  color: var(--danger);
}

.timeline button.active .node {
  box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.12);
  border-color: var(--primary);
}

.timeline b {
  display: block;
  font-size: 14px;
  margin-bottom: 8px;
}

.timeline em {
  position: absolute;
  left: 32px;
  top: 16px;
  width: 44px;
  height: 1px;
  background: var(--border);
}
</style>
