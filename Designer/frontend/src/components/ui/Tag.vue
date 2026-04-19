<script setup lang="ts">
defineProps<{
  kind?: 'default' | 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'violet' | 'outline'
  withDot?: boolean
}>()
</script>

<template>
  <span :class="['tag', kind ?? 'default']">
    <span v-if="withDot" class="dot" />
    <slot />
  </span>
</template>
