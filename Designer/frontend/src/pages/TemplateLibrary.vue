<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { Button, Card, Tag } from '@/components/ui'
import { useTemplatesStore } from '@/stores/templates'

const router = useRouter()
const store = useTemplatesStore()
const search = ref('')

onMounted(() => store.refresh())

const grouped = computed(() => {
  const q = search.value.toLowerCase()
  const filter = (c: { name: string; display_name: string }) =>
    !q || c.name.toLowerCase().includes(q) || c.display_name.toLowerCase().includes(q)
  const map = new Map<string, typeof store.cards>()
  for (const c of store.cards) {
    if (!filter(c)) continue
    const arr = map.get(c.category) ?? []
    arr.push(c)
    map.set(c.category, arr)
  }
  return [...map.entries()]
})
</script>

<template>
  <div class="page">
    <header class="hdr">
      <h2>节点模板库</h2>
      <div class="flex gap-8">
        <input v-model="search" class="input" placeholder="搜索..." style="width: 220px" />
        <Button variant="primary" @click="router.push('/template-editor')">+ 新建节点模板</Button>
      </div>
    </header>

    <div v-if="!store.cards.length && !store.loading" class="card">
      <div class="card-body">暂无节点模板。</div>
    </div>

    <div v-for="[cat, cards] in grouped" :key="cat" class="category">
      <h3>{{ cat }} <Tag kind="outline">{{ cards.length }}</Tag></h3>
      <div class="grid">
        <Card v-for="c in cards" :key="c.id">
          <template #header>
            <span class="mono">{{ c.name }}</span>
            <Tag kind="primary">v{{ c.current_version }}</Tag>
          </template>
          <div class="dname">{{ c.display_name }}</div>
          <div class="edges">
            <Tag v-for="e in c.edge_semantics" :key="e.field" kind="outline">{{ e.field }}</Tag>
          </div>
          <div class="actions">
            <Button size="sm" @click="router.push(`/template-editor/${c.id}`)">编辑</Button>
          </div>
        </Card>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { padding: 24px; max-width: 1400px; margin: 0 auto; }
.hdr { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.hdr h2 { margin: 0; font-size: 18px; }
.category { margin-bottom: 24px; }
.category h3 { font-size: 13px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.4px; margin: 0 0 8px; display: flex; align-items: center; gap: 8px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 12px; }
.dname { font-size: 13px; color: var(--text); font-weight: 500; margin-bottom: 8px; }
.edges { display: flex; gap: 4px; flex-wrap: wrap; margin-bottom: 8px; }
.actions { display: flex; gap: 8px; }
</style>
