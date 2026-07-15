<template>
  <aside class="build-history surface" aria-label="构建历史">
    <header>
      <div>
        <span>BUILD HISTORY</span>
        <strong>历史构建</strong>
      </div>
      <b>{{ builds.length }}</b>
    </header>

    <el-skeleton :loading="loading" animated :rows="7">
      <div v-if="builds.length" class="history-list">
        <button
          v-for="build in builds"
          :key="build.id"
          type="button"
          :class="{ active: build.id === selectedId }"
          :aria-pressed="build.id === selectedId"
          @click="$emit('select', build.id)"
        >
          <div class="history-top">
            <strong>{{ build.version }}</strong>
            <StatusBadge :status="build.status" />
          </div>
          <p>{{ build.git_branch }} · {{ shortSha(build.git_commit) }}</p>
          <div class="history-bottom">
            <span>{{ relative(build.created_at) }}</span>
            <span>{{ duration(build) }}</span>
          </div>
        </button>
      </div>
    </el-skeleton>
  </aside>
</template>

<script setup lang="ts">
import StatusBadge from '../common/StatusBadge.vue'
import type { BuildVersion } from '../../types'

defineProps<{
  builds: BuildVersion[]
  selectedId?: number
  loading: boolean
}>()

defineEmits<{ select: [buildId: number] }>()

function shortSha(value?: string) {
  return value?.slice(0, 8) || '未锁定提交'
}

function relative(value: string) {
  const seconds = Math.max(0, Math.round((Date.now() - new Date(value).getTime()) / 1000))
  if (seconds < 60) return '刚刚'
  if (seconds < 3600) return `${Math.floor(seconds / 60)} 分钟前`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} 小时前`
  return `${Math.floor(seconds / 86400)} 天前`
}

function duration(build: BuildVersion) {
  if (!build.finished_at) return ['Pending', 'Running', 'Building'].includes(build.status) ? '进行中' : '—'
  const seconds = Math.max(0, Math.round(
    (new Date(build.finished_at).getTime() - new Date(build.created_at).getTime()) / 1000,
  ))
  if (seconds < 60) return `${seconds}s`
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
}
</script>

<style scoped>
.build-history {
  height: calc(100vh - 92px);
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: none;
}

.build-history :deep(.el-skeleton) {
  min-height: 0;
  display: flex;
  flex: 1;
  flex-direction: column;
}

header,
.history-top,
.history-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

header {
  min-height: 62px;
  padding: 0 16px;
  border-bottom: 1px solid var(--border-soft);
}

header span,
header strong {
  display: block;
}

header span {
  color: var(--primary);
  font-size: 9px;
  font-weight: 800;
  letter-spacing: .12em;
}

header strong {
  margin-top: 4px;
  font-size: 14px;
}

header b {
  color: var(--muted);
  font-size: 12px;
}

.history-list {
  min-height: 0;
  flex: 1;
  overflow: auto;
  padding: 8px;
}

.history-list button {
  width: 100%;
  padding: 12px;
  border: 1px solid transparent;
  border-radius: 11px;
  background: transparent;
  color: var(--text-2);
  text-align: left;
  cursor: pointer;
}

.history-list button + button {
  margin-top: 4px;
}

.history-list button:hover {
  background: var(--surface-soft);
}

.history-list button.active {
  border-color: color-mix(in srgb, var(--primary) 22%, var(--border-soft));
  background: var(--primary-soft);
}

.history-top strong {
  min-width: 0;
  overflow: hidden;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-list p {
  margin: 8px 0;
  overflow: hidden;
  color: var(--muted);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-bottom {
  justify-content: flex-start;
  color: var(--subtle);
  font-size: 10px;
}

@media (max-width: 760px) {
  .build-history {
    height: auto;
  }

  .history-list {
    flex: none;
    max-height: 280px;
  }
}
</style>
