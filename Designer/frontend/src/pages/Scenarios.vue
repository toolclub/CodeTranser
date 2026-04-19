<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { runsApi } from '@/api'
import { Button, Card, FormField, JsonEditor } from '@/components/ui'
import type { PipelineVariant, ScenarioInput } from '@/types'

const route = useRoute()
const router = useRouter()

const graphVersionId = ref<string>((route.params.graphVersionId as string) ?? '')
const variant = ref<PipelineVariant>('phase1_only')
const scenarios = ref<ScenarioInput[]>([
  { name: '默认场景', input_json: {}, expected_output: {}, tables: {} },
])

function addScenario() {
  scenarios.value.push({ name: `场景 ${scenarios.value.length + 1}`, input_json: {}, expected_output: {}, tables: {} })
}

async function trigger() {
  if (!graphVersionId.value) {
    alert('需要先选一个 graph_version_id')
    return
  }
  try {
    const r = await runsApi.trigger({
      graph_version_id: graphVersionId.value,
      scenarios: scenarios.value,
      options: { variant: variant.value },
    })
    router.push(`/runs/${r.run_id}`)
  } catch (e) {
    alert('触发失败(Ch10 未实装): ' + (e as Error).message)
  }
}
</script>

<template>
  <div class="page">
    <header class="hdr">
      <h2>场景 / 触发运行</h2>
      <div class="flex gap-8">
        <select v-model="variant" class="select" style="width: auto">
          <option value="phase1_only">PHASE1_ONLY · 只验证设计</option>
          <option value="up_to_phase2">UP_TO_PHASE2 · 代码预览</option>
          <option value="full">FULL · 完整三阶段</option>
        </select>
        <Button variant="primary" @click="trigger">触发运行</Button>
      </div>
    </header>

    <FormField label="graph_version_id" required>
      <input v-model="graphVersionId" class="input" placeholder="gv_xxxxxxxx" />
    </FormField>

    <div v-for="(s, i) in scenarios" :key="i">
      <Card :title="`场景 ${i + 1}`">
        <template #actions>
          <Button size="sm" variant="ghost" @click="scenarios.splice(i, 1)">删除</Button>
        </template>
        <FormField label="name" required>
          <input v-model="s.name" class="input" />
        </FormField>
        <div class="cols">
          <div>
            <label>input_json</label>
            <JsonEditor v-model="s.input_json" :rows="8" />
          </div>
          <div>
            <label>expected_output</label>
            <JsonEditor v-model="s.expected_output" :rows="8" />
          </div>
        </div>
        <FormField label="tables(按 table_name → rows[] 注入 ctx.table_data)">
          <JsonEditor v-model="s.tables" :rows="4" />
        </FormField>
        <FormField label="description(中文说明,给 LLM 看)">
          <textarea v-model="s.description" class="textarea" rows="2" style="font-family: inherit" />
        </FormField>
      </Card>
    </div>
    <Button @click="addScenario">+ 新增场景</Button>
  </div>
</template>

<style scoped>
.page { padding: 24px; max-width: 1100px; margin: 0 auto; }
.hdr { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.hdr h2 { margin: 0; font-size: 18px; }
.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
label { font-size: 12px; font-weight: 500; color: var(--text-muted); display: block; margin-bottom: 4px; }
</style>
