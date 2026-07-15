<template>
  <section class="delivery-section">
    <div class="delivery-title">
      <div><span>ENVIRONMENT DELIVERY</span><h3>环境发布</h3></div>
      <small v-if="batch">{{ batch.targets.length }} 个环境</small>
    </div>

    <div v-if="batch?.targets.length" class="target-grid">
      <button
        v-for="target in batch.targets"
        :key="target.id"
        type="button"
        :class="['target-card', { active: target.id === selectedTargetId }]"
        :aria-pressed="target.id === selectedTargetId"
        @click="$emit('select-target', target.id)"
      >
        <div><strong>{{ target.display_name || target.environment || `Environment #${target.environment_id}` }}</strong><StatusBadge :status="target.status" /></div>
        <p>{{ targetExecutionState(target).description }}</p>
        <small>{{ target.pipeline_run_name || '尚未创建 PipelineRun' }}</small>
      </button>
    </div>
    <div v-else class="delivery-empty">此构建尚未发布到任何环境。</div>

    <div v-if="selectedTarget" class="target-detail">
      <div v-if="!targetExecutionState(selectedTarget).canLoadLogs" class="target-waiting">
        <strong>{{ targetExecutionState(selectedTarget).description }}</strong>
        <p>当前环境还没有可读取的 Deploy-only PipelineRun。</p>
      </div>
      <PipelineStepLogPanel
        v-else
        eyebrow="DEPLOY PIPELINE STEPS"
        :title="`${selectedTarget.display_name || selectedTarget.environment || '环境'}部署步骤`"
        :steps="steps"
        :selected-step-id="selectedStepId"
        :loading="loading"
        :error="error"
        empty-description="Deploy-only PipelineRun 可能仍在初始化，请稍后刷新。"
        @select-step="$emit('select-step', $event)"
        @retry="$emit('retry')"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import StatusBadge from '../common/StatusBadge.vue'
import PipelineStepLogPanel from './PipelineStepLogPanel.vue'
import { targetExecutionState, type ExecutionStepDetail } from '../../features/build-explorer/state'
import type { ReleaseBatch } from '../../types'

const props = withDefaults(defineProps<{
  batch?: ReleaseBatch
  selectedTargetId?: number
  steps?: ExecutionStepDetail[]
  selectedStepId?: string
  loading?: boolean
  error?: string
}>(), { steps: () => [], loading: false, error: '' })

defineEmits<{
  'select-target': [targetId: number]
  'select-step': [stepId: string]
  retry: []
}>()

const selectedTarget = computed(() => props.batch?.targets.find(target => target.id === props.selectedTargetId))
</script>

<style scoped>
.delivery-section{border-top:1px solid var(--border-soft);padding:18px 20px 20px}.delivery-title,.target-card>div{display:flex;align-items:center;justify-content:space-between;gap:12px}.delivery-title span{color:var(--primary);font-size:9px;font-weight:800;letter-spacing:.12em}.delivery-title h3{margin:4px 0 0;font-size:16px}.delivery-title small{color:var(--muted)}.target-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:8px;margin-top:14px}.target-card{min-width:0;padding:12px;border:1px solid var(--border-soft);border-radius:11px;background:var(--surface-soft);color:var(--text-2);text-align:left;cursor:pointer}.target-card.active{border-color:var(--primary);box-shadow:0 0 0 2px var(--primary-soft)}.target-card strong{font-size:13px}.target-card p{margin:9px 0 6px;color:var(--muted);font-size:11px}.target-card small{display:block;overflow:hidden;color:var(--subtle);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:10px;text-overflow:ellipsis;white-space:nowrap}.delivery-empty,.target-waiting{margin-top:14px;padding:24px;border:1px dashed var(--border);border-radius:11px;color:var(--muted);text-align:center}.target-waiting p{margin:6px 0 0;font-size:12px}.target-detail :deep(.step-log-panel){padding:18px 0 0}
</style>
