<template>
  <el-table ref="table" :data="items" class="runtime-table" :row-key="rowKey" @expand-change="onExpand" @row-click="onRowClick">
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
    <el-table-column label="操作" width="88" align="center" fixed="right">
      <template #default="{ row }">
        <div class="row-actions" data-runtime-action="actions">
          <el-dropdown trigger="click" popper-class="runtime-actions-menu" @command="onAction($event, row)">
            <el-button class="more-action" text :icon="MoreFilled" aria-label="Deployment 更多操作" data-runtime-action="menu" />
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="yaml">查看 YAML</el-dropdown-item>
                <el-dropdown-item command="restart" divided class="danger-item">重启 Deployment</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </template>
    </el-table-column>
  </el-table>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { MoreFilled } from '@element-plus/icons-vue'
import type { DeploymentPodEntry } from '../../composables/useDeploymentPods'
import type { RuntimeInventoryItem, RuntimePodSummary } from '../../types'
import StatusBadge from '../common/StatusBadge.vue'
import DeploymentPodTable from './DeploymentPodTable.vue'
import { shouldToggleDeploymentRow } from './runtime-view-model'
defineProps<{ items: RuntimeInventoryItem[]; podEntries: Record<string, DeploymentPodEntry> }>()
const emit=defineEmits<{ yaml:[row:RuntimeInventoryItem];restart:[row:RuntimeInventoryItem];expand:[row:RuntimeInventoryItem,force:boolean];'pod-detail':[row:RuntimeInventoryItem,pod:RuntimePodSummary] }>()
const table=ref<{toggleRowExpansion:(row:RuntimeInventoryItem)=>void}>()
const rowKey=(row:RuntimeInventoryItem)=>`${row.application_id}:${row.deployment?.name||''}`
function onExpand(row:RuntimeInventoryItem){emit('expand',row,false)}
function onAction(command:string,row:RuntimeInventoryItem){
  if(command==='yaml')emit('yaml',row)
  if(command==='restart')emit('restart',row)
}
function onRowClick(row:RuntimeInventoryItem,column:{type?:string}|null,event:PointerEvent){
  if(column?.type==='expand')return
  const action=(event.target as HTMLElement|null)?.closest<HTMLElement>('[data-runtime-action]')?.dataset.runtimeAction
  if(shouldToggleDeploymentRow(action))table.value?.toggleRowExpansion(row)
}
</script>
<style scoped>
.identity{display:grid;gap:4px}.identity strong{color:#344054;font-weight:700}.identity small{display:block;color:#667085;font-size:11px}.runtime-table code{font-size:11px;color:#344054}.row-actions{display:flex;justify-content:center}.more-action{width:32px;height:32px;color:#667085}.more-action:hover{background:#eef3fa!important;color:#344054!important}.runtime-table{--el-table-header-bg-color:#f6f8fc;--el-table-header-text-color:#667085;--el-table-row-hover-bg-color:#f7faff;--el-table-border-color:#e8edf5;--el-table-expanded-cell-bg-color:#f7f9fd}:deep(.el-table__header-wrapper th.el-table__cell){background:#f6f8fc!important;color:#667085!important;border-bottom:1px solid #e3e9f2;font-size:12px;font-weight:700;letter-spacing:.04em;text-transform:none}:deep(.el-table__body tr:not(.el-table__expanded-cell):hover>td.el-table__cell){background:#f7faff!important}:deep(.el-table__body tr:not(.el-table__expanded-cell)>td.el-table__cell){color:#475467;cursor:pointer}:deep(.el-table__expanded-cell){padding:0!important;background:#f7f9fd!important}:deep(.el-table__expand-icon){color:#667085}:global(.runtime-actions-menu .danger-item){color:#b54708}:global(.runtime-actions-menu .danger-item:hover){background:#fff7ed;color:#9a3412}
</style>
