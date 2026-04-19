import { defineStore } from 'pinia'
import { ref } from 'vue'

import { runsApi } from '@/api'
import type { RunSummary } from '@/types'

export const useRunsStore = defineStore('runs', () => {
  const list = ref<RunSummary[]>([])
  const current = ref<RunSummary | null>(null)

  async function refresh() {
    try {
      list.value = await runsApi.list()
    } catch {
      list.value = []
    }
  }

  async function detail(id: string) {
    current.value = await runsApi.detail(id)
  }

  return { list, current, refresh, detail }
})
