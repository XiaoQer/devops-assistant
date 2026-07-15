<template>
  <div class="deployment-pods">
    <div class="hierarchy-line" aria-hidden="true"></div>
    <div v-if="entry?.loading" class="pod-state"><el-icon class="is-loading"><Loading /></el-icon> 正在读取 Pods…</div>
    <div v-else-if="entry?.error" class="pod-error"><span>{{ entry.error }}</span><el-button link type="primary" data-runtime-action="retry" @click="$emit('retry')">重试</el-button></div>
    <div v-else-if="entry?.pods.length" class="pod-list">
      <article v-for="pod in entry.pods" :key="pod.name" class="pod-row">
        <div class="pod-primary"><span class="pod-dot" :class="{ healthy: pod.ready }"></span><div><button type="button" class="pod-link" data-runtime-action="pod-detail" @click="$emit('pod-detail', pod)">{{ pod.name }}</button><small>Pod</small></div></div>
        <div class="pod-field"><small>状态</small><StatusBadge :status="pod.ready ? 'Healthy' : pod.status" /></div>
        <div class="pod-field"><small>Ready</small><strong>{{ pod.ready ? 'Yes' : 'No' }}</strong></div>
        <div class="pod-field"><small>Containers</small><strong>{{ pod.containers.length }}</strong></div>
        <div class="pod-field"><small>重启</small><strong>{{ pod.restart_count }}</strong></div>
        <div class="pod-field node"><small>Node</small><span>{{ pod.node || '—' }}</span></div>
        <div class="pod-field created"><small>创建时间</small><span>{{ formatRuntimeTime(pod.created_at) }}</span></div>
      </article>
    </div>
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
.deployment-pods{position:relative;padding:14px 20px 16px 70px;background:#f7f9fd}.hierarchy-line{position:absolute;left:31px;top:0;bottom:24px;width:1px;background:#cddcf6}.hierarchy-line:after{content:"";position:absolute;left:0;bottom:0;width:22px;height:1px;background:#cddcf6}.pod-list{display:grid;gap:8px}.pod-row{display:grid;grid-template-columns:minmax(250px,2fr) 140px 72px 94px 64px minmax(130px,1fr) 170px;gap:14px;align-items:center;min-height:68px;padding:10px 14px;background:#fff;border:1px solid #e3eaf4;border-radius:10px;box-shadow:0 1px 2px rgba(30,64,175,.03)}.pod-row:hover{border-color:#c9d9f2;background:#fbfdff}.pod-primary{display:flex;align-items:center;gap:10px;min-width:0}.pod-dot{width:8px;height:8px;flex:0 0 auto;border-radius:50%;background:#f59e0b}.pod-dot.healthy{background:#22a559}.pod-primary div,.pod-field{display:grid;gap:4px;min-width:0}.pod-link{overflow:hidden;padding:0;border:0;background:none;color:#2878e8;font:inherit;font-weight:650;text-align:left;text-overflow:ellipsis;white-space:nowrap;cursor:pointer}.pod-link:hover{text-decoration:underline}.pod-primary small,.pod-field small{color:#98a2b3;font-size:10px;font-weight:650;letter-spacing:.04em;text-transform:uppercase}.pod-field strong,.pod-field span{overflow:hidden;color:#475467;font-size:12px;text-overflow:ellipsis;white-space:nowrap}.pod-state,.pod-error{display:flex;align-items:center;gap:8px;min-height:54px;color:#667085;font-size:13px}.pod-error{justify-content:space-between;padding:0 14px;border:1px solid #f6d69b;border-radius:9px;background:#fffaf0;color:#9a6700}@media(max-width:1100px){.pod-row{grid-template-columns:minmax(220px,2fr) 130px repeat(3,70px) minmax(120px,1fr)}.created{display:none}}@media(max-width:760px){.deployment-pods{padding:12px 12px 14px 36px}.hierarchy-line{left:18px}.pod-row{grid-template-columns:1fr 1fr;gap:12px}.pod-primary{grid-column:1/-1}.node,.created{display:grid}}
</style>
