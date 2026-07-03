<template>
  <div class="page-content page-stack">
    <section class="hero surface glass-card">
      <div class="hero-copy">
        <span class="soft-pill">Aegis AI Command</span>
        <h1>What would you like to do today?</h1>
        <p>把部署、回滚、创建应用、查看故障与运行状态，统一成一个更自然的软件操作界面。</p>
      </div>
      <div class="hero-command">
        <div class="command-input">
          <span>⌘</span>
          <input v-model="command" type="text" placeholder="Deploy payment service to production" @focus="openPalette(command)" @keyup.enter="runCommand" />
          <button class="run-button" @click="runCommand">Run</button>
        </div>
        <div class="prompt-list">
          <button v-for="item in quickPrompts" :key="item" @click="fillPrompt(item)">{{ item }}</button>
        </div>
      </div>
    </section>

    <div class="metrics">
      <MetricCard title="Applications" :value="store.items.length" icon="◇" helper="已接入软件服务" />
      <MetricCard title="Healthy delivery" :value="`${successRate}%`" icon="✓" tone="green" helper="最近执行成功率" />
      <MetricCard title="Active deployments" :value="runningCount" icon="↻" tone="blue" helper="仍在进行中的变更" />
      <MetricCard title="Needs attention" :value="failedCount" icon="!" tone="red" helper="建议优先处理" />
    </div>

    <div class="overview-grid">
      <section class="surface recommendations">
        <div class="surface-header">
          <div>
            <h3>Recommended next actions</h3>
            <p>优先展示现在最值得处理的事情，而不是堆叠监控图表。</p>
          </div>
          <el-button @click="refresh" :loading="loading">刷新</el-button>
        </div>
        <div class="recommendation-list">
          <article v-for="action in suggestedActions" :key="action.title" class="recommendation-item">
            <div>
              <span class="soft-pill">{{ action.tag }}</span>
              <h4>{{ action.title }}</h4>
              <p>{{ action.description }}</p>
            </div>
            <el-button @click="action.run()">{{ action.cta }}</el-button>
          </article>
        </div>
      </section>

      <section class="surface health-card">
        <div class="surface-header">
          <div>
            <h3>Production health</h3>
            <p>仅保留真正影响决策的核心信号。</p>
          </div>
          <StatusBadge :status="failedCount ? 'Degraded' : 'Healthy'" :label="failedCount ? 'Needs review' : 'Stable'" />
        </div>
        <div class="health-score">
          <div class="ring" :style="donutStyle">
            <div>
              <strong>{{ successRate }}%</strong>
              <span>delivery confidence</span>
            </div>
          </div>
          <div class="health-meta">
            <div><label>Healthy</label><b>{{ healthyCount }}</b></div>
            <div><label>Running</label><b>{{ runningCount }}</b></div>
            <div><label>Failed</label><b>{{ failedCount }}</b></div>
            <div><label>Unknown</label><b>{{ unknownCount }}</b></div>
          </div>
        </div>
      </section>
    </div>

    <div class="activity-grid">
      <section class="surface">
        <div class="surface-header">
          <div>
            <h3>Recent activity</h3>
            <p>把发布、流水线与异常统一成一条面向行动的活动流。</p>
          </div>
        </div>
        <div v-if="activityFeed.length" class="activity-list">
          <article v-for="item in activityFeed" :key="item.id" class="activity-item" @click="openActivity(item)">
            <div class="activity-dot" :class="item.tone"></div>
            <div class="activity-main">
              <b>{{ item.title }}</b>
              <p>{{ item.description }}</p>
            </div>
            <StatusBadge :status="item.status" />
            <time>{{ item.time }}</time>
          </article>
        </div>
        <EmptyState v-else title="暂无活动" description="第一次部署或发布之后，这里会自动生成你的软件活动流。" />
      </section>

      <section class="surface quick-actions-card">
        <div class="surface-header">
          <div>
            <h3>Quick actions</h3>
            <p>围绕“下一步操作”组织体验，而不是配置项。</p>
          </div>
        </div>
        <div class="quick-actions">
          <button @click="$router.push('/applications/new')">
            <strong>Create application</strong>
            <span>从仓库创建一个新的服务工作区</span>
          </button>
          <button @click="$router.push('/releases')">
            <strong>Review releases</strong>
            <span>查看发布历史、回滚与交付轨迹</span>
          </button>
          <button @click="$router.push('/approvals')">
            <strong>Handle approvals</strong>
            <span>快速处理 Production 变更申请</span>
          </button>
          <button @click="$router.push('/pipelines')">
            <strong>Inspect pipelines</strong>
            <span>定位失败构建或进行中的执行</span>
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useApplicationStore } from '../stores/application'
import { applicationApi } from '../api/application'
import { useCommandCenter } from '../composables/useCommandCenter'
import type { Release } from '../types'
import MetricCard from '../components/common/MetricCard.vue'
import StatusBadge from '../components/common/StatusBadge.vue'
import EmptyState from '../components/common/EmptyState.vue'

