<template>
  <section class="surface history-card">
    <div class="surface-header">
      <div>
        <h3>Release history</h3>
        <p>构建、发布与回滚的完整审计记录</p>
      </div>
      <div class="tools">
        <el-input v-model="query" placeholder="搜索版本或 Commit" clearable />
        <el-select v-model="status" style="width: 130px">
          <el-option label="全部状态" value="" />
          <el-option v-for="s in statuses" :key="s" :label="s" :value="s" />
        </el-select>
      </div>
    </div>

    <div v-if="paged.length" class="history-list">
      <article v-for="row in paged" :key="row.id" class="history-item">
        <div class="history-line"></div>
        <div class="history-main">
          <div class="history-head">
            <div>
              <h4>{{ row.image_tag }}</h4>
              <p class="mono">{{ row.image }}</p>
            </div>
            <StatusBadge :status="row.deploy_status" />
          </div>
          <div class="history-meta">
            <span class="soft-pill">{{ row.environment.toUpperCase() }}</span>
            <span class="soft-pill">{{ row.deploy_user }}</span>
            <span class="soft-pill">{{ row.git_commit?.slice(0, 8) || 'no commit' }}</span>
            <span class="soft-pill">{{ format(row.created_at) }}</span>
          </div>
          <div class="history-actions">
            <el-button v-if="row.pipeline_run_name" link @click="$emit('logs', row)">日志</el-button>
            <el-button link :disabled="row.deploy_status !== 'Succeeded'" :loading="rollbackId === row.id" @click="$emit('rollback', row)">回滚</el-button>
          </div>
        </div>
      </article>
    </div>
    <EmptyState v-else title="没有匹配的发布记录" description="调整筛选条件，或从应用详情发起一次新发布。" />

    <footer v-if="filtered.length > pageSize" class="pager">
      <el-pagination v-model:current-page="page" :page-size="pageSize" layout="prev, pager, next" :total="filtered.length" />
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Release } from '../../types'
import StatusBadge from '../common/StatusBadge.vue'
import EmptyState from '../common/EmptyState.vue'

const props = withDefaults(defineProps<{ releases: Release[]; rollbackId?: number }>(), { rollbackId: 0 })
defineEmits<{ rollback: [Release]; logs: [Release] }>()

const query = ref('')
const status = ref('')
const page = ref(1)
const pageSize = 8
const statuses = ['Succeeded', 'Failed', 'Running', 'Pending']

const filtered = computed(() => props.releases.filter(release => (
  (!status.value || release.deploy_status === status.value) &&
  (!query.value || `${release.image_tag}${release.git_commit}`.toLowerCase().includes(query.value.toLowerCase()))
)))

const paged = computed(() => filtered.value.slice((page.value - 1) * pageSize, page.value * pageSize))

function format(value: string) {
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}
</script>

<style scoped>
.history-card {
  overflow: hidden;
  box-shadow: none;
}

.tools {
  display: flex;
  gap: 10px;
}

.tools :deep(.el-input) {
  width: 220px;
}

.history-list {
  padding: 12px 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-item {
  display: grid;
  grid-template-columns: 24px 1fr;
  gap: 16px;
}

.history-line {
  width: 2px;
  border-radius: 999px;
  background: linear-gradient(180deg, var(--primary), transparent);
}

.history-main {
  padding: 18px;
  border-radius: 14px;
  border: 1px solid var(--border-soft);
  background: var(--surface-soft);
}

.history-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.history-head h4 {
  margin: 0 0 8px;
  font-size: 18px;
  letter-spacing: -0.03em;
}

.history-head p {
  margin: 0;
  color: var(--muted);
  font-size: 12px;
  word-break: break-all;
}

.history-meta,
.history-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.history-meta {
  margin: 16px 0 10px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  padding: 0 24px 24px;
}

@media (max-width: 900px) {
  .tools,
  .history-head {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
