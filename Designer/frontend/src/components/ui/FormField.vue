<script setup lang="ts">
defineProps<{
  label: string
  required?: boolean
  hint?: string
  error?: string | null
}>()
</script>

<template>
  <div class="form-row">
    <label>
      {{ label }}<span v-if="required" class="req">*</span>
    </label>
    <slot />
    <div v-if="error" class="hint" style="color: var(--danger)">{{ error }}</div>
    <div v-else-if="hint" class="hint">{{ hint }}</div>
  </div>
</template>