const router = useRouter()
const store = useApplicationStore()
const loading = ref(false)
const releases = ref<Release[]>([])
const command = ref('')
const { quickPrompts, runIntent, openPalette } = useCommandCenter()

const executions = computed(() => store.items.flatMap(a => a.latest_execution ? [{ ...a.latest_execution, appName: a.name }] : []))
const pipelineCount = computed(() => executions.value.length)
const failedCount = computed(() => executions.value.filter(e => e.status === 'Failed').length)
const healthyCount = computed(() => executions.value.filter(e => e.status === 'Succeeded').length)
const runningCount = computed(() => executions.value.filter(e => ['Running', 'Pending'].includes(e.status)).length)
const unknownCount = computed(() => Math.max(store.items.length - healthyCount.value - runningCount.value - failedCount.value, 0))
const successRate = computed(() => pipelineCount.value ? Math.round((healthyCount.value / pipelineCount.value) * 100) : 100)
const donutStyle = computed(() => ({
  background: `conic-gradient(var(--success) 0 ${successRate.value}%, rgba(220,38,38,.18) ${successRate.value}% 100%)`,
}))

const suggestedActions = computed(() => [
  {
    tag: failedCount.value ? 'Incident' : 'Healthy',
    title: failedCount.value ? `有 ${failedCount.value} 条失败执行等待处理` : '当前没有失败执行',
    description: failedCount.value ? '优先查看最近失败的 Pipeline 与发布记录，缩短恢复时间。' : '你可以继续推进今天的发布计划。',
    cta: failedCount.value ? '查看 pipelines' : '查看发布中心',
    run: () => router.push(failedCount.value ? '/pipelines' : '/releases'),
  },
  {
    tag: runningCount.value ? 'Live' : 'Flow',
    title: runningCount.value ? `${runningCount.value} 个交付流程正在进行` : '没有进行中的部署',
    description: runningCount.value ? '检查进行中的发布，确认是否需要人工关注或等待审批。' : '可以发起新的部署或创建一个新应用。',
    cta: runningCount.value ? '查看运行' : '创建应用',
    run: () => router.push(runningCount.value ? '/pipelines' : '/applications/new'),
  },
  {
    tag: 'AI',
    title: '让 Aegis 帮你决定下一步',
    description: '把自然语言输入放到主页中心，逐步替代配置表单与传统仪表盘。',
    cta: '试一个命令',
    run: () => openPalette('Deploy payment service to production'),
  },
])

const activityFeed = computed(() => {
  const pipelineActivities = executions.value.map(item => ({
    id: `pipeline-${item.pipeline_run_name}`,
    type: 'pipeline',
    title: item.pipeline_run_name,
    description: `${item.appName} · 最新交付执行`,
    status: item.status,
    tone: item.status === 'Failed' ? 'danger' : item.status === 'Succeeded' ? 'success' : 'info',
    time: formatTime(item.created_at),
    path: `/pipelines/${item.pipeline_run_name}`,
  }))

  const releaseActivities = releases.value.slice(0, 6).map(item => ({
    id: `release-${item.id}`,
    type: 'release',
    title: item.image_tag,
    description: `${item.environment.toUpperCase()} · ${item.deploy_user}`,
    status: item.deploy_status,
    tone: item.deploy_status === 'Failed' ? 'danger' : item.deploy_status === 'Succeeded' ? 'success' : 'warning',
    time: formatTime(item.created_at),
    path: '/releases',
  }))

  return [...pipelineActivities, ...releaseActivities]
    .sort((a, b) => b.time.localeCompare(a.time))
    .slice(0, 8)
})

