<template>
  <div v-if="status" class="runtime page-stack">
    <div class="runtime-cards">
      <section class="surface deployment-card">
        <div class="surface-header">
          <div>
            <h3>Deployment</h3>
            <p>{{ status.namespace }} / {{ status.deployment.name }}</p>
          </div>
          <StatusBadge :status="status.status" />
        </div>
        <div class="deploy-body">
          <div class="replicas">
            <strong>{{ status.deployment.ready_replicas }}</strong>
            <span>/ {{ status.deployment.replicas }} ready</span>
          </div>
          <div class="bars">
            <i v-for="n in Math.max(status.deployment.replicas, 1)" :key="n" :class="{ ready: n <= status.deployment.ready_replicas }" />
          </div>
          <pre class="code-block inline-code">{{ status.deployment.images?.[0] || 'No image deployed' }}</pre>
        </div>
      </section>

      <section class="surface network-card">
        <div class="surface-header">
          <div>
            <h3>Network</h3>
            <p>Service 与 Ingress</p>
          </div>
        </div>
        <dl>
          <div>
            <dt>Service</dt>
            <dd>{{ status.service?.name || 'Not configured' }}</dd>
            <small>{{ status.service?.type || '—' }} {{ status.service?.cluster_ip || '' }}</small>
          </div>
          <div>
            <dt>Ingress</dt>
            <dd>{{ status.ingress?.host || 'Not configured' }}</dd>
            <small>{{ status.ingress?.address || '—' }}</small>
          </div>
        </dl>
      </section>
    </div>

    <section class="surface list-card">
      <div class="surface-header">
        <div>
          <h3>Pods</h3>
          <p>工作负载实时状态</p>
        </div>
        <span>{{ status.pods.length }} pods</span>
      </div>
      <div v-if="status.pods.length" class="pod-list">
        <article v-for="row in status.pods" :key="row.name" class="pod-card">
          <div>
            <h4>{{ row.name }}</h4>
            <p>{{ row.node }}</p>
          </div>
          <StatusBadge :status="row.ready ? 'Healthy' : row.status" />
          <div class="pod-meta">
            <span class="soft-pill">{{ row.ready ? 'Ready' : 'Not ready' }}</span>
            <span class="soft-pill">{{ row.restart_count }} restarts</span>
          </div>
          <div class="pod-actions">
            <el-button link :loading="loadingPod === row.name" @click="openPod(row.name, 'logs')">Logs</el-button>
            <el-button link :loading="loadingPod === row.name" @click="openPod(row.name, 'yaml')">YAML</el-button>
          </div>
        </article>
      </div>
      <EmptyState v-else title="暂无 Pod" description="应用尚未部署，或工作负载还未创建。" />
    </section>

    <div class="inventory-grid">
      <ResourceList title="ReplicaSets" :items="status.replica_sets || []" empty="暂无 ReplicaSet" />
      <ResourceList title="PVC" :items="status.persistent_volume_claims || []" empty="暂无持久化存储" />
      <ResourceList title="ConfigMaps" :items="status.config_maps || []" empty="暂无 ConfigMap" />
      <ResourceList title="Secrets" :items="status.secrets || []" empty="暂无 Secret" />
    </div>

    <section class="surface events-card">
      <div class="surface-header">
        <div>
          <h3>Events</h3>
          <p>Kubernetes 最近事件</p>
        </div>
      </div>
      <div v-if="status.events.length" class="event-list">
        <article v-for="(event, index) in status.events" :key="index" class="event-item">
          <StatusBadge :status="event.type === 'Warning' ? 'Failed' : 'Succeeded'" :label="event.type" />
          <div>
            <b>{{ event.reason }}</b>
            <p>{{ event.message }}</p>
          </div>
          <span>×{{ event.count }}</span>
        </article>
      </div>
      <EmptyState v-else title="没有异常事件" description="当前应用没有需要关注的 Kubernetes Event。" icon="✓" />
    </section>

    <el-drawer v-model="drawer" :title="`${selectedPod} · ${drawerMode.toUpperCase()}`" size="62%">
      <div class="drawer-tools"><el-button size="small" @click="copyContent">复制</el-button></div>
      <pre class="code-block pod-output">{{ podContent }}</pre>
    </el-drawer>
  </div>
  <EmptyState v-else title="运行状态不可用" description="尚未部署应用，或暂时无法连接 Kubernetes。" />
</template>

