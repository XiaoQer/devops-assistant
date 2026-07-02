<template><div class="page-header"><div><span class="eyebrow">{{ eyebrow }}</span><h1>{{ title }}</h1><p v-if="description">{{ description }}</p></div><div class="page-actions"><slot/></div></div></template>
<script setup lang="ts">defineProps<{title:string;description?:string;eyebrow?:string}>()
</script>
<style scoped>.page-header{display:flex;align-items:flex-end;justify-content:space-between;margin-bottom:24px}.eyebrow{display:block;color:#766be0;font-size:12px;font-weight:700;letter-spacing:1.3px;text-transform:uppercase;margin-bottom:8px}.page-header h1{margin:0;color:var(--text);font-size:24px;line-height:1.2;letter-spacing:-.6px}.page-header p{margin:7px 0 0;color:var(--muted);font-size:13px}.page-actions{display:flex;align-items:center;gap:8px}</style>