function formatTime(value: string) {
  return new Date(value).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function openActivity(item: { path: string }) {
  router.push(item.path)
}

function fillPrompt(value: string) {
  command.value = value
}

async function runCommand() {
  await runIntent(command.value)
}

async function refresh() {
  loading.value = true
  try {
    await store.load()
    const data = await Promise.all(store.items.slice(0, 8).map(a => applicationApi.releases(a.id).catch(() => [])))
    releases.value = data.flat().sort((a, b) => b.created_at.localeCompare(a.created_at))
  } finally {
    loading.value = false
  }
}

onMounted(refresh)
</script>

<style scoped>
.hero {
  padding: 28px;
}

.hero-copy {
  max-width: 760px;
}

.hero h1 {
  margin: 18px 0 12px;
  font-size: 48px;
  line-height: 1.02;
  letter-spacing: -0.06em;
}

.hero p {
  margin: 0;
  max-width: 720px;
  color: var(--muted);
  font-size: 16px;
  line-height: 1.75;
}

.hero-command {
  margin-top: 24px;
}

.command-input {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 68px;
  padding: 0 16px;
  border-radius: 18px;
  border: 1px solid var(--border-soft);
  background: var(--theme-panel);
}

.command-input span {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  background: var(--primary-soft);
  color: var(--primary);
  font-weight: 700;
}

.command-input input {
  flex: 1;
  border: 0;
  background: transparent;
  outline: none;
  color: var(--text);
  font-size: 16px;
}

.run-button {
  min-width: 88px;
  height: 42px;
  border: 0;
  border-radius: 12px;
  background: var(--primary);
  color: white;
  font-weight: 700;
  cursor: pointer;
}

.prompt-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}

.prompt-list button {
  min-height: 36px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid var(--border-soft);
  background: var(--surface-soft);
  color: var(--text);
  cursor: pointer;
}

.metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.overview-grid,
.activity-grid {
  display: grid;
  grid-template-columns: 1.25fr 0.95fr;
  gap: 16px;
}

.recommendation-list,
.activity-list,
.quick-actions {
  display: flex;
  flex-direction: column;
}

.recommendation-item,
.activity-item {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 20px;
  padding: 22px 24px;
  border-top: 1px solid var(--border-soft);
}

.recommendation-item:first-child,
.activity-item:first-child {
  border-top: 0;
}

.recommendation-item h4 {
  margin: 14px 0 8px;
  font-size: 18px;
  letter-spacing: -0.03em;
}

.recommendation-item p {
  margin: 0;
  color: var(--muted);
  line-height: 1.7;
}

.health-card {
  padding-bottom: 24px;
}

.health-score {
  padding: 8px 24px 0;
  display: flex;
  align-items: center;
  gap: 28px;
}

.ring {
  width: 180px;
  height: 180px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  position: relative;
}

.ring::after {
  content: '';
  position: absolute;
  inset: 16px;
  border-radius: 50%;
  background: var(--theme-panel);
}

.ring > div {
  position: relative;
  z-index: 1;
  text-align: center;
}

.ring strong,
.ring span {
  display: block;
}

.ring strong {
  font-size: 34px;
  letter-spacing: -0.06em;
}

.ring span {
  margin-top: 8px;
  color: var(--muted);
  font-size: 12px;
}

.health-meta {
  flex: 1;
  display: grid;
  gap: 14px;
}

.health-meta div {
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 44px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--border-soft);
}

.health-meta label {
  color: var(--muted);
  font-size: 14px;
}

.health-meta b {
  font-size: 16px;
}

.activity-item {
  grid-template-columns: 12px 1fr auto auto;
  align-items: center;
  cursor: pointer;
}

.activity-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--info);
}

.activity-dot.success {
  background: var(--success);
}

.activity-dot.warning {
  background: var(--warning);
}

.activity-dot.danger {
  background: var(--danger);
}

.activity-main b {
  display: block;
  font-size: 14px;
}

.activity-main p {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 13px;
}

.activity-item time {
  color: var(--muted);
  font-size: 12px;
}

.quick-actions {
  padding: 12px 24px 24px;
  gap: 12px;
}

.quick-actions button {
  padding: 18px 18px;
  border-radius: 14px;
  border: 1px solid var(--border-soft);
  background: var(--surface-soft);
  text-align: left;
  cursor: pointer;
}

.quick-actions strong,
.quick-actions span {
  display: block;
}

.quick-actions span {
  margin-top: 6px;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.6;
}

@media (max-width: 1100px) {
  .metrics,
  .overview-grid,
  .activity-grid {
    grid-template-columns: 1fr;
  }

  .hero h1 {
    font-size: 38px;
  }

  .health-score {
    flex-direction: column;
    align-items: flex-start;
  }

  .activity-item {
    grid-template-columns: 12px 1fr;
  }
}
</style>
