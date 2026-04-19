<script setup lang="ts">
import { RouterLink } from 'vue-router'

import { Card } from '@/components/ui'
</script>

<template>
  <div class="page">
    <h1>级跳设计平台 / Cascade</h1>
    <p class="muted">JSON 画布编辑器 + 三阶段验证。入口导航:</p>
    <div class="grid">
      <RouterLink to="/graphs"><Card title="图列表">管理你的 CascadeGraph</Card></RouterLink>
      <RouterLink to="/templates"><Card title="节点模板库">浏览/搜索/创建节点模板</Card></RouterLink>
      <RouterLink to="/runs"><Card title="Run 列表">查看触发的执行记录 + 实时 trace</Card></RouterLink>
    </div>
  </div>
</template>

<style scoped>
.page { padding: 48px; max-width: 1100px; margin: 0 auto; }
.page h1 { margin: 0 0 6px; font-size: 24px; color: var(--primary); }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; margin-top: 24px; }
.grid a { display: block; }
</style>
