<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { metaTemplateApi, templatesApi } from '@/api'
import { Button, Card, FormField, JsonEditor, Tag } from '@/components/ui'
import type { MetaTemplate, NodeTemplateDefinition, NodeTemplateOut } from '@/types'

const route = useRoute()
const router = useRouter()

const templateId = computed(() => (route.params.id as string) || null)
const meta = ref<MetaTemplate | null>(null)
const loading = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)

const form = ref({
  name: '',
  display_name: '',
  category: 'utility',
  scope: 'private' as 'global' | 'private',
  description: [''] as string[],
  input_schema: { type: 'object', properties: {} } as Record<string, unknown>,
  output_schema: { type: 'object', properties: {} } as Record<string, unknown>,
  edge_semantics: [] as Array<{ field: string; description?: string }>,
  style_hints: [] as string[],
  forbidden: [] as string[],
  example_fragment: '',
  engine: 'llm' as 'pure_python' | 'llm' | 'hybrid',
  python_impl: '' as string,
  llm_fallback: false,
  extensions: {} as Record<string, unknown>,
  change_note: 'initial',
})

onMounted(async () => {
  loading.value = true
  try {
    meta.value = await metaTemplateApi.get().catch(() => null)
    if (templateId.value) await load(templateId.value)
  } finally {
    loading.value = false
  }
})

async function load(id: string) {
  try {
    const t: NodeTemplateOut = await templatesApi.getFull(id)
    form.value.name = t.name
    form.value.display_name = t.display_name
    form.value.category = t.category
    form.value.scope = t.scope
    form.value.description = t.definition.description
    form.value.input_schema = t.definition.input_schema
    form.value.output_schema = t.definition.output_schema
    form.value.edge_semantics = t.definition.edge_semantics ?? []
    form.value.style_hints = t.definition.code_hints?.style_hints ?? []
    form.value.forbidden = t.definition.code_hints?.forbidden ?? []
    form.value.example_fragment = t.definition.code_hints?.example_fragment ?? ''
    form.value.engine = t.definition.simulator.engine
    form.value.python_impl = t.definition.simulator.python_impl ?? ''
    form.value.llm_fallback = Boolean(t.definition.simulator.llm_fallback)
    form.value.extensions = t.definition.extensions ?? {}
  } catch (e) {
    error.value = (e as Error).message
  }
}

async function save() {
  saving.value = true
  error.value = null
  try {
    const definition: NodeTemplateDefinition = {
      description: form.value.description,
      input_schema: form.value.input_schema,
      output_schema: form.value.output_schema,
      simulator: {
        engine: form.value.engine,
        python_impl: form.value.python_impl || null,
        llm_fallback: form.value.llm_fallback,
      },
      edge_semantics: form.value.edge_semantics,
      code_hints: {
        style_hints: form.value.style_hints,
        forbidden: form.value.forbidden,
        example_fragment: form.value.example_fragment,
      },
      extensions: form.value.extensions,
    }
    if (templateId.value) {
      const r = await templatesApi.update(templateId.value, {
        display_name: form.value.display_name,
        category: form.value.category,
        definition,
        change_note: form.value.change_note,
      })
      alert(`已保存,新版本号 ${r.version_number}`)
    } else {
      const api = form.value.scope === 'global' ? templatesApi.createGlobal : templatesApi.createPrivate
      const r = await api({
        name: form.value.name,
        display_name: form.value.display_name,
        category: form.value.category,
        scope: form.value.scope,
        definition,
        change_note: form.value.change_note,
      })
      alert(`已创建: ${r.template_id}`)
      router.replace(`/template-editor/${r.template_id}`)
    }
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="page">
    <header class="hdr">
      <h2>{{ templateId ? '编辑' : '新建' }} 节点模板</h2>
      <div class="flex gap-8">
        <Tag v-if="meta" kind="outline">meta v{{ meta.version }}</Tag>
        <Button variant="ghost" @click="router.back()">取消</Button>
        <Button variant="primary" :disabled="saving" @click="save">{{ saving ? '保存中...' : '保存' }}</Button>
      </div>
    </header>

    <div v-if="error" class="card" style="border-color: var(--danger)">
      <div class="card-body" style="color: var(--danger)">{{ error }}</div>
    </div>

    <div class="grid">
      <Card title="基础信息">
        <FormField label="name" required hint="^[A-Z][A-Za-z0-9_]{2,63}$">
          <input v-model="form.name" class="input" :disabled="Boolean(templateId)" placeholder="IndexTableLookup" />
        </FormField>
        <FormField label="display_name" required>
          <input v-model="form.display_name" class="input" placeholder="索引表查询" />
        </FormField>
        <FormField label="category" required>
          <input v-model="form.category" class="input" placeholder="table_ops" />
        </FormField>
        <FormField label="scope">
          <select v-model="form.scope" class="select" :disabled="Boolean(templateId)">
            <option value="private">private(设计人员,强制 llm)</option>
            <option value="global">global(admin)</option>
          </select>
        </FormField>
      </Card>

      <Card title="description(数组,一行一项)">
        <div v-for="(_, i) in form.description" :key="i" class="flex gap-8" style="margin-bottom: 6px">
          <input v-model="form.description[i]" class="input" />
          <Button size="sm" variant="ghost" @click="form.description.splice(i, 1)">-</Button>
        </div>
        <Button size="sm" @click="form.description.push('')">+ 新增</Button>
      </Card>

      <Card title="input_schema (JSON Schema)">
        <JsonEditor v-model="form.input_schema" :rows="10" />
      </Card>

      <Card title="output_schema (JSON Schema)">
        <JsonEditor v-model="form.output_schema" :rows="10" />
      </Card>

      <Card title="simulator">
        <FormField label="engine">
          <select v-model="form.engine" class="select">
            <option value="llm">llm</option>
            <option value="pure_python">pure_python</option>
            <option value="hybrid">hybrid</option>
          </select>
        </FormField>
        <FormField v-if="form.engine !== 'llm'" label="python_impl(与 tool_name 同名的 Python 类)">
          <input v-model="form.python_impl" class="input" placeholder="IndexTableLookup" />
        </FormField>
        <FormField v-if="form.engine === 'hybrid'" label="llm_fallback">
          <label><input v-model="form.llm_fallback" type="checkbox" /> 允许 LLM 兜底</label>
        </FormField>
      </Card>

      <Card title="edge_semantics">
        <div v-for="(e, i) in form.edge_semantics" :key="i" class="flex gap-8" style="margin-bottom: 6px">
          <input v-model="e.field" class="input" placeholder="field(如 next_on_hit)" style="width: 180px" />
          <input v-model="e.description" class="input" placeholder="描述" />
          <Button size="sm" variant="ghost" @click="form.edge_semantics.splice(i, 1)">-</Button>
        </div>
        <Button size="sm" @click="form.edge_semantics.push({ field: 'next', description: '' })">+ 新增</Button>
      </Card>
    </div>
  </div>
</template>

<style scoped>
.page { padding: 24px; max-width: 1100px; margin: 0 auto; }
.hdr { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.hdr h2 { margin: 0; font-size: 18px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
</style>
