<template>
  <div class="deployment-pods">
    <div class="hierarchy-line" aria-hidden="true"></div>
    <div v-if="entry?.loading" class="pod-state"><el-icon class="is-loading"><Loading /></el-icon> 正在读取 Pods…</div>
    <div v-else-if="entry?.error" class="pod-error"><span>{{ entry.error }}</span><el-button link type="primary" data-runtime-action="retry" @click="$emit('retry')">重试</el-button></div>
    <div v-else-if="entry?.pods.length" class="runtime-pod-list">
      <article v-for="pod in entry.pods" :key="pod.name" class="runtime-pod-item">
        <div class="runtime-pod-primary"><span class="runtime-pod-dot" :class="{ healthy: pod.ready }"></span><div><button type="button" class="runtime-pod-link" data-runtime-action="pod-detail" @click="$emit('pod-detail', pod)">{{ pod.name }}</button><small>Pod</small></div></div>
        <div class="runtime-pod-field"><small>状态</small><StatusBadge :status="pod.ready ? 'Healthy' : pod.status" /></div>
        <div class="runtime-pod-field"><small>Ready</small><strong>{{ pod.ready ? 'Yes' : 'No' }}</strong></div>
        <div class="runtime-pod-field"><small>Containers</small><strong>{{ pod.containers.length }}</strong></div>
        <div class="runtime-pod-field"><small>重启</small><strong>{{ pod.restart_count }}</strong></div>
        <div class="runtime-pod-field runtime-pod-node"><small>Node</small><span>{{ pod.node || '—' }}</span></div>
        <div class="runtime-pod-field runtime-pod-created"><small>创建时间</small><span>{{ formatRuntimeTime(pod.created_at) }}</span></div>
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
.deployment-pods{position:relative;padding:14px 20px 16px 70px;background:#f7f9fd}.hierarchy-line{position:absolute;left:31px;top:0;bottom:24px;width:1px;background:#b9ccef}.hierarchy-line:after{content:"";position:absolute;left:0;bottom:0;width:22px;height:1px;background:#b9ccef}.runtime-pod-list{display:grid;gap:8px}.runtime-pod-item{display:grid;grid-template-columns:minmax(0,2fr) minmax(120px,1fr) 72px 90px 64px minmax(100px,1fr) minmax(150px,1fr);gap:14px;align-items:center;min-height:68px;padding:10px 14px;background:#fff;border:1px solid #dce5f1;border-radius:10px;box-shadow:0 1px 2px rgba(30,64,175,.04)}.runtime-pod-item:hover{border-color:#b9cceb;background:#fbfdff}.runtime-pod-primary{display:flex;align-items:center;gap:10px;min-width:0}.runtime-pod-dot{width:8px;height:8px;flex:0 0 auto;border-radius:50%;background:#d97706}.runtime-pod-dot.healthy{background:#22a559}.runtime-pod-primary>div,.runtime-pod-field{display:grid;gap:4px;min-width:0}.runtime-pod-link{display:block;max-width:100%;overflow:hidden;padding:0;border:0;outline:0;background:transparent;color:#175cd3;font:inherit;font-weight:700;text-align:left;text-overflow:ellipsis;white-space:nowrap;cursor:pointer}.runtime-pod-link:hover{text-decoration:underline}.runtime-pod-primary small,.runtime-pod-field small{color:#667085;font-size:10px;font-weight:650;letter-spacing:.03em;text-transform:uppercase}.runtime-pod-field strong,.runtime-pod-field span{overflow:hidden;color:#344054;font-size:12px;font-weight:600;text-overflow:ellipsis;white-space:nowrap}.pod-state,.pod-error{display:flex;align-items:center;gap:8px;min-height:54px;color:#475467;font-size:13px}.pod-error{justify-content:space-between;padding:0 14px;border:1px solid #f6d69b;border-radius:9px;background:#fffaf0;color:#9a6700}@media(max-width:1100px){.runtime-pod-item{grid-template-columns:minmax(0,2fr) minmax(110px,1fr) repeat(3,70px) minmax(100px,1fr)}.runtime-pod-created{display:none}}@media(max-width:760px){.deployment-pods{padding:12px 12px 14px 36px}.hierarchy-line{left:18px}.runtime-pod-item{grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px}.runtime-pod-primary{grid-column:1/-1}.runtime-pod-node,.runtime-pod-created{display:grid}}
</style>
