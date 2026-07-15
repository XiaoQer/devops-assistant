<template>
  <div class="pod-overview">
    <section class="surface facts">
      <h3>运行信息</h3>
      <dl>
        <div><dt>Namespace</dt><dd>{{ pod.namespace }}</dd></div>
        <div><dt>Node</dt><dd>{{ pod.node || '—' }}</dd></div>
        <div><dt>Pod IP</dt><dd>{{ pod.pod_ip || '—' }}</dd></div>
        <div><dt>Host IP</dt><dd>{{ pod.host_ip || '—' }}</dd></div>
        <div><dt>QoS Class</dt><dd>{{ pod.qos_class || '—' }}</dd></div>
        <div><dt>创建时间</dt><dd>{{ formatRuntimeTime(pod.created_at) }}</dd></div>
        <div><dt>启动时间</dt><dd>{{ formatRuntimeTime(pod.start_time) }}</dd></div>
        <div><dt>累计重启</dt><dd>{{ pod.restart_count }}</dd></div>
      </dl>
    </section>
    <section class="surface conditions">
      <h3>Conditions</h3>
      <el-table :data="pod.conditions" empty-text="暂无 Conditions">
        <el-table-column prop="type" label="类型" min-width="160" />
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column prop="reason" label="原因" min-width="160" />
        <el-table-column prop="message" label="消息" min-width="260" show-overflow-tooltip />
        <el-table-column label="最后变化" width="190"><template #default="{ row }">{{ formatRuntimeTime(row.last_transition_time) }}</template></el-table-column>
      </el-table>
    </section>
  </div>
</template>
<script setup lang="ts">
import type { RuntimePodDetail } from '../../types'
import { formatRuntimeTime } from './pod-detail-view-model'
defineProps<{ pod: RuntimePodDetail }>()
</script>
<style scoped>
.pod-overview{display:grid;gap:16px}.facts,.conditions{padding:20px;box-shadow:none}.facts h3,.conditions h3{margin:0 0 18px}.facts dl{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:20px;margin:0}.facts dl div{display:grid;gap:6px}.facts dt{color:var(--muted);font-size:12px}.facts dd{margin:0;color:var(--text);font-weight:600;word-break:break-all}@media(max-width:900px){.facts dl{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style>