<script setup lang="ts">
import { defineComponent, h, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { RuntimeStatus } from '../../types'
import { applicationApi } from '../../api/application'
import StatusBadge from '../common/StatusBadge.vue'
import EmptyState from '../common/EmptyState.vue'

const props = defineProps<{ status?: RuntimeStatus; applicationId?: number; projectId?: number; environment?: string }>()
const drawer = ref(false)
const drawerMode = ref('logs')
const selectedPod = ref('')
const podContent = ref('')
const loadingPod = ref('')

const ResourceList = defineComponent({
  props: {
    title: { type: String, required: true },
    items: { type: Array, required: true },
    empty: { type: String, required: true },
  },
  setup(componentProps) {
    return () => h('section', { class: 'surface inventory' }, [
      h('div', { class: 'inventory-title' }, [h('h3', componentProps.title), h('span', String(componentProps.items.length))]),
      componentProps.items.length
        ? h('div', { class: 'inventory-items' }, componentProps.items.slice(0, 8).map((item: any) => h('article', [
            h('b', item.name || 'resource'),
            h('small', item.status || item.type || item.storage_class || 'Managed by Kubernetes'),
          ])))
        : h('p', { class: 'inventory-empty' }, componentProps.empty),
    ])
  },
})

async function openPod(name: string, mode: 'logs' | 'yaml') {
  if (!props.applicationId) return
  selectedPod.value = name
  drawerMode.value = mode
  loadingPod.value = name
  try {
    if (mode === 'logs') {
      const result = await applicationApi.podLogs(props.projectId || 0, props.applicationId, name, props.environment || 'dev')
      podContent.value = result.logs || '该 Pod 暂无日志。'
    } else {
      const result = await applicationApi.podYaml(props.projectId || 0, props.applicationId, name, props.environment || 'dev')
      podContent.value = JSON.stringify(result, null, 2)
    }
    drawer.value = true
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    loadingPod.value = ''
  }
}

function copyContent() {
  navigator.clipboard.writeText(podContent.value)
  ElMessage.success('内容已复制')
}
</script>

<style scoped>
.runtime-cards {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 16px;
}

.deployment-card,
.network-card,
.list-card,
.inventory,
.events-card {
  box-shadow: none;
}

.deploy-body {
  padding: 24px;
}

.replicas strong {
  font-size: 34px;
  letter-spacing: -0.05em;
}

.replicas span {
  color: var(--muted);
  font-size: 13px;
}

.bars {
  display: flex;
  gap: 8px;
  margin: 18px 0;
}

.bars i {
  height: 8px;
  max-width: 60px;
  flex: 1;
  border-radius: 999px;
  background: var(--border-soft);
}

.bars i.ready {
  background: var(--success);
}

.inline-code {
  margin: 0;
}

.network-card dl {
  margin: 0;
  padding: 8px 24px 24px;
}

.network-card dl div {
  padding: 16px 0;
  border-bottom: 1px solid var(--border-soft);
}

.network-card dt {
  font-size: 12px;
  color: var(--muted);
}

.network-card dd {
  font-size: 14px;
  margin: 8px 0 6px;
  font-weight: 600;
}

.network-card small {
  color: var(--muted);
}

.list-card,
.events-card {
  overflow: hidden;
}

.surface-header > span {
  font-size: 12px;
  color: var(--muted);
}

.pod-list {
  padding: 12px 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pod-card {
  display: grid;
  grid-template-columns: 1fr auto auto auto;
  gap: 14px;
  align-items: center;
  padding: 18px;
  border-radius: 14px;
  border: 1px solid var(--border-soft);
  background: var(--surface-soft);
}

.pod-card h4 {
  margin: 0 0 6px;
  font-size: 16px;
}

.pod-card p {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
}

.pod-meta,
.pod-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.inventory-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.inventory {
  overflow: hidden;
}

.inventory-title {
  height: 54px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border-soft);
}

.inventory-title h3 {
  margin: 0;
  font-size: 14px;
}

.inventory-title span {
  color: var(--muted);
  font-size: 12px;
}

.inventory-items article {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-soft);
}

.inventory-items b,
.inventory-items small {
  display: block;
}

.inventory-items b {
  font-size: 13px;
}

.inventory-items small {
  margin-top: 6px;
  color: var(--muted);
}

.inventory-empty {
  padding: 18px 16px;
  margin: 0;
  color: var(--muted);
}

.event-list {
  padding: 12px 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.event-item {
  display: grid;
  grid-template-columns: 110px 1fr auto;
  gap: 14px;
  align-items: start;
  padding: 16px 18px;
  border-radius: 14px;
  background: var(--surface-soft);
  border: 1px solid var(--border-soft);
}

.event-item b {
  display: block;
  font-size: 14px;
  margin-bottom: 6px;
}

.event-item p {
  margin: 0;
  color: var(--muted);
  line-height: 1.7;
}

.event-item > span {
  color: var(--muted);
}

.drawer-tools {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

.pod-output {
  min-height: 520px;
  white-space: pre-wrap;
}

@media (max-width: 1100px) {
  .runtime-cards,
  .inventory-grid,
  .pod-card,
  .event-item {
    grid-template-columns: 1fr;
  }
}
</style>
