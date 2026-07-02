<template>
  <article class="metric surface">
    <div class="metric-top">
      <span>{{ title }}</span>
      <i :class="tone">{{ icon }}</i>
    </div>
    <strong>{{ value }}</strong>
    <div class="metric-foot">
      <span :class="trendClass">{{ trend || helper }}</span>
      <small v-if="trend && helper">{{ helper }}</small>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  title: string
  value: string | number
  icon?: string
  tone?: string
  trend?: string
  helper?: string
}>(), {
  icon: '◇',
  tone: 'purple',
  trend: '',
  helper: '',
})

const trendClass = computed(() => ({
  positive: props.trend.startsWith('+'),
  negative: props.trend.startsWith('-'),
}))
</script>

<style scoped>
.metric {
  padding: 18px 20px;
  box-shadow: none;
}

.metric-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  color: var(--muted);
  font-size: 13px;
  font-weight: 600;
}

.metric-top i {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: var(--primary-soft);
  color: var(--primary);
  font-style: normal;
}

.metric-top i.green {
  background: rgba(22, 163, 74, 0.10);
  color: var(--success);
}

.metric-top i.red {
  background: rgba(220, 38, 38, 0.10);
  color: var(--danger);
}

.metric-top i.blue {
  background: rgba(37, 99, 235, 0.10);
  color: var(--info);
}

strong {
  display: block;
  margin: 18px 0 10px;
  font-size: 32px;
  line-height: 1;
  letter-spacing: -0.06em;
  color: var(--text-2);
}

.metric-foot {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 18px;
  color: var(--muted);
  font-size: 12px;
}

.metric-foot span {
  font-weight: 700;
}

.metric-foot small {
  color: var(--muted);
}

.positive {
  color: var(--success);
}

.negative {
  color: var(--danger);
}
</style>
