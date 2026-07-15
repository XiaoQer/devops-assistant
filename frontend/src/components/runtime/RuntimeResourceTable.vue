<template>
  <el-table :data="items" class="runtime-table" :row-key="rowKey" @expand-change="onExpand">
    <el-table-column type="expand" width="52">
      <template #default="{ row }">
        <DeploymentPodTable :entry="podEntries[rowKey(row)]" @retry="$emit('expand', row, true)" @pod-detail="pod => $emit('pod-detail', row, pod)" />
      </template>
    </el-table-column>
    <el-table-column label="Application / Deployment" min-width="260"><template #default="{ row }"><div class="identity"><strong>{{ row.application_name }}</strong><small>{{ row.deployment?.name || row.namespace }}</small></div></template></el-table-column>
    <el-table-column label="状态" width="130"><template #default="{ row }"><StatusBadge :status="row.status" /></template></el-table-column>
    <el-table-column label="副本" width="100"><template #default="{ row }">{{ row.deployment?.ready_replicas || 0 }}/{{ row.deployment?.replicas || 0 }}</template></el-table-column>
    <el-table-column label="Pods" width="90" prop="pod_count" />
    <el-table-column label="重启" width="90" prop="restart_count" />
    <el-table-column label="镜像" min-width="260"><template #default="{ row }"><code>{{ row.deployment?.images?.[0] || '—' }}</code></template></el-table-column>
    <el-table-column label="操作" width="140" fixed="right"><template #default="{ row }"><el-button link @click="$emit('yaml', row)">YAML</el-button><el-button link type="warning" @click="$emit('restart', row)">重启</el-button></template></el-table-column>
  </el-table>
</template>
<script setup lang="ts">
import type { DeploymentPodEntry } from '../../composables/useDeploymentPods'
import type { RuntimeInventoryItem, RuntimePodSummary } from '../../types'
import StatusBadge from '../common/StatusBadge.vue'
import DeploymentPodTable from './DeploymentPodTable.vue'
defineProps<{ items: RuntimeInventoryItem[]; podEntries: Record<string, DeploymentPodEntry> }>()
const emit=defineEmits<{ yaml:[row:RuntimeInventoryItem];restart:[row:RuntimeInventoryItem];expand:[row:RuntimeInventoryItem,force:boolean];'pod-detail':[row:RuntimeInventoryItem,pod:RuntimePodSummary] }>()
const rowKey=(row:RuntimeInventoryItem)=>`${row.application_id}:${row.deployment?.name||''}`
function onExpand(row:RuntimeInventoryItem){emit('expand',row,false)}
</script>
<style scoped>
.identity{display:grid;gap:4px}.identity small{display:block;color:var(--muted);font-size:11px}.runtime-table code{font-size:11px;color:var(--muted)}
</style>
