<script setup lang="ts">
import { computed, ref, watch } from 'vue'

const props = defineProps<{
  modelValue: unknown
  rows?: number
  readonly?: boolean
}>()
const emit = defineEmits<{
  'update:modelValue': [value: unknown]
  error: [message: string | null]
}>()

const text = ref(JSON.stringify(props.modelValue, null, 2))
const errorMsg = ref<string | null>(null)

watch(
  () => props.modelValue,
  (v) => {
    const next = JSON.stringify(v, null, 2)
    if (next !== text.value) text.value = next
  },
  { deep: true },
)

function onInput(e: Event) {
  const t = (e.target as HTMLTextAreaElement).value
  text.value = t
  try {
    const parsed = JSON.parse(t)
    errorMsg.value = null
    emit('update:modelValue', parsed)
    emit('error', null)
  } catch (err) {
    errorMsg.value = (err as Error).message
    emit('error', errorMsg.value)
  }
}

const classes = computed(() => (errorMsg.value ? 'textarea invalid' : 'textarea'))
</script>

<template>
  <div>
    <textarea
      :class="classes"
      :value="text"
      :rows="rows ?? 8"
      :readonly="readonly"
      spellcheck="false"
      @input="onInput"
    />
    <div v-if="errorMsg" class="hint" style="color: var(--danger)">JSON 解析失败: {{ errorMsg }}</div>
  </div>
</template>

<style scoped>
.textarea.invalid {
  border-color: var(--danger);
  box-shadow: 0 0 0 2px var(--danger-soft);
}
</style>
