<template>
  <div class="container-first-layout">
    <main class="pod-main">
      <section class="overview-section">
        <div class="section-heading"><div><span class="section-kicker">WORKLOAD</span><h3>容器</h3></div><span class="section-count">{{ pod.containers.length }} 个容器</span></div>
        <div v-if="pod.containers.length" class="container-list">
          <article v-for="container in pod.containers" :key="container.name" class="container-row">
            <div class="container-identity"><span class="state-dot" :class="container.ready ? 'ready' : 'warning'" /><div><strong>{{ container.name }}</strong><code>{{ container.image }}</code></div></div>
            <div class="container-field"><small>状态</small><strong :class="container.ready ? 'text-success' : 'text-warning'">{{ containerStateLabel(container) }}</strong></div>
            <div class="container-field"><small>就绪</small><strong>{{ container.ready ? '1/1' : '0/1' }}</strong></div>
            <div class="container-field"><small>重启次数</small><strong>{{ container.restart_count }}</strong></div>
            <div class="container-field container-started"><small>启动时间</small><span>{{ formatRuntimeTime(container.started_at) }}</span></div>
            <div class="container-actions">
              <el-button size="small" data-runtime-action="container-logs" @click="$emit('container-logs', container.name)">查看日志</el-button>
              <el-tooltip :content="terminalEnabled ? '打开终端' : '终端权限不足'" placement="top">
                <el-button size="small" type="primary" plain circle :icon="Monitor" :disabled="!terminalEnabled" aria-label="打开终端" data-runtime-action="container-terminal" @click="$emit('container-terminal', container.name)" />
              </el-tooltip>
            </div>
            <p v-if="container.message" class="container-message">{{ container.message }}</p>
          </article>
        </div>
        <div v-else class="empty-state">暂无容器信息</div>
      </section>
      <section class="overview-section">
        <div class="section-heading"><div><span class="section-kicker">HEALTH</span><h3>Conditions</h3></div><span class="section-count">{{ pod.conditions.length }} 条状态</span></div>
        <el-table class="light-table" :data="pod.conditions" empty-text="暂无 Conditions">
          <el-table-column prop="type" label="类型" min-width="170" />
          <el-table-column label="状态" width="100"><template #default="{ row }"><span class="condition-state" :class="String(row.status).toLowerCase() === 'true' ? 'is-true' : 'is-false'"><i />{{ row.status }}</span></template></el-table-column>
          <el-table-column prop="reason" label="原因" min-width="160" />
          <el-table-column prop="message" label="消息" min-width="260" show-overflow-tooltip />
          <el-table-column label="最后变化" width="190"><template #default="{ row }">{{ formatRuntimeTime(row.last_transition_time) }}</template></el-table-column>
        </el-table>
      </section>
      <section class="overview-section">
        <div class="section-heading"><div><span class="section-kicker">ACTIVITY</span><h3>最近 Events</h3></div><span class="section-count">{{ pod.events.length }} 条事件</span></div>
        <el-table class="light-table" :data="pod.events" empty-text="暂无 Events">
          <el-table-column label="时间" width="190"><template #default="{ row }">{{ formatRuntimeTime(row.timestamp) }}</template></el-table-column>
          <el-table-column prop="type" label="类型" width="100" />
          <el-table-column prop="reason" label="原因" min-width="160" />
          <el-table-column prop="message" label="消息" min-width="320" show-overflow-tooltip />
          <el-table-column prop="count" label="次数" width="80" />
        </el-table>
      </section>
    </main>
    <aside class="pod-facts">
      <div class="facts-heading"><span class="section-kicker">POD INFORMATION</span><h3>Pod 信息</h3></div>
      <dl>
        <div><dt>Namespace</dt><dd>{{ pod.namespace }}</dd></div><div><dt>Node</dt><dd>{{ pod.node || '—' }}</dd></div>
        <div><dt>Pod IP</dt><dd>{{ pod.pod_ip || '—' }}</dd></div><div><dt>Host IP</dt><dd>{{ pod.host_ip || '—' }}</dd></div>
        <div><dt>QoS Class</dt><dd>{{ pod.qos_class || '—' }}</dd></div><div><dt>创建时间</dt><dd>{{ formatRuntimeTime(pod.created_at) }}</dd></div>
        <div><dt>启动时间</dt><dd>{{ formatRuntimeTime(pod.start_time) }}</dd></div><div><dt>累计重启</dt><dd>{{ pod.restart_count }}</dd></div>
      </dl>
    </aside>
  </div>
