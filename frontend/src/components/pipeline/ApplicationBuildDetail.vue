<template>
  <section ref="detailElement" class="build-detail surface">
    <el-skeleton :loading="loading" animated :rows="10">
      <template v-if="build">
        <header class="detail-head">
          <div>
            <span>SELECTED BUILD</span>
            <h2>{{ build.version }}</h2>
            <p>{{ build.commit_message || '没有 Commit message' }}</p>
          </div>
          <StatusBadge :status="build.status" />
        </header>

        <dl class="build-facts">
          <div><dt>镜像版本</dt><dd>{{ build.image }}</dd></div>
          <div><dt>代码版本</dt><dd>{{ build.git_branch }} · {{ build.git_commit || '未锁定提交' }}</dd></div>
          <div><dt>PipelineRun</dt><dd>{{ build.pipeline_run_name || '尚未创建' }}</dd></div>
          <div><dt>触发人</dt><dd>{{ build.created_by }}</dd></div>
          <div><dt>开始时间</dt><dd>{{ format(build.created_at) }}</dd></div>
          <div><dt>结束时间</dt><dd>{{ format(build.finished_at) }}</dd></div>
        </dl>

        <p v-if="build.error_message" class="build-error">{{ build.error_message }}</p>

        <PipelineStepLogPanel
          eyebrow="BUILD PIPELINE STEPS"
          title="实际构建步骤"
          :steps="steps"
          :selected-step-id="selectedStepId"
          :loading="loading"
          :error="logsError"
          :empty-description="build.pipeline_run_name ? 'PipelineRun 可能仍在初始化，请稍后刷新。' : '此构建没有关联 PipelineRun。'"
          @select-step="$emit('select-step', $event)"
          @retry="$emit('retry-logs')"
        />

        <BuildDeliveryTargets
          :batch="batch"
          :selected-target-id="selectedTargetId"
          :steps="deploySteps"
          :selected-step-id="selectedDeployStepId"
          :loading="deployLoading"
          :error="deployError"
          @select-target="$emit('select-target', $event)"
          @select-step="$emit('select-deploy-step', $event)"
          @retry="$emit('retry-deploy-logs')"
        />
      </template>
    </el-skeleton>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import StatusBadge from '../common/StatusBadge.vue'
import PipelineStepLogPanel from './PipelineStepLogPanel.vue'
import BuildDeliveryTargets from './BuildDeliveryTargets.vue'
import type { BuildVersion, ReleaseBatch } from '../../types'
import type { ExecutionStepDetail } from '../../features/build-explorer/state'

defineProps<{
  build?: BuildVersion
  steps: ExecutionStepDetail[]
  selectedStepId?: string
  loading: boolean
  logsError?: string
  batch?: ReleaseBatch
  selectedTargetId?: number
  deploySteps?: ExecutionStepDetail[]
  selectedDeployStepId?: string
  deployLoading?: boolean
  deployError?: string
}>()

defineEmits<{
  'select-step': [stepId: string]
  'retry-logs': []
  'select-target': [targetId: number]
  'select-deploy-step': [stepId: string]
  'retry-deploy-logs': []
}>()

const detailElement = ref<HTMLElement>()
defineExpose({
  scrollIntoView: () => detailElement.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }),
})

function format(value?: string) {
  return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '—'
}

</script>

<style scoped>
.build-detail {
  min-width: 0;
  overflow: hidden;
  box-shadow: none;
}

.detail-head,
.section-title,
.log-panel > header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.detail-head {
  padding: 18px 20px;
  border-bottom: 1px solid var(--border-soft);
}

.detail-head span,
.section-title span {
  color: var(--primary);
  font-size: 9px;
  font-weight: 800;
  letter-spacing: .12em;
}

.detail-head h2 {
  margin: 5px 0 0;
  font-size: 23px;
}

.detail-head p {
  margin: 7px 0 0;
  color: var(--muted);
  font-size: 12px;
}

.build-facts {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1px;
  margin: 0;
  background: var(--border-soft);
  border-bottom: 1px solid var(--border-soft);
}

.build-facts div {
  min-width: 0;
  padding: 13px 16px;
  background: var(--surface);
}

.build-facts dt {
  color: var(--subtle);
  font-size: 10px;
}

.build-facts dd {
  margin: 5px 0 0;
  overflow: hidden;
  color: var(--text-2);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.build-error {
  margin: 14px 20px 0;
  padding: 10px 12px;
  border-radius: 9px;
  background: color-mix(in srgb, var(--danger) 8%, transparent);
  color: var(--danger);
  font-size: 12px;
}

.steps-section {
  padding: 18px 20px 20px;
}

.section-title h3 {
  margin: 4px 0 0;
  font-size: 16px;
}

.step-tabs {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-top: 14px;
}

.step-tab {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 12px;
  border: 1px solid var(--border-soft);
  border-radius: 10px;
  background: var(--surface-soft);
  color: var(--text-2);
  text-align: left;
  cursor: pointer;
}

.step-tab.active {
  border-color: var(--primary);
  box-shadow: 0 0 0 2px var(--primary-soft);
}

.step-tab i {
  width: 22px;
  height: 22px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 50%;
  background: var(--surface);
  color: var(--success);
  font-size: 11px;
  font-style: normal;
}

.step-tab.status-failed i {
  color: var(--danger);
}

.step-tab span,
.step-tab strong,
.step-tab small {
  min-width: 0;
  display: block;
}

.step-tab strong {
  font-size: 12px;
}

.step-tab small {
  margin-top: 3px;
  color: var(--muted);
  font-size: 10px;
}

.log-panel,
.log-state {
  margin-top: 12px;
  border: 1px solid var(--border-soft);
  border-radius: 11px;
  overflow: hidden;
}

.log-panel > header {
  align-items: center;
  min-height: 44px;
  padding: 0 14px;
  background: var(--surface-soft);
  color: var(--muted);
  font-size: 11px;
}

.log-panel pre {
  min-height: 260px;
  max-height: 460px;
  margin: 0;
  padding: 14px;
  overflow: auto;
  background: #111827;
  color: #d7e0ef;
  font: 11px/1.65 ui-monospace, SFMono-Regular, Menlo, monospace;
  white-space: pre-wrap;
  word-break: break-word;
}

.log-state {
  min-height: 150px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
  color: var(--muted);
  text-align: center;
}

.log-state p {
  margin: 6px 0 0;
  font-size: 12px;
}

.error-state strong {
  color: var(--danger);
}

@media (max-width: 1000px) {
  .build-facts {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 600px) {
  .build-facts,
  .step-tabs {
    grid-template-columns: 1fr;
  }
}
</style>
