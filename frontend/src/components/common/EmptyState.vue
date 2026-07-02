<template>
  <div class="empty surface">
    <span>{{ icon }}</span>
    <h3>{{ title }}</h3>
    <p>{{ description }}</p>
    <slot />
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ title: string; description?: string; icon?: string }>(), {
  icon: '◇',
})
</script>

<style scoped>
.empty {
  min-height: 240px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 32px;
  box-shadow: none;
}

.empty > span {
  width: 52px;
  height: 52px;
  display: grid;
  place-items: center;
  border: 1px solid var(--border-soft);
  background: var(--primary-soft);
  border-radius: 16px;
  color: var(--primary);
  font-size: 22px;
}

.empty h3 {
  margin: 18px 0 8px;
  font-size: 18px;
  letter-spacing: -0.03em;
}

.empty p {
  max-width: 420px;
  margin: 0 0 18px;
  color: var(--muted);
  font-size: 14px;
  line-height: 1.7;
}
</style>
