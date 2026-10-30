import { defineStore } from 'pinia'
import { ref } from 'vue'
import { apiFetch } from '../lib/api'
import { useAuthStore } from './auth'

// ── Types matching backend schemas ──

export type AssetType = 'object' | 'tileset'
export type CameraView = 'side_view' | 'top_down' | 'isometric'
export type JobStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface GenerationItem {
  id: string
  item_index: number
  item_description: string
  direction: string | null
  version: number
  tag: string
  edit_count: number
  redo_count: number
  original_image_url: string | null
  output_image_url: string | null
  status: string
  error_message: string | null
  created_at: string
}

export interface GenerationJob {
  id: string
  user_id: number
  name: string | null
  asset_type: AssetType
  directions: string
  camera_view: CameraView
  pixel_size: number
  global_description: string
  style_reference_url: string | null
  token_cost: number
  status: JobStatus
  created_at: string
  updated_at: string
  items: GenerationItem[]
}

export interface GenerationJobListItem {
  id: string
  name: string | null
  asset_type: AssetType
  directions: string
  camera_view: CameraView
  pixel_size: number
  global_description: string
  status: JobStatus
  token_cost: number
  created_at: string
  items: GenerationItem[]
}

export interface CreateJobPayload {
  asset_type: AssetType
  directions: string
  camera_view: CameraView
  pixel_size: number
  global_description: string
  items?: { item_index: number; item_description: string }[]
  referenceFile?: File | null
}

// ── Helpers ──

const CAMERA_MAP: Record<string, CameraView> = {
  side: 'side_view',
  'top-down': 'top_down',
  isometric: 'isometric',
}

const CAMERA_LABELS: Record<CameraView, string> = {
  side_view: 'Side View',
  top_down: 'Top-Down',
  isometric: 'Isometric',
}

const DIRECTION_MAP: Record<string, string> = {
  '1': '1 Direction',
  '4': '4 Directions',
  '8': '8 Directions',
}

export function mapCameraToApi(uiValue: string): CameraView {
  return CAMERA_MAP[uiValue] ?? 'side_view'
}

export function mapDirectionsToApi(uiValue: string): string {
  return DIRECTION_MAP[uiValue] ?? '1 Direction'
}

export function cameraLabel(view: CameraView): string {
  return CAMERA_LABELS[view] ?? view
}

export function directionsCount(directions: string): number {
  const match = directions.match(/^(\d+)/)
  return match ? parseInt(match[1]!, 10) : 1
}

// ── Store ──

