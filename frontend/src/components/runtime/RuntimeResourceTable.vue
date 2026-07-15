<template>
  <el-table :data="items" class="runtime-table" :row-key="rowKey">
    <template v-if="resource === 'deployments'">
      <el-table-column label="Application / Deployment" min-width="260"><template #default="{ row }"><div class="identity"><strong>{{ row.application_name }}</strong><small>{{ row.deployment?.name || row.namespace }}</small></div></template></el-table-column>
      <el-table-column label="状态" width="130"><template #default="{ row }"><StatusBadge :status="row.status" /></template></el-table-column>
      <el-table-column label="副本" width="100"><template #default="{ row }">{{ row.deployment?.ready_replicas || 0 }}/{{ row.deployment?.replicas || 0 }}</template></el-table-column>
      <el-table-column label="Pods" width="90" prop="pod_count" />
      <el-table-column label="重启" width="90" prop="restart_count" />
      <el-table-column label="镜像" min-width="260"><template #default="{ row }"><code>{{ row.deployment?.images?.[0] || '—' }}</code></template></el-table-column>
      <el-table-column label="操作" width="140" fixed="right"><template #default="{ row }"><el-button link @click="$emit('yaml', row)">YAML</el-button><el-button link type="warning" @click="$emit('restart', row)">重启</el-button></template></el-table-column>
    </template>
    <template v-else>
      <el-table-column label="Pod" min-width="280"><template #default="{ row }"><el-button link type="primary" @click="$emit('pod-detail', row)">{{ row.name }}</el-button><small class="namespace">{{ row.namespace }}</small></template></el-table-column>
      <el-table-column label="Application" min-width="180" prop="application_name" />
      <el-table-column label="状态" width="150"><template #default="{ row }"><StatusBadge :status="row.ready ? 'Healthy' : row.status" /></template></el-table-column>
      <el-table-column label="Ready" width="90"><template #default="{ row }">{{ row.ready ? 'Yes' : 'No' }}</template></el-table-column>
      <el-table-column label="Containers" width="110"><template #default="{ row }">{{ row.containers?.length || 0 }}</template></el-table-column>
      <el-table-column label="重启" width="90" prop="restart_count" />
      <el-table-column label="Node" min-width="180"><template #default="{ row }">{{ row.node || '—' }}</template></el-table-column>
    </template>
  </el-table>
</template>
<script setup lang="ts">
import type { RuntimeInventoryItem } from '../../types'
import StatusBadge from '../common/StatusBadge.vue'
defineProps<{ items: RuntimeInventoryItem[]; resource: 'deployments' | 'pods' }>()
defineEmits<{ yaml: [row: RuntimeInventoryItem]; restart: [row: RuntimeInventoryItem]; 'pod-detail': [row: RuntimeInventoryItem] }>()
const rowKey = (row: RuntimeInventoryItem) => `${row.resource}:${row.application_id}:${row.name || row.deployment?.name || ''}`
</script>
<style scoped>
.identity { display:grid; gap:4px }.identity small,.namespace{display:block;color:var(--muted);font-size:11px}.runtime-table code{font-size:11px;color:var(--muted)}
</style>
