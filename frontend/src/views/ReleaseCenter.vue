<template>
  <div class="page-content page-stack">
    <PageHeader eyebrow="Release center" title="Releases" description="跨应用统一追踪发布、回滚与环境变更，帮助你判断下一步该做什么。">
      <el-button @click="load" :loading="loading">刷新</el-button>
    </PageHeader>

    <div class="metrics">
      <MetricCard title="All releases" :value="total" icon="↗" helper="统一交付轨迹" />
      <MetricCard title="Succeeded" :value="successCount" icon="✓" tone="green" helper="已成功完成" />
      <MetricCard title="Failed" :value="failedCount" icon="!" tone="red" helper="建议回看日志" />
      <MetricCard title="Production" :value="prodCount" icon="◆" tone="blue" helper="生产环境变更" />
    </div>

    <section class="surface toolbar-card">
      <div class="toolbar">
        <el-select v-model="environment" style="width: 150px">
          <el-option label="全部环境" value="" />
          <el-option v-for="e in ['dev', 'test', 'staging', 'prod']" :key="e" :label="e.toUpperCase()" :value="e" />
        </el-select>
        <el-select v-model="status" style="width: 150px">
          <el-option label="全部状态" value="" />
          <el-option v-for="s in ['Succeeded', 'Failed', 'Running', 'Pending']" :key="s" :label="s" :value="s" />
        </el-select>
        <span>{{ total }} release records</span>
      </div>
    </section>

    <section class="release-layout">
      <div class="surface release-list-card">
        <div class="surface-header">
          <div>
            <h3>Release activity</h3>
            <p>按时间顺序展示软件变更，让回滚、定位与审计都更直接。</p>
          </div>
        </div>
        <el-skeleton :loading="loading" animated :rows="7">
          <div v-if="items.length" class="release-list">
            <article v-for="row in items" :key="row.id" class="release-item">
              <div class="release-line"></div>
              <div class="release-main">
                <div class="release-head">
                  <div>
                    <h4>{{ row.image_tag }}</h4>
                    <p>{{ row.image }}</p>
                  </div>
                  <StatusBadge :status="row.deploy_status" />
                </div>
                <div class="release-meta">
                  <span class="soft-pill">{{ row.environment.toUpperCase() }}</span>
                  <span class="soft-pill">{{ row.release_type }}</span>
                  <span class="soft-pill">{{ row.deploy_user }}</span>
                </div>
                <div class="release-foot">
                  <span>{{ row.git_commit?.slice(0, 8) || row.git_branch }}</span>
                  <time>{{ format(row.created_at) }}</time>
                  <el-button v-if="row.pipeline_run_name" link @click="$router.push(`/pipelines/${row.pipeline_run_name}`)">查看日志</el-button>
                </div>
              </div>
            </article>
          </div>
          <EmptyState v-else title="没有发布记录" description="发布应用后，记录会以活动流形式显示在这里。" />
        </el-skeleton>
      </div>

      <aside class="surface summary-rail">
        <div class="surface-header">
          <div>
            <h3>Release guidance</h3>
            <p>帮助团队更快理解当前变更节奏。</p>
          </div>
        </div>
        <div class="rail-content">
          <article>
            <span class="soft-pill">Signal</span>
            <h4>{{ failedCount ? `${failedCount} 次发布失败需要复盘` : '发布状态稳定' }}</h4>
            <p>{{ failedCount ? '建议优先查看失败发布关联的 PipelineRun，并决定是否需要回滚。' : '最近没有明显的交付风险，可以推进下一个迭代。' }}</p>
          </article>
          <article>
            <span class="soft-pill">Focus</span>
            <h4>{{ prodCount ? `${prodCount} 条生产环境记录` : '暂无生产变更' }}</h4>
            <p>生产变更应该总是比测试环境更容易被看见，并且快速关联到审批与执行日志。</p>
          </article>
        </div>
      </aside>
    </section>

    <footer class="pager">
      <el-pagination v-model:current-page="page" :page-size="pageSize" layout="prev, pager, next" :total="total" />
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { releaseApi } from '../api/release'
import type { Release } from '../types'
import PageHeader from '../components/common/PageHeader.vue'
import MetricCard from '../components/common/MetricCard.vue'
import StatusBadge from '../components/common/StatusBadge.vue'
import EmptyState from '../components/common/EmptyState.vue'

const items = ref<Release[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const environment = ref('')
const status = ref('')
const loading = ref(false)

const successCount = computed(() => items.value.filter(item => item.deploy_status === 'Succeeded').length)
const failedCount = computed(() => items.value.filter(item => item.deploy_status === 'Failed').length)
const prodCount = computed(() => items.value.filter(item => item.environment === 'prod').length)

async function load() {
  loading.value = true
  try {
    const data = await releaseApi.list({ page: page.value, pageSize, environment: environment.value, status: status.value })
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function format(value: string) {
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

watch([page, environment, status], () => {
  load()
})

watch([environment, status], () => {
  page.value = 1
})

onMounted(load)
</script>

<style scoped>
.metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.toolbar-card {
  padding: 16px 20px;
  box-shadow: none;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar span {
  color: var(--muted);
  font-size: 13px;
}

.release-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(280px, 0.8fr);
  gap: 16px;
}

.release-list-card,
.summary-rail {
  box-shadow: none;
}

.release-list {
  padding: 8px 24px 24px;
}

.release-item {
  display: grid;
  grid-template-columns: 24px 1fr;
  gap: 16px;
  padding: 18px 0;
}

.release-line {
  width: 2px;
  border-radius: 999px;
  background: linear-gradient(180deg, var(--primary), transparent);
}

.release-main {
  padding-bottom: 18px;
  border-bottom: 1px solid var(--border-soft);
}

.release-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.release-head h4 {
  margin: 0;
  font-size: 18px;
  letter-spacing: -0.03em;
}

.release-head p {
  margin: 8px 0 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.6;
  word-break: break-all;
}

.release-meta,
.release-foot {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.release-meta {
  margin: 14px 0;
}

.release-foot {
  color: var(--muted);
  font-size: 13px;
}

.rail-content {
  padding: 12px 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rail-content article {
  padding: 18px;
  border-radius: 14px;
  background: var(--surface-soft);
  border: 1px solid var(--border-soft);
}

.rail-content h4 {
  margin: 14px 0 8px;
  font-size: 17px;
}

.rail-content p {
  margin: 0;
  color: var(--muted);
  line-height: 1.7;
}

.pager {
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 1100px) {
  .metrics,
  .release-layout {
    grid-template-columns: 1fr;
  }
}
</style>