export const useGenerationsStore = defineStore('generations', () => {
  const jobs = ref<GenerationJobListItem[]>([])
  const loading = ref(false)
  const generating = ref(false)
  const error = ref<string | null>(null)

  async function fetchJobs() {
    loading.value = true
    error.value = null
    try {
      jobs.value = await apiFetch<GenerationJobListItem[]>('/api/v1/generations')
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load jobs'
    } finally {
      loading.value = false
    }
  }

  async function createJob(payload: CreateJobPayload): Promise<GenerationJob | null> {
    const authStore = useAuthStore()
    generating.value = true
    error.value = null
    try {
      const formData = new FormData()
      formData.append('asset_type', payload.asset_type)
      formData.append('directions', payload.directions)
      formData.append('camera_view', payload.camera_view)
      formData.append('pixel_size', String(payload.pixel_size))
      formData.append('global_description', payload.global_description)
      formData.append('items_json', JSON.stringify(payload.items ?? []))
      if (payload.referenceFile) {
        formData.append('reference_file', payload.referenceFile)
      }

      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      const token = localStorage.getItem('access_token')
      const res = await fetch(`${API_URL}/api/v1/generations`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      })
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail ?? `API error ${res.status}`)
      }
      const job: GenerationJob = await res.json()
      authStore.fetchCurrentUser()
      // Prepend to list
      jobs.value.unshift({
        id: job.id,
        name: job.name,
        asset_type: job.asset_type,
        directions: job.directions,
        camera_view: job.camera_view,
        pixel_size: job.pixel_size,
        global_description: job.global_description,
        status: job.status,
        token_cost: job.token_cost,
        created_at: job.created_at,
        items: job.items,
      })
      return job
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Generation failed'
      return null
    } finally {
      generating.value = false
    }
  }

  async function getJob(jobId: string): Promise<GenerationJob | null> {
    try {
      return await apiFetch<GenerationJob>(`/api/v1/generations/${jobId}`)
    } catch {
      return null
    }
  }

  async function updateJob(
    jobId: string,
    data: { name?: string },
  ): Promise<GenerationJob | null> {
    try {
      const job = await apiFetch<GenerationJob>(`/api/v1/generations/${jobId}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      })
      const existing = jobs.value.find((j) => j.id === jobId)
      if (existing) {
        existing.name = job.name
      }
      return job
    } catch {
      return null
    }
  }

  function streamJob(jobId: string) {
    const token = localStorage.getItem('access_token')
    const url = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/generations/${jobId}/stream`

    const eventSource = new EventSource(`${url}?token=${token}`)

    // We can't set Authorization header with EventSource, so we use polling via fetch instead
    eventSource.close()

    const poll = async () => {
      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok || !res.body) return

      const reader = res.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const text = decoder.decode(value)
        const lines = text.split('\n')

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const data = JSON.parse(line.slice(6))

          // Update the job in the list
          const job = jobs.value.find((j) => j.id === jobId)
          if (job) {
            job.status = data.status
            if (data.items) {
              for (const updatedItem of data.items) {
                const existing = job.items.find(
                  (i) => i.item_index === updatedItem.item_index,
                )
                if (existing) {
                  if (updatedItem.output_image_url) {
                    existing.output_image_url = updatedItem.output_image_url
                  }
                  if (updatedItem.status) {
                    existing.status = updatedItem.status
                  }
                  if (updatedItem.error_message !== undefined) {
                    existing.error_message = updatedItem.error_message
                  }
                }
              }
            }
          }

          if (data.status === 'completed' || data.status === 'failed') {
            return
          }
        }
      }
    }

    poll()
  }

  async function addItem(
    jobId: string,
    itemDescription: string,
    isVariant: boolean = false,
    direction?: string,
  ): Promise<GenerationItem | null> {
    const authStore = useAuthStore()
    try {
      const item = await apiFetch<GenerationItem>(
        `/api/v1/generations/${jobId}/items`,
        {
          method: 'POST',
          body: JSON.stringify({
            item_description: itemDescription,
            is_variant: isVariant,
            direction: direction || null,
          }),
        },
      )
      authStore.fetchCurrentUser()
      return item
    } catch {
      return null
    }
  }

  async function regenerateItem(
    jobId: string,
    itemId: string,
    itemDescription?: string,
  ): Promise<GenerationItem | null> {
    const authStore = useAuthStore()
    try {
      const item = await apiFetch<GenerationItem>(
        `/api/v1/generations/${jobId}/items/${itemId}/regenerate`,
        {
          method: 'POST',
          body: JSON.stringify({ item_description: itemDescription }),
        },
      )
      authStore.fetchCurrentUser()
      return item
    } catch {
      return null
    }
  }

  async function deleteJob(jobId: string) {
    await apiFetch(`/api/v1/generations/${jobId}`, { method: 'DELETE' })
    jobs.value = jobs.value.filter((j) => j.id !== jobId)
  }

  async function deleteItem(jobId: string, itemId: string) {
    await apiFetch(`/api/v1/generations/${jobId}/items/${itemId}`, { method: 'DELETE' })
  }

  async function getAnimationUrl(jobId: string, duration: number = 200): Promise<string | null> {
    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
    const token = localStorage.getItem('access_token')
    try {
      const res = await fetch(
        `${API_URL}/api/v1/generations/${jobId}/animate?duration=${duration}`,
        { headers: token ? { Authorization: `Bearer ${token}` } : {} },
      )
      if (!res.ok) return null
      const blob = await res.blob()
      return URL.createObjectURL(blob)
    } catch {
      return null
    }
  }

  return {
    jobs,
    loading,
    generating,
    error,
    fetchJobs,
    updateJob,
    createJob,
    getJob,
    streamJob,
    addItem,
    regenerateItem,
    deleteJob,
    deleteItem,
    getAnimationUrl,
  }
})
