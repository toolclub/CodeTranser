<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'

const navItems = [
  { to: '/graphs', label: '图列表', icon: 'grid' },
  { to: '/canvas', label: '画布', icon: 'nodes' },
  { to: '/templates', label: '节点模板', icon: 'layers' },
  { to: '/scenarios', label: '场景', icon: 'list' },
  { to: '/runs', label: '运行', icon: 'play' },
  { to: '/review', label: 'Review', icon: 'check' },
]
</script>

<template>
  <div class="app">
    <header class="topbar">
      <div class="logo"><span class="logo-mark">级</span>级跳</div>
      <div class="breadcrumb">
        <slot name="breadcrumb" />
      </div>
      <div class="spacer" />
      <div class="actions">
        <slot name="actions" />
      </div>
      <div class="user"><div class="avatar">YZ</div>开发者</div>
    </header>

    <nav class="sidebar-nav">
      <RouterLink
        v-for="n in navItems"
        :key="n.to"
        :to="n.to"
        class="nav-item"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <template v-if="n.icon === 'grid'">
            <rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" />
            <rect x="14" y="14" width="7" height="7" /><rect x="3" y="14" width="7" height="7" />
          </template>
          <template v-else-if="n.icon === 'nodes'">
            <circle cx="6" cy="6" r="3" /><circle cx="18" cy="6" r="3" />
            <circle cx="6" cy="18" r="3" /><circle cx="18" cy="18" r="3" />
            <line x1="9" y1="6" x2="15" y2="6" /><line x1="6" y1="9" x2="6" y2="15" />
            <line x1="9" y1="18" x2="15" y2="18" />
          </template>
          <template v-else-if="n.icon === 'layers'">
            <path d="M20 7L12 3L4 7L12 11L20 7Z" /><path d="M4 12L12 16L20 12" />
          </template>
          <template v-else-if="n.icon === 'list'">
            <line x1="8" y1="6" x2="21" y2="6" /><line x1="8" y1="12" x2="21" y2="12" />
            <line x1="8" y1="18" x2="21" y2="18" /><circle cx="4" cy="6" r="1" />
            <circle cx="4" cy="12" r="1" /><circle cx="4" cy="18" r="1" />
          </template>
          <template v-else-if="n.icon === 'play'">
            <polygon points="5 3 19 12 5 21 5 3" />
          </template>
          <template v-else-if="n.icon === 'check'">
            <polyline points="20 6 9 17 4 12" />
          </template>
        </svg>
        <span class="tip">{{ n.label }}</span>
      </RouterLink>
    </nav>

    <main class="main">
      <RouterView />
    </main>
  </div>
</template>
