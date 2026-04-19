import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { metaTemplateApi, templatesApi } from '@/api'
import type { MetaTemplate, NodeTemplateCard } from '@/types'

export const useTemplatesStore = defineStore('templates', () => {
  const cards = ref<NodeTemplateCard[]>([])
  const byId = computed(() => new Map(cards.value.map((c) => [c.id, c])))
  const byName = computed(() => new Map(cards.value.map((c) => [c.name, c])))
  const meta = ref<MetaTemplate | null>(null)
  const loading = ref(false)

  async function refresh() {
    loading.value = true
    try {
      cards.value = await templatesApi.listCards()
    } finally {
      loading.value = false
    }
  }

  async function refreshMeta() {
    meta.value = await metaTemplateApi.get()
  }

  function groupedByCategory() {
    const m = new Map<string, NodeTemplateCard[]>()
    for (const c of cards.value) {
      const arr = m.get(c.category) ?? []
      arr.push(c)
      m.set(c.category, arr)
    }
    return m
  }

  return {
    cards,
    byId,
    byName,
    meta,
    loading,
    refresh,
    refreshMeta,
    groupedByCategory,
  }
})
