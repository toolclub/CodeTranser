import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const currentGraphId = ref<string | null>(null)
  const currentUser = ref<{ id: string; name: string; isAdmin: boolean } | null>(null)
  return { currentGraphId, currentUser }
})
