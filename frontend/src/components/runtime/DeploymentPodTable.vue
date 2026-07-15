<template>
  <div class="deployment-pods">
    <div v-if="entry?.loading" class="pod-state"><el-icon class="is-loading"><Loading /></el-icon> 正在读取 Pods…</div>
    <el-alert v-else-if="entry?.error" :title="entry.error" type="warning" :closable="false" show-icon>
      <template #default><el-button link type="primary" @click="$emit('retry')">重试</el-button></template>
    </el-alert>
    <el-table v-else-if="entry?.pods.length" :data="entry.pods" :show-header="true" size="small" class="pod-table" row-key="name">
      <el-table-column label="Pod" min-width="260"><template #default="{ row }"><el-button link type="primary" @click="$emit('pod-detail', row)">{{ row.name }}</el-button></template></el-table-column>
      <el-table-column label="状态" width="150"><template #default="{ row }"><StatusBadge :status="row.ready ? 'Healthy' : row.status" /></template></el-table-column>
      <el-table-column label="Ready" width="90"><template #default="{ row }">{{ row.ready ? 'Yes' : 'No' }}</template></el-table-column>
      <el-table-column label="Containers" width="110"><template #default="{ row }">{{ row.containers.length }}</template></el-table-column>
      <el-table-column prop="restart_count" label="重启" width="80" />
      <el-table-column label="Node" min-width="150"><template #default="{ row }">{{ row.node || '—' }}</template></el-table-column>
      <el-table-column label="创建时间" width="180"><template #default="{ row }">{{ formatRuntimeTime(row.created_at) }}</template></el-table-column>
    </el-table>
    <div v-else-if="entry?.loaded" class="pod-state">该 Deployment 当前没有 Pod</div>
  </div>
</template>
<script setup lang="ts">
import { Loading } from '@element-plus/icons-vue'
import type { DeploymentPodEntry } from '../../composables/useDeploymentPods'
import type { RuntimePodSummary } from '../../types'
import StatusBadge from '../common/StatusBadge.vue'
import { formatRuntimeTime } from './pod-detail-view-model'
defineProps<{ entry?: DeploymentPodEntry }>()
defineEmits<{ retry: []; 'pod-detail': [pod: RuntimePodSummary] }>()
</script>
<style scoped>
.deployment-pods{padding:12px 20px 16px 52px;background:var(--surface-muted,#f8fafc)}.pod-state{display:flex;align-items:center;gap:8px;min-height:54px;color:var(--muted);font-size:13px}.pod-table{border:1px solid var(--border-soft);border-radius:10px;overflow:hidden}
</style>
