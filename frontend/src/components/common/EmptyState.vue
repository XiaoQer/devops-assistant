<template><div class="empty"><span>{{ icon }}</span><h3>{{ title }}</h3><p>{{ description }}</p><slot/></div></template>
<script setup lang="ts">withDefaults(defineProps<{title:string;description?:string;icon?:string}>(),{icon:'◇'})
</script>
<style scoped>.empty{min-height:240px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:30px}.empty>span{width:46px;height:46px;display:grid;place-items:center;border:1px solid #302b4b;background:var(--primary-soft);border-radius:13px;color:#988cf1;font-size:20px}.empty h3{font-size:13px;margin:14px 0 7px}.empty p{max-width:380px;margin:0 0 16px;color:var(--muted);font-size:12px;line-height:1.6}</style>
