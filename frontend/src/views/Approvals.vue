<template>
  <div class="page-content page-stack">
    <PageHeader eyebrow="Governance" title="Approvals" description="把 Production 变更审批收敛成清晰的决策队列，优先处理真正需要你判断的事项。">
      <el-button :loading="loading" @click="load">刷新</el-button>
    </PageHeader>

    <div class="metrics">
      <MetricCard title="Pending" :value="pendingCount" icon="◷" tone="blue" helper="等待你的决定" />
      <MetricCard title="Approved" :value="approvedCount" icon="✓" tone="green" helper="已自动继续执行" />
      <MetricCard title="Rejected" :value="rejectedCount" icon="×" tone="red" helper="已阻止发布" />
      <MetricCard title="All records" :value="total" icon="▤" helper="完整审计轨迹" />
    </div>

    <section class="surface toolbar-card">
      <div class="toolbar">
        <el-select v-model="status" style="width: 150px">
          <el-option label="全部状态" value="" />
          <el-option v-for="s in statuses" :key="s" :label="s" :value="s" />
        </el-select>
        <el-select v-model="environment" style="width: 150px">
          <el-option label="全部环境" value="" />
          <el-option label="Production" value="prod" />
          <el-option label="Staging" value="staging" />
        </el-select>
        <span>{{ total }} approval records</span>
      </div>
    </section>

    <section class="approvals-layout">
      <div class="surface approvals-list-card">
        <div class="surface-header">
          <div>
            <h3>Approval queue</h3>
            <p>审批页只回答一个问题：现在有哪些发布申请需要决定？</p>
          </div>
        </div>
        <el-skeleton :loading="loading" animated :rows="7">
          <div v-if="items.length" class="approval-list">
            <article v-for="row in items" :key="row.id" class="approval-card">
              <div class="approval-head">
                <div>
                  <span class="soft-pill">{{ row.environment.toUpperCase() }}</span>
                  <h4>{{ row.application_name || `Application #${row.application_id}` }}</h4>
                  <p>{{ row.applicant }} 提交 · {{ row.namespace }}</p>
                </div>
                <StatusBadge :status="statusTone(row.status)" :label="row.status" />
              </div>
              <div class="approval-body">
                <div>
                  <label>Image</label>
                  <b>{{ row.image }}</b>
                </div>
                <div>
                  <label>Commit / Branch</label>
                  <b>{{ row.git_commit?.slice(0, 8) || row.git_branch || '—' }}</b>
                </div>
                <div>
                  <label>Requested at</label>
                  <b>{{ format(row.created_at) }}</b>
                </div>
              </div>
              <div class="approval-actions">
                <template v-if="row.status === 'Pending'">
                  <el-button type="primary" :loading="actingId === row.id" @click="approve(row)">批准并继续</el-button>
                  <el-button :loading="actingId === row.id" @click="reject(row)">拒绝</el-button>
                </template>
                <el-button v-if="row.pipeline_run_name" link @click="$router.push(`/pipelines/${row.pipeline_run_name}`)">查看 Pipeline</el-button>
                <span v-else class="processed">{{ row.status === 'Pending' ? '等待操作' : '已处理' }}</span>
              </div>
            </article>
          </div>
          <EmptyState v-else title="没有审批记录" description="当用户向需要审批的环境发布时，这里会成为你的决策队列。" icon="✓" />
        </el-skeleton>
      </div>

      <aside class="surface rail-card">
        <div class="surface-header">
          <div>
            <h3>Decision guidance</h3>
            <p>降低审批者的认知负担，让判断更有信心。</p>
          </div>
        </div>
        <div class="rail-content">
          <article>
            <span class="soft-pill">Attention</span>
            <h4>{{ pendingCount ? `${pendingCount} 个待审批请求` : '当前没有待审批请求' }}</h4>
            <p>{{ pendingCount ? '建议先处理 Production 发布，避免交付链路长时间阻塞。' : '说明当前交付流转顺畅。' }}</p>
          </article>
          <article>
            <span class="soft-pill">Policy</span>
            <h4>默认隐藏高级治理细节</h4>
            <p>审批页面先展示关键上下文：应用、环境、镜像与申请时间，其他复杂信息放到执行详情中查看。</p>
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { approvalApi } from '../api/approval'
import type { Approval } from '../types'
import PageHeader from '../components/common/PageHeader.vue'
import MetricCard from '../components/common/MetricCard.vue'
import StatusBadge from '../components/common/StatusBadge.vue'
import EmptyState from '../components/common/EmptyState.vue'

const items = ref<Approval[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const status = ref('')
const environment = ref('')
const loading = ref(false)
const actingId = ref(0)
const statuses = ['Pending', 'Approved', 'Rejected']

const pendingCount = computed(() => items.value.filter(item => item.status === 'Pending').length)
const approvedCount = computed(() => items.value.filter(item => item.status === 'Approved').length)
const rejectedCount = computed(() => items.value.filter(item => item.status === 'Rejected').length)

async function load() {
  loading.value = true
  try {
    const data = await approvalApi.list({ page: page.value, pageSize, status: status.value || undefined, environment: environment.value || undefined })
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function approve(item: Approval) {
  const { value } = await ElMessageBox.prompt('可填写审批意见', '通过 Production 发布', { inputPlaceholder: '同意发布' })
  actingId.value = item.id
  try {
    await approvalApi.approve(item.id, value)
    ElMessage.success('审批通过，PipelineRun 已启动')
    load()
  } finally {
    actingId.value = 0
  }
}

async function reject(item: Approval) {
  const { value } = await ElMessageBox.prompt('请填写拒绝原因', '拒绝发布', {
    inputValidator: input => !!input || '拒绝原因不能为空',
    type: 'warning',
  })
  actingId.value = item.id
  try {
    await approvalApi.reject(item.id, value)
    ElMessage.success('审批已拒绝')
    load()
  } finally {
    actingId.value = 0
  }
}

function statusTone(value: string) {
  return value === 'Approved' ? 'Succeeded' : value === 'Rejected' ? 'Failed' : 'Pending'
}

function format(value: string) {
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

watch([page, status, environment], load)
watch([status, environment], () => {
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

.approvals-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(280px, 0.8fr);
  gap: 16px;
}

.approvals-list-card,
.rail-card {
  box-shadow: none;
}

.approval-list {
  padding: 12px 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.approval-card {
  padding: 20px;
  border-radius: 16px;
  border: 1px solid var(--border-soft);
  background: var(--surface-soft);
}

.approval-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.approval-head h4 {
  margin: 12px 0 6px;
  font-size: 20px;
  letter-spacing: -0.03em;
}

.approval-head p {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
}

.approval-body {
  display: grid;
  gap: 14px;
  margin: 18px 0;
}

.approval-body label,
.approval-body b {
  display: block;
}

.approval-body label {
  color: var(--muted);
  font-size: 12px;
  margin-bottom: 6px;
}

.approval-body b {
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
}

.approval-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.processed {
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
  .approvals-layout {
    grid-template-columns: 1fr;
  }
}
</style>
