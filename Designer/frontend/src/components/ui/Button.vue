<script setup lang="ts">
defineProps<{
  variant?: 'default' | 'primary' | 'ghost' | 'danger'
  size?: 'sm' | 'default' | 'lg'
  disabled?: boolean
  title?: string
}>()
</script>

<template>
  <button
    :class="['btn', variant ?? 'default', size]"
    :disabled="disabled"
    :title="title"
  >
    <slot />
  </button>
</template>
