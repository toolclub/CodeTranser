<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'

import { Button, Card } from '@/components/ui'

const route = useRoute()
const router = useRouter()
</script>

<template>
  <div class="page">
    <Card title="权限不足 / 资源未找到">
      <p>无法访问:<code>{{ route.fullPath }}</code></p>
      <p class="muted">后端返回 401 / 403 / 404 / 500 时跳到此页。trace_id 若在响应头里,可在开发者工具 Network 面板查看。</p>
      <div class="flex gap-8" style="margin-top: 12px">
        <Button @click="router.back()">返回</Button>
        <Button variant="primary" @click="router.push('/graphs')">回到图列表</Button>
      </div>
    </Card>
  </div>
</template>

<style scoped>
.page { padding: 48px; max-width: 600px; margin: 0 auto; }
</style>