</template>
<script setup lang="ts">
import type { RuntimePodDetail } from '../../types'
import { Monitor } from '@element-plus/icons-vue'
import { containerStateLabel, formatRuntimeTime } from './pod-detail-view-model'
defineProps<{ pod: RuntimePodDetail; terminalEnabled: boolean }>()
defineEmits<{ 'container-logs': [name: string]; 'container-terminal': [name: string] }>()
</script>
<style scoped>
.container-first-layout{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;padding:20px 0}.pod-main{display:grid;gap:16px;min-width:0}.overview-section,.pod-facts{border:1px solid var(--border-soft);border-radius:10px;background:var(--surface);overflow:hidden}.section-heading,.facts-heading{display:flex;align-items:flex-end;justify-content:space-between;gap:12px;padding:16px 18px;border-bottom:1px solid var(--border-soft)}.section-heading h3,.facts-heading h3{margin:4px 0 0;color:var(--text);font-size:16px}.section-kicker{color:var(--subtle);font-size:10px;font-weight:750;letter-spacing:.1em;text-transform:uppercase}.section-count{color:var(--muted);font-size:12px}.container-list{display:grid}.container-row{display:grid;grid-template-columns:minmax(240px,1.6fr) 78px 60px 76px minmax(120px,1fr) auto;gap:12px;align-items:center;padding:16px 18px;border-bottom:1px solid var(--border-soft)}.container-row:last-child{border-bottom:0}.container-identity{display:flex;align-items:flex-start;gap:10px;min-width:0}.container-identity>div{min-width:0}.state-dot{width:8px;height:8px;flex:0 0 auto;margin-top:5px;border-radius:50%;background:var(--warning)}.state-dot.ready{background:var(--success)}.container-identity strong,.container-identity code{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.container-identity strong{color:var(--text);font-size:13px}.container-identity code{max-width:240px;margin-top:4px;color:var(--muted);font-size:11px}.container-field{display:grid;gap:5px;min-width:0}.container-field small{color:var(--subtle);font-size:10px}.container-field strong,.container-field span{overflow:hidden;color:var(--text);font-size:12px;text-overflow:ellipsis;white-space:nowrap}.text-success{color:var(--success)!important}.text-warning{color:var(--warning)!important}.container-actions{display:flex;gap:6px;justify-content:flex-end;flex-wrap:wrap}.container-message{grid-column:1/-1;margin:0;padding:8px 10px;border-radius:6px;background:var(--surface-soft);color:var(--danger);font-size:12px}.empty-state{padding:28px 18px;color:var(--muted);font-size:13px;text-align:center}.light-table :deep(.el-table__header-wrapper th.el-table__cell){background:#f7f9fc!important;color:var(--muted)!important;border-bottom:1px solid var(--border-soft);font-size:11px;font-weight:700}.light-table :deep(.el-table__body td.el-table__cell){color:var(--text);border-bottom:1px solid #eef2f6;font-size:12px}.light-table :deep(.el-table__body tr:hover>td.el-table__cell){background:#fbfdff!important}.condition-state{display:inline-flex;align-items:center;gap:6px;font-size:12px}.condition-state i{width:6px;height:6px;border-radius:50%;background:var(--muted)}.condition-state.is-true{color:var(--success)}.condition-state.is-true i{background:var(--success)}.condition-state.is-false{color:var(--danger)}.condition-state.is-false i{background:var(--danger)}.pod-facts{align-self:start;position:sticky;top:16px}.pod-facts dl{margin:0;padding:0 18px}.pod-facts dl div{display:grid;gap:5px;padding:13px 0;border-bottom:1px solid var(--border-soft)}.pod-facts dl div:last-child{border-bottom:0}.pod-facts dt{color:var(--muted);font-size:11px}.pod-facts dd{margin:0;color:var(--text);font-size:13px;font-weight:600;overflow-wrap:anywhere}@media(max-width:960px){.container-first-layout{grid-template-columns:1fr}.pod-facts{position:static}.container-row{grid-template-columns:minmax(180px,1fr) repeat(3,72px) auto}.container-started{display:none}}@media(max-width:640px){.container-first-layout{padding:12px 0}.container-row{grid-template-columns:1fr 1fr;gap:12px}.container-identity,.container-actions,.container-message{grid-column:1/-1}.container-actions{justify-content:flex-start}.section-heading,.facts-heading{padding:14px}.light-table{overflow:auto}}
</style>
