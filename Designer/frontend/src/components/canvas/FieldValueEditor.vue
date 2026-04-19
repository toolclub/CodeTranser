<script setup lang="ts">
/**
 * 基于 input_schema 驱动的表单编辑器。
 *
 * 支持的类型(覆盖 90% 用例,复杂的走 JSON 模式兜底):
 * - integer / number  → number input
 * - string            → text input
 * - boolean           → checkbox
 * - enum              → select
 * - array / object    → 嵌入式 JsonEditor
 * - 允许 null 的联合   → 额外加"留空 = null"开关
 */
import { computed, ref, watch } from 'vue'

import JsonEditor from '@/components/ui/JsonEditor.vue'

interface SchemaProp {
  type?: string | string[]
  enum?: unknown[]
  default?: unknown
  description?: string
  minimum?: number
  maximum?: number
}

const props = defineProps<{
  schema: Record<string, unknown>
  modelValue: Record<string, unknown>
}>()
const emit = defineEmits<{ 'update:modelValue': [value: Record<string, unknown>] }>()

const local = ref<Record<string, unknown>>({ ...props.modelValue })
watch(
  () => props.modelValue,
  (v) => {
    local.value = { ...v }
  },
  { deep: true },
)

function commit() {
  emit('update:modelValue', { ...local.value })
}

const required = computed<Set<string>>(() => new Set((props.schema.required as string[]) ?? []))

const propsList = computed<Array<[string, SchemaProp]>>(() => {
  const schemaProps = (props.schema.properties as Record<string, SchemaProp>) ?? {}
  return Object.entries(schemaProps)
})

function typeOf(p: SchemaProp): string {
  const t = p.type
  if (Array.isArray(t)) {
    const nonNull = t.filter((x) => x !== 'null')
    return nonNull[0] ?? 'string'
  }
  return (t as string) ?? 'string'
}

function allowNull(p: SchemaProp): boolean {
  return Array.isArray(p.type) && p.type.includes('null')
}
</script>

<template>
  <div class="field-editor">
    <div v-for="[key, p] in propsList" :key="key" class="field">
      <label>
        <span class="fname">{{ key }}</span>
        <span class="ftype mono">{{ typeOf(p) }}{{ allowNull(p) ? '?' : '' }}</span>
        <span v-if="required.has(key)" class="req">*</span>
      </label>
      <div v-if="p.description" class="desc">{{ p.description }}</div>
      <!-- number / integer -->
      <input
        v-if="typeOf(p) === 'integer' || typeOf(p) === 'number'"
        class="input"
        type="number"
        :step="typeOf(p) === 'integer' ? 1 : 'any'"
        :min="p.minimum"
        :max="p.maximum"
        :value="local[key] ?? ''"
        @input="
          (e) => {
            const v = (e.target as HTMLInputElement).value
            local[key] = v === '' ? null : Number(v)
            commit()
          }
        "
      />
      <!-- boolean -->
      <label v-else-if="typeOf(p) === 'boolean'" class="bool">
        <input
          type="checkbox"
          :checked="Boolean(local[key])"
          @change="
            (e) => {
              local[key] = (e.target as HTMLInputElement).checked
              commit()
            }
          "
        />
        <span>{{ Boolean(local[key]) ? 'true' : 'false' }}</span>
      </label>
      <!-- enum -->
      <select
        v-else-if="Array.isArray(p.enum)"
        class="select"
        :value="String(local[key] ?? '')"
        @change="
          (e) => {
            local[key] = (e.target as HTMLSelectElement).value
            commit()
          }
        "
      >
        <option v-for="opt in p.enum" :key="String(opt)" :value="String(opt)">
          {{ opt }}
        </option>
      </select>
      <!-- string -->
      <input
        v-else-if="typeOf(p) === 'string'"
        class="input"
        :value="String(local[key] ?? '')"
        @input="
          (e) => {
            local[key] = (e.target as HTMLInputElement).value
            commit()
          }
        "
      />
      <!-- array / object / fallback -->
      <JsonEditor
        v-else
        :modelValue="local[key]"
        :rows="4"
        @update:modelValue="(v) => { local[key] = v; commit() }"
      />
    </div>
    <div v-if="propsList.length === 0" class="empty">无字段</div>
  </div>
</template>

<style scoped>
.field-editor { display: flex; flex-direction: column; gap: 10px; }
.field { padding: 10px 12px; border: 1px solid var(--border); border-radius: 6px; background: #fff; }
.field label { display: flex; gap: 6px; align-items: center; font-size: 12px; font-weight: 600; color: var(--text-muted); }
.field .fname { color: var(--text); font-size: 13px; }
.field .ftype { font-size: 10px; padding: 1px 5px; border-radius: 3px; background: var(--surface-3); color: var(--primary); }
.field .req { color: var(--danger); }
.field .desc { font-size: 11px; color: var(--text-dim); margin: 2px 0 6px; }
.field .bool { display: flex; gap: 6px; align-items: center; font-size: 12px; }
.empty { color: var(--text-dim); font-size: 12px; text-align: center; padding: 20px; }
</style>
