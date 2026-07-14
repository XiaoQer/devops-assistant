<template>
  <nav class="detail-breadcrumb" aria-label="Breadcrumb">
    <template v-for="(item, index) in items" :key="`${item.label}-${index}`">
      <span v-if="index" class="separator" aria-hidden="true">/</span>
      <RouterLink v-if="item.to && !item.current" class="crumb link" :to="item.to">
        {{ item.label }}
      </RouterLink>
      <span v-else class="crumb" :class="{ current: item.current }" :aria-current="item.current ? 'page' : undefined">
        {{ item.label }}
      </span>
    </template>
  </nav>
</template>

<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router'

export interface DetailBreadcrumbItem {
  label: string
  to?: RouteLocationRaw
  current?: boolean
}

defineProps<{ items: DetailBreadcrumbItem[] }>()
</script>

<style scoped>
.detail-breadcrumb {
  display: flex;
  align-items: center;
  min-width: 0;
  margin-bottom: 10px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.4;
}

.crumb {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.crumb.link {
  color: var(--muted);
  transition: color .15s ease;
}

.crumb.link:hover {
  color: var(--primary);
}

.crumb.current {
  max-width: 360px;
  color: var(--text-2);
  font-weight: 600;
}

.separator {
  margin: 0 9px;
  color: var(--border);
}

@media (max-width: 640px) {
  .crumb.current {
    max-width: 190px;
  }
}
</style>
