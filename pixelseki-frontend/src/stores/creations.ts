import { defineStore } from 'pinia'
import { ref } from 'vue'
import { apiFetch } from '../lib/api'
import { useAuthStore } from './auth'

export type CreationCategory =
  | 'character'
  | 'background'
  | 'place'
  | 'environment'
  | 'item'
  | 'other'
export type CreationStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface DirectionOption {
  value: string
  label: string
}

export const categoryDirectionMapping: Record<CreationCategory, DirectionOption[]> = {
  character: [
    { value: 'south', label: 'South (Front View)' },
    { value: 'south-east', label: 'South East (3/4 View)' },
    { value: 'east', label: 'East (Side View Right)' },
    { value: 'north', label: 'North (Back View)' },
  ],
  background: [
    { value: 'horizontal-parallax', label: 'Horizontal Parallax Layer' },
    { value: 'isometric-skybox', label: 'Isometric Skybox View' },
    { value: 'top-down-map', label: 'Top-Down Map View' },
  ],
  place: [
    { value: 'top-down-map', label: 'Top-Down Map View (Overhead)' },
    { value: 'interior-cross-section', label: 'Interior Cross-Section' },
    { value: 'exterior-cutout', label: 'Building Exterior Structure' },
    { value: 'isometric-place', label: 'Isometric View (2.5D)' },
  ],
  environment: [
    { value: 'seamless-tile', label: 'Seamless Floor Tile (Looping)' },
    { value: 'standalone-prop', label: 'Standalone Prop (Isolated)' },
  ],
  item: [
    { value: 'flat-icon', label: 'Flat UI Icon View' },
    { value: 'angled-display', label: 'Angled Weapon Showcase' },
  ],
  other: [
    { value: 'none', label: 'Default Generic Perspective' },
  ],
}

export interface Creation {
  id: string
  user_id: number
  description: string
  category: CreationCategory
  direction: string
  width: number
  height: number
  transparent_bg: boolean
  version: number
  parent_id: string | null
  reference_image_url: string | null
  original_image_url: string | null
  output_image_url: string | null
  status: CreationStatus
  created_at: string
  updated_at: string
}

export interface CreateCreationPayload {
  description: string
  category?: CreationCategory
  direction?: string
  width?: number
  height?: number
  transparent_bg?: boolean
}

export const useCreationsStore = defineStore('creations', () => {
  const items = ref<Creation[]>([])
  const loading = ref(false)
  const generating = ref(false)
  const error = ref<string | null>(null)

  async function fetchCreations() {
    loading.value = true
    error.value = null
    try {
      items.value = await apiFetch<Creation[]>('/api/v1/creations')
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load creations'
    } finally {
      loading.value = false
    }
  }

  async function createCreation(
    payload: CreateCreationPayload,
    referenceFile?: File | null,
  ): Promise<Creation | null> {
    const authStore = useAuthStore()
    generating.value = true
    error.value = null
    try {
      const formData = new FormData()
      formData.append('description', payload.description)
      if (payload.category) formData.append('category', payload.category)
      if (payload.direction) formData.append('direction', payload.direction)
      if (payload.width != null) formData.append('width', String(payload.width))
      if (payload.height != null) formData.append('height', String(payload.height))
      if (payload.transparent_bg != null) formData.append('transparent_bg', String(payload.transparent_bg))
      if (referenceFile) formData.append('reference_image', referenceFile)

      const creation = await apiFetch<Creation>('/api/v1/creations', {
        method: 'POST',
        body: formData,
        headers: {}, // let browser set Content-Type with boundary
      })
      items.value.unshift(creation)
      authStore.fetchCurrentUser()
      return creation
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Generation failed'
      return null
    } finally {
      generating.value = false
    }
  }

  function pollCreation(creationId: string) {
    const poll = setInterval(async () => {
      try {
        const updated = await apiFetch<Creation>(`/api/v1/creations/${creationId}`)
        const idx = items.value.findIndex((c) => c.id === creationId)
        if (idx !== -1) {
          items.value[idx] = updated
        }
        if (updated.status === 'completed' || updated.status === 'failed') {
          clearInterval(poll)
        }
      } catch {
        clearInterval(poll)
      }
    }, 2000)
  }

  async function getCreation(creationId: string): Promise<Creation | null> {
    try {
      return await apiFetch<Creation>(`/api/v1/creations/${creationId}`)
    } catch {
      return null
    }
  }

  async function getVersions(creationId: string): Promise<Creation[]> {
    try {
      return await apiFetch<Creation[]>(`/api/v1/creations/${creationId}/versions`)
    } catch {
      return []
    }
  }

  async function regenerateCreation(
    creationId: string,
    description?: string,
  ): Promise<Creation | null> {
    const authStore = useAuthStore()
    try {
      const creation = await apiFetch<Creation>(
        `/api/v1/creations/${creationId}/regenerate`,
        {
          method: 'POST',
          body: JSON.stringify({ description }),
        },
      )
      items.value.unshift(creation)
      authStore.fetchCurrentUser()
      return creation
    } catch {
      return null
    }
  }

  async function deleteCreation(creationId: string) {
    await apiFetch(`/api/v1/creations/${creationId}`, { method: 'DELETE' })
    items.value = items.value.filter((c) => c.id !== creationId)
  }

  return {
    items,
    loading,
    generating,
    error,
    fetchCreations,
    createCreation,
    getCreation,
    getVersions,
    regenerateCreation,
    pollCreation,
    deleteCreation,
  }
})
