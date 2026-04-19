<script setup lang="ts">
defineProps<{ title?: string }>()
</script>

<template>
  <section class="card">
    <header v-if="title || $slots.header" class="card-header">
      <slot name="header">
        <span>{{ title }}</span>
      </slot>
      <slot name="actions" />
    </header>
    <div class="card-body">
      <slot />
    </div>
  </section>
</template>
