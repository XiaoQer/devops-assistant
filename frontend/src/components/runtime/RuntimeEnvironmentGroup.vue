<template>
  <section class="surface environment-group">
    <header class="environment-head">
      <div>
        <span class="environment-name">{{ group.display_name }}</span>
        <small>{{ group.name }} · {{ group.cluster_name || 'Cluster unavailable' }}</small>
      </div>
      <div class="environment-counts">
        <span>{{ group.applications.length }} Applications</span>
        <span>{{ podCount }} Pods</span>
      </div>
    </header>

    <el-collapse>
      <el-collapse-item v-for="application in group.applications" :key="application.application_id">
        <template #title>
          <div class="deployment-row">
            <div class="application-identity">
              <span class="app-mark">{{ application.application_name[0]?.toUpperCase() }}</span>
              <div><strong>{{ application.application_name }}</strong><small>{{ application.namespace }}</small></div>
            </div>
            <StatusBadge :status="application.status" />
            <div class="replica-state">
              <strong>{{ application.deployment?.ready_replicas || 0 }}/{{ application.deployment?.replicas || 0 }}</strong>
              <small>Ready replicas</small>
            </div>
            <code>{{ application.deployment?.images?.[0] || 'No image' }}</code>
            <div class="deployment-actions" @click.stop>
              <el-button link :disabled="!application.deployment" @click="$emit('deployment-yaml', application)">YAML</el-button>
              <el-button link type="warning" :disabled="!application.deployment" @click="$emit('restart', application)">重启</el-button>
            </div>
          </div>
        </template>

        <el-alert
          v-if="application.error"
          :title="application.error.message"
          type="error"
          :closable="false"
          show-icon
        />
        <el-table v-else-if="application.pods.length" :data="application.pods" class="pod-table">
          <el-table-column label="Pod" min-width="250">
            <template #default="{ row }"><div class="pod-name"><i :class="{ ready: row.ready }"></i><strong>{{ row.name }}</strong></div></template>
          </el-table-column>
          <el-table-column label="状态" width="140"><template #default="{ row }"><StatusBadge :status="row.ready ? 'Healthy' : row.status" /></template></el-table-column>
          <el-table-column label="重启" width="90" prop="restart_count" />
          <el-table-column label="Node" min-width="150"><template #default="{ row }">{{ row.node || '—' }}</template></el-table-column>
          <el-table-column label="操作" width="260" fixed="right">
            <template #default="{ row }">
              <el-button link @click="$emit('pod-logs', application, row)">日志</el-button>
              <el-button link @click="$emit('pod-yaml', application, row)">YAML</el-button>
              <el-button link type="primary" :disabled="!row.containers?.length" @click="$emit('terminal', application, row)">终端</el-button>
              <el-button link type="danger" @click="$emit('delete-pod', application, row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div v-else class="empty-pods">尚未发现 Pod</div>
      </el-collapse-item>
    </el-collapse>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { RuntimeApplication, RuntimeEnvironmentGroup, RuntimePod } from '../../types'
import StatusBadge from '../common/StatusBadge.vue'

const props = defineProps<{ group: RuntimeEnvironmentGroup }>()
defineEmits<{
  'deployment-yaml': [application: RuntimeApplication]
  restart: [application: RuntimeApplication]
  'pod-logs': [application: RuntimeApplication, pod: RuntimePod]
  'pod-yaml': [application: RuntimeApplication, pod: RuntimePod]
  terminal: [application: RuntimeApplication, pod: RuntimePod]
  'delete-pod': [application: RuntimeApplication, pod: RuntimePod]
}>()
const podCount = computed(() => props.group.applications.reduce((sum, item) => sum + item.pods.length, 0))
</script>

<style scoped>
.environment-group { overflow: hidden; box-shadow: none; }
.environment-head { display: flex; align-items: center; justify-content: space-between; padding: 18px 22px; border-bottom: 1px solid var(--border-soft); }
.environment-head > div:first-child, .application-identity > div { display: grid; gap: 4px; }
.environment-name { color: var(--text-2); font-size: 17px; font-weight: 800; }
.environment-head small, .application-identity small, .replica-state small { color: var(--muted); font-size: 11px; }
.environment-counts { display: flex; gap: 8px; }
.environment-counts span { padding: 5px 9px; border-radius: 999px; background: var(--surface-soft); color: var(--muted); font-size: 11px; }
.deployment-row { width: 100%; display: grid; grid-template-columns: minmax(210px, 1.2fr) 130px 110px minmax(160px, 1fr) 120px; align-items: center; gap: 16px; padding-right: 12px; }
.application-identity { display: flex; align-items: center; gap: 10px; min-width: 0; }
.app-mark { display: grid; place-items: center; width: 30px; height: 30px; border-radius: 9px; background: var(--primary-soft); color: var(--primary); font-weight: 800; }
.replica-state { display: grid; }
.deployment-row code { overflow: hidden; color: var(--muted); font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.deployment-actions { display: flex; }
.pod-table { padding: 0 18px 18px; }
.pod-name { display: flex; align-items: center; gap: 9px; }
.pod-name i { width: 8px; height: 8px; border-radius: 50%; background: var(--danger); }
.pod-name i.ready { background: var(--success); }
.empty-pods { padding: 22px; color: var(--muted); text-align: center; }
@media (max-width: 1050px) { .deployment-row { grid-template-columns: minmax(180px, 1fr) 120px 90px 110px; } .deployment-row code { display: none; } }
@media (max-width: 760px) { .environment-head { align-items: flex-start; gap: 12px; } .deployment-row { grid-template-columns: 1fr auto; } .replica-state, .deployment-actions { display: none; } }
</style>
