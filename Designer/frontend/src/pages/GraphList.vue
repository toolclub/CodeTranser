<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { graphsApi } from '@/api'
import { Button, Card, Tag } from '@/components/ui'
import type { GraphInfo } from '@/types'

const router = useRouter()
const list = ref<GraphInfo[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

onMounted(refresh)

async function refresh() {
  loading.value = true
  error.value = null
  try {
    list.value = await graphsApi.list()
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
  }
}

async function create() {
  const name = prompt('新图名称:', '未命名图')
  if (!name) return
  try {
    const { graph_id } = await graphsApi.create({ name })
    router.push(`/canvas/${graph_id}`)
  } catch (e) {
    alert('创建失败: ' + (e as Error).message)
  }
}
</script>

<template>
  <div class="page">
    <header class="hdr">
      <h2>CascadeGraph 列表</h2>
      <Button variant="primary" @click="create">+ 新建图</Button>
    </header>

    <div v-if="error" class="card"><div class="card-body" style="color: var(--danger)">{{ error }}</div></div>
    <div v-else-if="loading" class="card"><div class="card-body">加载中...</div></div>
    <div v-else-if="!list.length" class="card"><div class="card-body">暂无图,点击右上角新建。</div></div>

    <div v-else class="grid">
      <Card v-for="g in list" :key="g.id" :title="g.name">
        <template #actions>
          <Tag :kind="g.status === 'validated' ? 'success' : g.status === 'failed' ? 'danger' : 'default'">
            {{ g.status }}
          </Tag>
        </template>
        <p class="muted">{{ g.description || '(无描述)' }}</p>
        <div class="meta">
          <span class="mono">{{ g.id }}</span>
          <span v-if="g.latest_version_id" class="mono dim">latest: {{ g.latest_version_id }}</span>
        </div>
        <div class="actions">
          <Button size="sm" @click="router.push(`/canvas/${g.id}`)">打开画布</Button>
          <Button size="sm" variant="ghost" @click="router.push(`/scenarios/${g.latest_version_id}`)" :disabled="!g.latest_version_id">场景</Button>
        </div>
      </Card>
    </div>
  </div>
</template>

<style scoped>
.page { padding: 24px; max-width: 1200px; margin: 0 auto; }
.hdr { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.hdr h2 { margin: 0; font-size: 18px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 12px; }
.meta { display: flex; gap: 12px; margin: 8px 0; font-size: 11px; }
.actions { display: flex; gap: 8px; margin-top: 8px; }
</style>
