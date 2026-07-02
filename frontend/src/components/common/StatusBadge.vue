<template><span class="status-badge" :class="tone"><i/>{{ label || status }}</span></template>
<script setup lang="ts">
import { computed } from 'vue'
const props=defineProps<{status?:string;label?:string}>()
const tone=computed(()=>{const s=(props.status||'Unknown').toLowerCase();if(['healthy','succeeded'].includes(s))return'success';if(['failed'].includes(s))return'danger';if(['degraded'].includes(s))return'warning';if(['running','progressing'].includes(s))return'info';return'neutral'})

</script>
<style scoped>.status-badge{display:inline-flex;align-items:center;gap:6px;min-height:26px;padding:3px 9px;border-radius:13px;font-size:12px;line-height:1;font-weight:600;color:#aab3c1;background:var(--surface-raised)}.status-badge i{width:6px;height:6px;border-radius:50%;background:#7c8595}.status-badge.success{color:#71d7aa;background:rgba(71,201,143,.12)}.status-badge.success i{background:var(--success)}.status-badge.danger{color:#f58d96;background:rgba(231,99,111,.13)}.status-badge.danger i{background:var(--danger)}.status-badge.warning{color:#f0c17a;background:rgba(230,169,80,.13)}.status-badge.warning i{background:var(--warning)}.status-badge.info{color:#8bbcff;background:rgba(92,156,242,.13)}.status-badge.info i{background:var(--info)}</style>
