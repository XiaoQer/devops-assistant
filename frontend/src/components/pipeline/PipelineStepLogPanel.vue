<template>
  <section class="step-log-panel">
    <div v-if="showHeader" class="section-title">
      <div><span>{{ eyebrow }}</span><h3>{{ title }}</h3></div>
      <el-button v-if="error" text @click="$emit('retry')">重新加载日志</el-button>
    </div>

    <el-skeleton :loading="loading" animated :rows="4">
      <div v-if="steps.length" class="step-tabs">
        <button
          v-for="step in steps"
          :key="step.id"
          type="button"
          :class="['step-tab', `status-${step.status.toLowerCase()}`, { active: step.id === selectedStepId }]"
          :aria-pressed="step.id === selectedStepId"
          @click="$emit('select-step', step.id)"
        >
          <i>{{ mark(step.status) }}</i>
          <span>
            <strong>{{ step.name }}</strong>
            <small>{{ step.taskName }} · {{ step.status }}</small>
          </span>
        </button>
      </div>

      <div v-if="error" class="log-state error-state">
        <strong>执行日志暂时不可用</strong>
        <p>{{ error }}</p>
        <el-button v-if="!showHeader" text @click="$emit('retry')">重新加载日志</el-button>
      </div>
      <div v-else-if="selectedStep" class="log-panel">
        <header><span>{{ selectedStep.label }}</span><b>{{ selectedStep.status }}</b></header>
        <pre>{{ selectedStep.logs || '该步骤没有返回日志。' }}</pre>
      </div>
      <div v-else class="log-state">
        <strong>尚无可展示的执行步骤</strong>
        <p>{{ emptyDescription }}</p>
      </div>
    </el-skeleton>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ExecutionStepDetail } from '../../features/build-explorer/state'

const props = withDefaults(defineProps<{
  eyebrow: string
  title: string
  steps: ExecutionStepDetail[]
  selectedStepId?: string
  loading?: boolean
  error?: string
  emptyDescription?: string
  showHeader?: boolean
}>(), {
  loading: false,
  error: '',
  emptyDescription: 'PipelineRun 可能仍在初始化，请稍后刷新。',
  showHeader: true,
})

defineEmits<{
  'select-step': [stepId: string]
  retry: []
}>()

const selectedStep = computed(() => props.steps.find(step => step.id === props.selectedStepId))

function mark(status: string) {
  if (status === 'Succeeded') return '✓'
  if (status === 'Failed') return '✕'
  return '↻'
}
</script>

<style scoped>
.step-log-panel { padding: 18px 20px 20px; }
.section-title,.log-panel>header{display:flex;align-items:flex-start;justify-content:space-between;gap:18px}.section-title span{color:var(--primary);font-size:9px;font-weight:800;letter-spacing:.12em}.section-title h3{margin:4px 0 0;font-size:16px}.step-tabs{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:8px;margin-top:14px}.step-tab{min-width:0;display:flex;align-items:center;gap:10px;padding:11px 12px;border:1px solid var(--border-soft);border-radius:10px;background:var(--surface-soft);color:var(--text-2);text-align:left;cursor:pointer}.step-tab.active{border-color:var(--primary);box-shadow:0 0 0 2px var(--primary-soft)}.step-tab i{width:22px;height:22px;display:grid;place-items:center;flex:0 0 auto;border-radius:50%;background:var(--surface);color:var(--success);font-size:11px;font-style:normal}.step-tab.status-failed i{color:var(--danger)}.step-tab span,.step-tab strong,.step-tab small{min-width:0;display:block}.step-tab strong{overflow:hidden;font-size:12px;text-overflow:ellipsis;white-space:nowrap}.step-tab small{margin-top:3px;overflow:hidden;color:var(--muted);font-size:10px;text-overflow:ellipsis;white-space:nowrap}.log-panel,.log-state{margin-top:12px;border:1px solid var(--border-soft);border-radius:11px;overflow:hidden}.log-panel>header{align-items:center;min-height:44px;padding:0 14px;background:var(--surface-soft);color:var(--muted);font-size:11px}.log-panel pre{min-height:230px;max-height:460px;margin:0;padding:14px;overflow:auto;background:#111827;color:#d7e0ef;font:11px/1.65 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap;word-break:break-word}.log-state{min-height:130px;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:20px;color:var(--muted);text-align:center}.log-state p{margin:6px 0 0;font-size:12px}.error-state strong{color:var(--danger)}
</style>
