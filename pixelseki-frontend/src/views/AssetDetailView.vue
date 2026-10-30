<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  useGenerationsStore,
  cameraLabel,
  directionsCount,
  type GenerationJob,
} from '../stores/generations'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const route = useRoute()
const router = useRouter()
const store = useGenerationsStore()

const job = ref<GenerationJob | null>(null)
const loading = ref(true)

onMounted(async () => {
  const id = route.params.id as string
  job.value = await store.getJob(id)
  loading.value = false
})

function imageUrl(path: string | null): string {
  if (!path) return ''
  if (path.startsWith('http')) return path
  return `${API_URL}${path}`
}

// ── Active preview ──
const selectedItemIdx = ref(0)

// ── Edit name ──
const isEditingName = ref(false)
const editName = ref('')

function displayName(): string {
  if (!job.value) return ''
  return job.value.name || job.value.global_description
}

function startEditName() {
  if (!job.value) return
  editName.value = displayName()
  isEditingName.value = true
}

async function saveName() {
  if (!job.value || !editName.value.trim()) return
  isEditingName.value = false
  const updated = await store.updateJob(job.value.id, { name: editName.value.trim() })
  if (updated) job.value = updated
}

// ── Computed helpers ──
const isObject = computed(() => job.value?.asset_type === 'object')
const dirCount = computed(() => (job.value ? directionsCount(job.value.directions) : 1))

// ── Download single item ──
async function downloadItem(path: string | null, filename: string) {
  if (!path) return
  const fullUrl = `${API_URL}${path}`
  const res = await fetch(fullUrl, { mode: 'cors' })
  if (!res.ok) return
  const blob = await res.blob()
  const blobUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = blobUrl
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(blobUrl)
}

// ── Selected item helper ──
const selectedItem = computed(() => job.value?.items[selectedItemIdx.value] ?? null)

// ── Edit item description + regenerate ──
const editingItemId = ref<string | null>(null)
const editItemDescription = ref('')
const regenerating = ref<string | null>(null)

function startEditItem(itemId: string, currentDescription: string) {
  editingItemId.value = itemId
  editItemDescription.value = currentDescription
}

function cancelEditItem() {
  editingItemId.value = null
  editItemDescription.value = ''
}

const MAX_EDITS = 2
const MAX_REDOS = 2

// ── Add new item ──
const showAddItem = ref(false)
const addItemDescription = ref('')
const addItemDirection = ref('')
const addItemMode = ref<'direction' | 'variant'>('direction')
const addingItem = ref(false)

const DIRECTION_OPTIONS = [
  { value: 'south', label: 'South (Front)' },
  { value: 'south_east', label: 'South-East (3/4 Front-Right)' },
  { value: 'east', label: 'East (Right Profile)' },
  { value: 'north_east', label: 'North-East (3/4 Back-Right)' },
  { value: 'north', label: 'North (Back)' },
  { value: 'north_west', label: 'North-West (3/4 Back-Left)' },
  { value: 'west', label: 'West (Left Profile)' },
  { value: 'south_west', label: 'South-West (3/4 Front-Left)' },
  { value: 'top', label: "Top (Bird's Eye)" },
  { value: 'bottom', label: "Bottom (Worm's Eye)" },
  { value: 'custom', label: 'Custom...' },
]

function buildAddDescription(): string {
  if (!job.value) return ''
  const base = job.value.global_description

  if (isObject.value) {
    if (addItemMode.value === 'variant') {
      // Variant: standalone description (not appended to base)
      const desc = addItemDescription.value.trim()
      return desc || ''
    }

    // Direction mode
    if (addItemDirection.value === 'custom') {
      return addItemDescription.value.trim() ? `${base} — ${addItemDescription.value.trim()}` : ''
    }
    const extra = addItemDescription.value.trim()
    return extra
      ? `${base} — facing ${addItemDirection.value}, ${extra}`
      : `${base} — facing ${addItemDirection.value}`
  }

  return addItemDescription.value.trim()
}

function openAddItem() {
  showAddItem.value = true
  addItemMode.value = 'direction'
  addItemDirection.value = ''
  addItemDescription.value = ''
}

function cancelAddItem() {
  showAddItem.value = false
  addItemMode.value = 'direction'
  addItemDirection.value = ''
  addItemDescription.value = ''
}

// ── Animation ──
const showAnimation = ref(false)
const animationUrl = ref<string | null>(null)
const animationLoading = ref(false)
const animationSpeed = ref(200)

async function openAnimation() {
  if (!job.value) return
  animationLoading.value = true
  showAnimation.value = true
  animationUrl.value = null
  const url = await store.getAnimationUrl(job.value.id, animationSpeed.value)
  animationUrl.value = url
  animationLoading.value = false
}

async function updateAnimationSpeed() {
  if (!job.value || !showAnimation.value) return
  animationLoading.value = true
  if (animationUrl.value) {
    URL.revokeObjectURL(animationUrl.value)
  }
  const url = await store.getAnimationUrl(job.value.id, animationSpeed.value)
  animationUrl.value = url
  animationLoading.value = false
}

function closeAnimation() {
  showAnimation.value = false
  if (animationUrl.value) {
    URL.revokeObjectURL(animationUrl.value)
    animationUrl.value = null
  }
}

function downloadAnimation() {
  if (!animationUrl.value || !job.value) return
  const name = job.value.name || job.value.global_description.slice(0, 30)
  const safe = name.replace(/[^a-zA-Z0-9 _-]/g, '_').trim()
  const a = document.createElement('a')
  a.href = animationUrl.value
  a.download = `${safe}_animation.gif`
  document.body.appendChild(a)
  a.click()
  a.remove()
}

const canSubmitAdd = computed(() => {
  if (isObject.value) {
    if (addItemMode.value === 'variant') {
      return !!addItemDescription.value.trim()
    }
    if (!addItemDirection.value) return false
    if (addItemDirection.value === 'custom' && !addItemDescription.value.trim()) return false
    return true
  }
  return !!addItemDescription.value.trim()
})

async function handleAddItem() {
  if (!job.value) return
  const desc = buildAddDescription()
  if (!desc) return

  addingItem.value = true
  showAddItem.value = false

  const isVariant = addItemMode.value === 'variant'
  let direction: string | undefined
  if (!isVariant && addItemDirection.value) {
    if (addItemDirection.value === 'custom') {
      direction = addItemDescription.value.trim() || undefined
    } else {
      direction = addItemDirection.value
    }
  }
  const newItem = await store.addItem(job.value.id, desc, isVariant, direction)
  addItemDescription.value = ''
  addItemDirection.value = ''
  addItemMode.value = 'direction'

  if (!newItem) {
    addingItem.value = false
    return
  }

  job.value.items.push(newItem)

  const poll = setInterval(async () => {
    if (!job.value) return
    const updated = await store.getJob(job.value.id)
    if (!updated) return
    const found = updated.items.find((i) => i.id === newItem.id)
    if (found?.status === 'completed' || found?.status === 'failed') {
      job.value = updated
      addingItem.value = false
      clearInterval(poll)
    }
  }, 2000)
}

// ── Download ZIP ──
const downloading = ref(false)

async function downloadZip() {
  if (!job.value) return
  downloading.value = true

  try {
    const token = localStorage.getItem('access_token')
    const res = await fetch(`${API_URL}/api/v1/generations/${job.value.id}/download`, {
      headers: { Authorization: `Bearer ${token}` },
    })

    if (!res.ok) throw new Error('Download failed')

    const blob = await res.blob()
    const url = URL.createObjectURL(blob)

    const a = document.createElement('a')
    a.href = url
    a.download =
      res.headers.get('content-disposition')?.match(/filename="(.+)"/)?.[1] ?? 'assets.zip'
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } finally {
    downloading.value = false
  }
}

function canEdit(item: { edit_count: number }): boolean {
  return item.edit_count < MAX_EDITS
}

function canRedo(item: { redo_count: number }): boolean {
  return item.redo_count < MAX_REDOS
}

async function saveAndRegenerate(itemId: string) {
  if (!job.value || !editItemDescription.value.trim()) return

  const newDesc = editItemDescription.value.trim()
  editingItemId.value = null

  const newItem = await store.regenerateItem(job.value.id, itemId, newDesc)
  if (!newItem) return

  regenerating.value = newItem.id

  // Poll until the new item completes or fails
  const poll = setInterval(async () => {
    if (!job.value) return
    const updated = await store.getJob(job.value.id)
    if (!updated) return
    const found = updated.items.find((i) => i.id === newItem.id)
    if (found?.status === 'completed' || found?.status === 'failed') {
      job.value = updated
      regenerating.value = null
      clearInterval(poll)
    }
  }, 2000)
}

async function regenerateWithoutEdit(itemId: string) {
  if (!job.value) return

  const newItem = await store.regenerateItem(job.value.id, itemId)
  if (!newItem) return

  regenerating.value = newItem.id

  const poll = setInterval(async () => {
    if (!job.value) return
    const updated = await store.getJob(job.value.id)
    if (!updated) return
    const found = updated.items.find((i) => i.id === newItem.id)
    if (found?.status === 'completed' || found?.status === 'failed') {
      job.value = updated
      regenerating.value = null
      clearInterval(poll)
    }
  }, 2000)
}

// ── Retry failed item ──
async function retryItem(itemId: string) {
  if (!job.value || regenerating.value) return

  regenerating.value = itemId

  const newItem = await store.regenerateItem(job.value.id, itemId)
  if (!newItem) {
    regenerating.value = null
    return
  }

  regenerating.value = newItem.id

  const poll = setInterval(async () => {
    if (!job.value) return
    const updated = await store.getJob(job.value.id)
    if (!updated) return
    const found = updated.items.find((i) => i.id === newItem.id)
    if (found?.status === 'completed' || found?.status === 'failed') {
      job.value = updated
      regenerating.value = null
      clearInterval(poll)
    }
  }, 2000)
}

// ── Delete ──
async function handleDeleteJob() {
  if (!job.value) return
  await store.deleteJob(job.value.id)
  router.push('/objects')
}

async function handleDeleteItem(itemId: string) {
  if (!job.value) return
  await store.deleteItem(job.value.id, itemId)
  job.value = await store.getJob(job.value.id)
  // Reset selected index if it's now out of bounds
  if (job.value && selectedItemIdx.value >= job.value.items.length) {
    selectedItemIdx.value = Math.max(0, job.value.items.length - 1)
  }
}
</script>

<template>
  <div class="min-h-screen w-full bg-game-dark text-slate-200">
    <!-- App Bar -->
    <header
      class="sticky top-0 z-40 w-full border-b border-white/5 bg-game-dark/95 backdrop-blur-md"
    >
      <div class="mx-auto flex max-w-5xl items-center justify-between px-4 py-2.5 md:px-8">
        <div class="flex items-center gap-4 min-w-0">
          <RouterLink
            to="/objects"
            class="font-sans text-xs text-slate-500 hover:text-white transition-none no-underline flex items-center gap-1.5 flex-shrink-0"
          >
            <svg
              class="w-3.5 h-3.5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
            >
              <path d="M15 19l-7-7 7-7" />
            </svg>
            Objects
          </RouterLink>
          <span class="w-px h-4 bg-white/10 flex-shrink-0"></span>
          <h1 class="font-sans text-sm font-medium text-white truncate">
            {{ job ? displayName() : 'Loading...' }}
          </h1>
        </div>
        <div v-if="job" class="flex items-center gap-2 flex-shrink-0">
          <button
            v-if="job.status === 'completed'"
            class="flex items-center gap-1.5 px-4 py-1.5 rounded-lg font-sans text-xs font-semibold text-white bg-game-accent hover:bg-game-accent/90 transition-none"
            :disabled="downloading"
            @click="downloadZip"
          >
            <svg
              v-if="!downloading"
              class="w-3.5 h-3.5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
            >
              <path
                d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3"
              />
            </svg>
            <svg
              v-else
              class="w-3.5 h-3.5 animate-spin"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                d="M12 2v4m0 12v4m-7.07-3.93l2.83-2.83m8.48-8.48l2.83-2.83M2 12h4m12 0h4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83"
              />
            </svg>
            {{ downloading ? 'Zipping...' : 'Download ZIP' }}
          </button>
          <button
            v-if="job.status === 'completed' && job.items.length > 1"
            class="flex items-center gap-1.5 px-4 py-1.5 rounded-lg font-sans text-xs font-semibold text-game-dark bg-game-gold hover:bg-game-gold/90 transition-none"
            @click="openAnimation"
          >
            <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <polygon points="5 3 19 12 5 21 5 3" />
            </svg>
            Animate
          </button>
          <button
            class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-sans text-xs font-medium text-slate-400 hover:text-red-400 border border-white/10 hover:border-red-400/30 hover:bg-red-400/5 transition-none"
            @click="handleDeleteJob"
          >
            <svg
              class="w-3.5 h-3.5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
              />
            </svg>
            Delete
          </button>
        </div>
      </div>
    </header>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-32">
      <p class="font-sans text-sm text-slate-500">Loading...</p>
    </div>

    <!-- Not Found -->
    <div v-else-if="!job" class="flex flex-col items-center justify-center py-32 text-center">
      <p class="font-sans text-lg text-slate-400 mb-2">Asset not found</p>
      <RouterLink
        to="/objects"
        class="font-sans text-sm text-game-accent hover:underline transition-none no-underline"
        >Back to objects</RouterLink
      >
    </div>

    <!-- ════════════════════════════════════ -->
    <!-- OBJECT DETAIL                        -->
    <!-- ════════════════════════════════════ -->
    <main v-else-if="isObject" class="mx-auto max-w-5xl px-4 pt-6 pb-12 md:px-8 md:pt-8">
      <!-- Top: Preview + Info -->
      <div class="rounded-2xl border border-white/10 bg-white/[0.02] overflow-hidden mb-8">
        <div class="flex flex-col md:flex-row">
          <!-- Left: Large preview -->
          <div
            class="checkerboard-bg w-full md:w-[320px] min-h-[280px] flex items-center justify-center p-8 flex-shrink-0 relative"
          >
            <span
              class="absolute top-3 left-3 flex items-center gap-1.5 px-2.5 py-1 rounded-lg font-sans text-[10px] font-medium"
              :class="{
                'bg-game-success/15 text-game-success': job.status === 'completed',
                'bg-game-gold/15 text-game-gold': job.status === 'processing',
                'bg-red-500/15 text-red-400': job.status === 'failed',
                'bg-white/10 text-slate-400': job.status === 'pending',
              }"
            >
              <span
                class="w-1.5 h-1.5 rounded-full"
                :class="{
                  'bg-game-success': job.status === 'completed',
                  'bg-game-gold': job.status === 'processing',
                  'bg-red-400': job.status === 'failed',
                  'bg-slate-400': job.status === 'pending',
                }"
              ></span>
              {{ job.status }}
            </span>
            <!-- Generated image or placeholder -->
            <img
              v-if="selectedItem?.output_image_url"
              :src="imageUrl(selectedItem.output_image_url)"
              alt=""
              class="max-w-full max-h-[220px] object-contain image-rendering-pixelated"
              @error="($event.target as HTMLImageElement).style.display = 'none'"
            />
            <div
              v-else
              class="border-2 border-white/10 rounded-lg bg-game-dark/50 flex items-center justify-center"
              :style="{
                width: `${Math.min(job.pixel_size * 2, 160)}px`,
                height: `${Math.min(job.pixel_size * 2, 160)}px`,
              }"
            >
              <span class="font-mono text-sm text-slate-600">{{ job.pixel_size }}px</span>
            </div>
          </div>

          <!-- Right: Info -->
          <div class="flex-1 p-6 md:p-8 border-t md:border-t-0 md:border-l border-white/5">
            <!-- Name -->
            <div class="flex items-center gap-2 mb-2">
              <svg
                class="w-5 h-5 text-game-accent flex-shrink-0"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.5"
              >
                <path
                  d="m21 7.5-9-5.25L3 7.5m18 0-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25"
                />
              </svg>
              <template v-if="!isEditingName">
                <h2 class="font-sans text-xl font-semibold text-white">{{ displayName() }}</h2>
                <button
                  class="text-slate-500 hover:text-white transition-none p-0.5"
                  @click="startEditName"
                >
                  <svg
                    class="w-4 h-4"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                  >
                    <path
                      d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Z"
                    />
                  </svg>
                </button>
              </template>
              <template v-else>
                <input
                  v-model="editName"
                  class="flex-1 font-sans text-xl font-semibold text-white bg-transparent border-b-2 border-game-accent focus:outline-none py-0.5"
                  @keydown.enter="saveName"
                  @blur="saveName"
                />
              </template>
            </div>

            <!-- Prompt -->
            <p class="font-sans text-sm text-slate-500 mb-4">"{{ job.global_description }}"</p>

            <!-- Meta bar -->
            <div class="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
              <!-- Size -->
              <span class="flex items-center gap-1.5 text-slate-400">
                <svg
                  class="w-3.5 h-3.5"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path
                    d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15"
                  />
                </svg>
                <span class="font-mono">{{ job.pixel_size }}&times;{{ job.pixel_size }}px</span>
              </span>

              <span class="w-px h-4 bg-white/10"></span>

              <!-- Directions -->
              <span class="flex items-center gap-1.5 text-slate-400">
                <svg
                  class="w-3.5 h-3.5"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path
                    d="M7.5 3.75H6A2.25 2.25 0 003.75 6v1.5M16.5 3.75H18A2.25 2.25 0 0120.25 6v1.5m0 9V18A2.25 2.25 0 0118 20.25h-1.5m-9 0H6A2.25 2.25 0 013.75 18v-1.5"
                  />
                </svg>
                {{ dirCount }} direction{{ dirCount > 1 ? 's' : '' }}
              </span>

              <span class="w-px h-4 bg-white/10"></span>

              <!-- Camera view -->
              <span class="flex items-center gap-1.5 text-slate-400">
                <svg
                  class="w-3.5 h-3.5"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path
                    d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178Z"
                  />
                  <path d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
                </svg>
                {{ cameraLabel(job.camera_view) }}
              </span>

              <span class="w-px h-4 bg-white/10"></span>

              <!-- Created -->
              <span class="text-slate-500 font-sans text-xs">
                {{ new Date(job.created_at).toLocaleString() }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Directions Section -->
      <section class="mb-8">
        <div class="flex items-center gap-3 mb-4">
          <svg
            class="w-5 h-5 text-game-accent"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <rect x="3" y="3" width="7" height="7" />
            <rect x="14" y="3" width="7" height="7" />
            <rect x="3" y="14" width="7" height="7" />
            <rect x="14" y="14" width="7" height="7" />
          </svg>
          <h3 class="font-sans text-lg font-semibold text-white">Directions/Variants</h3>
          <span class="px-2 py-0.5 rounded-md bg-white/5 font-sans text-xs text-slate-400">{{
            job.items.length
          }}</span>
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div
            v-for="(item, idx) in job.items"
            :key="item.id"
            class="rounded-xl border-2 overflow-hidden transition-none"
            :class="
              idx === selectedItemIdx
                ? 'border-game-accent shadow-glow-accent'
                : 'border-white/10 hover:border-white/20'
            "
          >
            <!-- Preview — click to select -->
            <button
              class="checkerboard-bg h-28 w-full flex items-center justify-center"
              @click="selectedItemIdx = idx"
            >
              <img
                v-if="item.output_image_url && regenerating !== item.id"
                :src="imageUrl(item.output_image_url)"
                alt=""
                class="max-w-full max-h-full object-contain image-rendering-pixelated p-1"
                @error="($event.target as HTMLImageElement).style.display = 'none'"
              />
              <img
                v-else-if="regenerating === item.id"
                src="/assets/loading.webp"
                alt="Regenerating..."
                class="w-12 h-12 animate-spin"
              />
              <div
                v-else-if="item.status === 'failed'"
                class="flex flex-col items-center justify-center gap-1 p-2"
              >
                <svg
                  class="w-6 h-6 text-red-400/60"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.5"
                >
                  <path
                    d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z"
                  />
                </svg>
                <span class="font-sans text-[9px] text-red-400/80 text-center line-clamp-2">{{
                  item.error_message || 'Failed'
                }}</span>
              </div>
              <div
                v-else
                class="border border-white/10 rounded bg-game-dark/50 flex items-center justify-center"
                :style="{
                  width: `${Math.min(job.pixel_size, 48)}px`,
                  height: `${Math.min(job.pixel_size, 48)}px`,
                }"
              >
                <span class="font-mono text-[9px] text-slate-600">{{ idx + 1 }}</span>
              </div>
            </button>

            <!-- Error message below preview -->
            <div
              v-if="item.status === 'failed' && item.error_message"
              class="px-2 py-1.5 bg-red-500/5 border-t border-red-500/10"
            >
              <p class="font-sans text-[10px] text-red-400 line-clamp-2">
                {{ item.error_message }}
              </p>
            </div>

            <!-- Footer: description + actions -->
            <div class="px-3 py-2.5 bg-game-dark/80">
              <!-- Editing mode -->
              <template v-if="editingItemId === item.id">
                <textarea
                  v-model="editItemDescription"
                  rows="2"
                  class="w-full px-2 py-1.5 rounded-lg bg-white/5 border border-white/10 font-sans text-[11px] text-white placeholder-slate-600 focus:outline-none focus:border-game-accent/60 resize-none mb-2"
                ></textarea>
                <div class="flex items-center gap-1.5">
                  <button
                    class="flex-1 flex items-center justify-center gap-1 px-2 py-1 rounded-lg font-sans text-[10px] font-medium text-white bg-game-accent hover:bg-game-accent/90 transition-none"
                    @click="saveAndRegenerate(item.id)"
                  >
                    <svg
                      class="w-3 h-3"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <path
                        d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09Z"
                      />
                    </svg>
                    Regenerate
                  </button>
                  <button
                    class="px-2 py-1 rounded-lg font-sans text-[10px] text-slate-400 hover:text-white border border-white/10 transition-none"
                    @click="cancelEditItem"
                  >
                    Cancel
                  </button>
                </div>
              </template>

              <!-- Display mode -->
              <template v-else>
                <!-- Version tag -->
                <div class="flex items-center gap-1.5 mb-1">
                  <span
                    class="px-1.5 py-0.5 rounded font-mono text-[9px] font-medium"
                    :class="
                      item.tag === 'original'
                        ? 'bg-game-accent/15 text-game-accent'
                        : 'bg-game-gold/15 text-game-gold'
                    "
                    >{{ item.tag }}</span
                  >
                </div>
                <p class="font-sans text-[11px] text-slate-300 truncate mb-1.5">
                  {{ item.item_description.split(' — ').pop() }}
                </p>
                <div class="flex items-center gap-1.5">
                  <button
                    v-if="item.output_image_url"
                    class="flex items-center gap-1 px-2 py-0.5 rounded-md font-sans text-[10px] text-slate-500 hover:text-white hover:bg-white/5 transition-none"
                    @click="
                      downloadItem(
                        item.output_image_url,
                        `${item.item_description.replace(/[^a-zA-Z0-9]/g, '_')}.png`,
                      )
                    "
                  >
                    <svg
                      class="w-3 h-3"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <path
                        d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3"
                      />
                    </svg>
                  </button>
                  <button
                    class="flex items-center gap-1 px-2 py-0.5 rounded-md font-sans text-[10px] transition-none"
                    :class="
                      canEdit(item)
                        ? 'text-slate-500 hover:text-white hover:bg-white/5'
                        : 'text-slate-700 cursor-not-allowed'
                    "
                    :disabled="!canEdit(item) || regenerating === item.id"
                    @click="startEditItem(item.id, item.item_description)"
                  >
                    <svg
                      class="w-3 h-3"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <path
                        d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Z"
                      />
                    </svg>
                    Edit {{ item.edit_count }}/{{ MAX_EDITS }}
                  </button>
                  <button
                    v-if="item.status === 'failed' && regenerating !== item.id"
                    class="flex items-center gap-1 px-2 py-0.5 rounded-md font-sans text-[10px] text-amber-500 hover:text-amber-400 hover:bg-amber-400/5 transition-none"
                    @click="retryItem(item.id)"
                  >
                    <svg
                      class="w-3 h-3"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <path
                        d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182M20.995 4.365v4.99"
                      />
                    </svg>
                    Retry
                  </button>
                  <button
                    class="flex items-center gap-1 px-2 py-0.5 rounded-md font-sans text-[10px] text-slate-600 hover:text-red-400 hover:bg-red-400/5 transition-none"
                    @click="handleDeleteItem(item.id)"
                    v-if="job.items.length > 1 && regenerating !== item.id"
                  >
                    <svg
                      class="w-3 h-3"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <path
                        d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
                      />
                    </svg>
                  </button>
                </div>
              </template>
            </div>
          </div>

          <!-- Add new direction card -->
          <div
            class="rounded-xl border-2 border-dashed overflow-hidden transition-none"
            :class="showAddItem ? 'border-game-accent/40' : 'border-white/10 hover:border-white/20'"
          >
            <!-- Adding in progress: show loader -->
            <template v-if="addingItem">
              <div class="flex flex-col items-center justify-center gap-2 min-h-[168px]">
                <img
                  src="/assets/loading.webp"
                  alt="Generating..."
                  class="w-12 h-12 animate-spin"
                />
                <p class="font-sans text-[11px] text-slate-400">Generating...</p>
              </div>
            </template>

            <!-- Add form -->
            <template v-else-if="showAddItem">
              <div class="p-3 bg-game-dark/80 h-full flex flex-col justify-center">
                <!-- Mode toggle: Direction / Variant -->
                <div class="flex rounded-lg border border-white/10 overflow-hidden mb-2">
                  <button
                    class="flex-1 px-2 py-1.5 font-sans text-[10px] font-medium transition-none"
                    :class="
                      addItemMode === 'direction'
                        ? 'bg-game-accent/15 text-game-accent'
                        : 'text-slate-400 hover:text-white'
                    "
                    @click="
                      addItemMode = 'direction';
                      addItemDirection = '';
                      addItemDescription = '';
                    "
                  >
                    Direction
                  </button>
                  <button
                    class="flex-1 px-2 py-1.5 font-sans text-[10px] font-medium border-l border-white/10 transition-none"
                    :class="
                      addItemMode === 'variant'
                        ? 'bg-game-gold/15 text-game-gold'
                        : 'text-slate-400 hover:text-white'
                    "
                    @click="
                      addItemMode = 'variant';
                      addItemDirection = '';
                      addItemDescription = '';
                    "
                  >
                    Variant
                  </button>
                </div>

                <!-- Direction mode: direction picker -->
                <template v-if="addItemMode === 'direction'">
                  <span
                    class="font-sans text-[10px] font-medium text-slate-400 uppercase tracking-wider mb-1"
                    >Direction</span
                  >
                  <div class="flex flex-wrap gap-1 mb-2">
                    <button
                      v-for="opt in DIRECTION_OPTIONS"
                      :key="opt.value"
                      class="px-2 py-1 rounded-md font-sans text-[10px] font-medium border transition-none"
                      :class="
                        addItemDirection === opt.value
                          ? 'bg-game-accent/15 border-game-accent/40 text-game-accent'
                          : 'bg-white/5 border-white/5 text-slate-400 hover:text-white hover:border-white/10'
                      "
                      @click="addItemDirection = opt.value"
                    >
                      {{ opt.label }}
                    </button>
                  </div>
                  <textarea
                    v-if="addItemDirection"
                    v-model="addItemDescription"
                    rows="2"
                    :placeholder="
                      addItemDirection === 'custom'
                        ? 'Describe the custom direction...'
                        : 'Additional details (optional)...'
                    "
                    class="w-full px-2 py-1.5 rounded-lg bg-white/5 border border-white/10 font-sans text-[11px] text-white placeholder-slate-600 focus:outline-none focus:border-game-accent/60 resize-none mb-2"
                  ></textarea>
                </template>

                <!-- Variant mode: description only -->
                <template v-else>
                  <span
                    class="font-sans text-[10px] font-medium text-slate-400 uppercase tracking-wider mb-1"
                    >What's different?</span
                  >
                  <textarea
                    v-model="addItemDescription"
                    rows="2"
                    placeholder="e.g. with a red cape, holding a shield, angry expression..."
                    class="w-full px-2 py-1.5 rounded-lg bg-white/5 border border-white/10 font-sans text-[11px] text-white placeholder-slate-600 focus:outline-none focus:border-game-gold/60 resize-none mb-2"
                  ></textarea>
                </template>

                <div class="flex items-center gap-1.5">
                  <button
                    class="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded-lg font-sans text-[10px] font-medium text-white transition-none"
                    :class="
                      canSubmitAdd
                        ? addItemMode === 'variant'
                          ? 'bg-game-gold hover:bg-game-gold/90'
                          : 'bg-game-accent hover:bg-game-accent/90'
                        : addItemMode === 'variant'
                          ? 'bg-game-gold/30 cursor-not-allowed'
                          : 'bg-game-accent/30 cursor-not-allowed'
                    "
                    :disabled="!canSubmitAdd"
                    @click="handleAddItem"
                  >
                    <svg
                      class="w-3 h-3"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <path
                        d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09Z"
                      />
                    </svg>
                    Generate
                  </button>
                  <button
                    class="px-2 py-1.5 rounded-lg font-sans text-[10px] text-slate-400 hover:text-white border border-white/10 transition-none"
                    @click="cancelAddItem"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </template>

            <!-- Default: + button -->
            <template v-else>
              <button
                class="w-full h-full min-h-[168px] flex flex-col items-center justify-center gap-2"
                @click="openAddItem"
              >
                <svg
                  class="w-6 h-6 text-slate-600"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.5"
                >
                  <path d="M12 4.5v15m7.5-7.5h-15" />
                </svg>
                <span class="font-sans text-[11px] text-slate-600">Add direction / variant</span>
              </button>
            </template>
          </div>
        </div>
      </section>

      <!-- Animations Section (placeholder — future feature) -->
      <!-- <section>
        <div class="flex items-center gap-3 mb-4">
          <svg class="w-5 h-5 text-game-sakura" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 0 1-1.125-1.125M3.375 19.5h1.5C5.496 19.5 6 18.996 6 18.375m-2.625 0V5.625m0 12.75v-12.75m0 0A1.125 1.125 0 0 1 4.5 4.5h15a1.125 1.125 0 0 1 1.125 1.125m-17.25 0h17.25m0 0v12.75M20.625 5.625v12.75m0 0a1.125 1.125 0 0 1-1.125 1.125m1.125-1.125h-1.5a.625.625 0 0 1-.625-.625" />
          </svg>
          <h3 class="font-sans text-lg font-semibold text-white">Animations</h3>
          <span class="px-2 py-0.5 rounded-md bg-white/5 font-sans text-xs text-slate-400">0</span>
        </div>

        <div class="px-4 py-6 rounded-xl border border-dashed border-white/10 text-center mb-4">
          <p class="font-sans text-sm text-slate-500">No animations yet</p>
        </div>
        <button
          class="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-dashed border-white/10 hover:border-white/20 font-sans text-sm text-slate-400 hover:text-white transition-none"
        >
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          Add Animation
        </button>
      </section> -->
    </main>

    <!-- ════════════════════════════════════ -->
    <!-- TILESET DETAIL                       -->
    <!-- ════════════════════════════════════ -->
    <main v-else class="mx-auto max-w-5xl px-4 pt-6 pb-12 md:px-8 md:pt-8">
      <!-- Top: Preview + Info -->
      <div class="rounded-2xl border border-white/10 bg-white/[0.02] overflow-hidden mb-8">
        <div class="flex flex-col md:flex-row">
          <!-- Left: Grid preview -->
          <div
            class="checkerboard-bg w-full md:w-[320px] min-h-[280px] flex items-center justify-center p-8 flex-shrink-0 relative"
          >
            <span
              class="absolute top-3 left-3 flex items-center gap-1.5 px-2.5 py-1 rounded-lg font-sans text-[10px] font-medium"
              :class="{
                'bg-game-success/15 text-game-success': job.status === 'completed',
                'bg-game-gold/15 text-game-gold': job.status === 'processing',
                'bg-red-500/15 text-red-400': job.status === 'failed',
                'bg-white/10 text-slate-400': job.status === 'pending',
              }"
            >
              <span
                class="w-1.5 h-1.5 rounded-full"
                :class="{
                  'bg-game-success': job.status === 'completed',
                  'bg-game-gold': job.status === 'processing',
                  'bg-red-400': job.status === 'failed',
                  'bg-slate-400': job.status === 'pending',
                }"
              ></span>
              {{ job.status }}
            </span>
            <div class="grid grid-cols-2 gap-2">
              <div
                v-for="(item, idx) in job.items"
                :key="item.id"
                class="border border-white/10 rounded-lg bg-game-dark/50 flex items-center justify-center overflow-hidden"
                :style="{
                  width: `${Math.min(job.pixel_size * 1.5, 80)}px`,
                  height: `${Math.min(job.pixel_size * 1.5, 80)}px`,
                }"
              >
                <img
                  v-if="item.output_image_url"
                  :src="imageUrl(item.output_image_url)"
                  alt=""
                  class="max-w-full max-h-full object-contain image-rendering-pixelated"
                  @error="($event.target as HTMLImageElement).style.display = 'none'"
                />
                <span v-else class="font-mono text-[10px] text-slate-600">{{ idx + 1 }}</span>
              </div>
            </div>
          </div>

          <!-- Right: Info -->
          <div class="flex-1 p-6 md:p-8 border-t md:border-t-0 md:border-l border-white/5">
            <!-- Name -->
            <div class="flex items-center gap-2 mb-2">
              <svg
                class="w-5 h-5 text-game-sakura flex-shrink-0"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.5"
              >
                <rect x="3" y="3" width="7" height="7" />
                <rect x="14" y="3" width="7" height="7" />
                <rect x="3" y="14" width="7" height="7" />
                <rect x="14" y="14" width="7" height="7" />
              </svg>
              <template v-if="!isEditingName">
                <h2 class="font-sans text-xl font-semibold text-white">{{ displayName() }}</h2>
                <button
                  class="text-slate-500 hover:text-white transition-none p-0.5"
                  @click="startEditName"
                >
                  <svg
                    class="w-4 h-4"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                  >
                    <path
                      d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Z"
                    />
                  </svg>
                </button>
              </template>
              <template v-else>
                <input
                  v-model="editName"
                  class="flex-1 font-sans text-xl font-semibold text-white bg-transparent border-b-2 border-game-sakura focus:outline-none py-0.5"
                  @keydown.enter="saveName"
                  @blur="saveName"
                />
              </template>
            </div>

            <!-- Prompt -->
            <p class="font-sans text-sm text-slate-500 mb-4">"{{ job.global_description }}"</p>

            <!-- Meta bar -->
            <div class="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
              <span class="flex items-center gap-1.5 text-slate-400">
                <svg
                  class="w-3.5 h-3.5"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path
                    d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15"
                  />
                </svg>
                <span class="font-mono">{{ job.pixel_size }}&times;{{ job.pixel_size }}px</span>
              </span>
              <span class="w-px h-4 bg-white/10"></span>
              <span class="flex items-center gap-1.5 text-slate-400">
                <svg
                  class="w-3.5 h-3.5"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <rect x="3" y="3" width="7" height="7" />
                  <rect x="14" y="3" width="7" height="7" />
                  <rect x="3" y="14" width="7" height="7" />
                  <rect x="14" y="14" width="7" height="7" />
                </svg>
                {{ job.items.length }} items
              </span>
              <span class="w-px h-4 bg-white/10"></span>
              <span class="flex items-center gap-1.5 text-slate-400">
                <svg
                  class="w-3.5 h-3.5"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path
                    d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178Z"
                  />
                  <path d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
                </svg>
                {{ cameraLabel(job.camera_view) }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Items Section -->
      <section>
        <div class="flex items-center gap-3 mb-4">
          <svg
            class="w-5 h-5 text-game-sakura"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <rect x="3" y="3" width="7" height="7" />
            <rect x="14" y="3" width="7" height="7" />
            <rect x="3" y="14" width="7" height="7" />
            <rect x="14" y="14" width="7" height="7" />
          </svg>
          <h3 class="font-sans text-lg font-semibold text-white">Items</h3>
          <span class="px-2 py-0.5 rounded-md bg-white/5 font-sans text-xs text-slate-400">{{
            job.items.length
          }}</span>
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
          <div
            v-for="(item, idx) in job.items"
            :key="item.id"
            class="rounded-xl border border-white/10 bg-white/[0.02] overflow-hidden hover:border-white/20 transition-none"
          >
            <div class="checkerboard-bg h-28 flex items-center justify-center">
              <img
                v-if="item.output_image_url && regenerating !== item.id"
                :src="imageUrl(item.output_image_url)"
                alt=""
                class="max-w-full max-h-full object-contain image-rendering-pixelated p-2"
                @error="($event.target as HTMLImageElement).style.display = 'none'"
              />
              <img
                v-else-if="regenerating === item.id"
                src="/assets/loading.webp"
                alt="Regenerating..."
                class="w-12 h-12 animate-spin"
              />
              <div
                v-else-if="item.status === 'failed'"
                class="flex flex-col items-center justify-center gap-1 p-2"
              >
                <svg
                  class="w-6 h-6 text-red-400/60"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.5"
                >
                  <path
                    d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z"
                  />
                </svg>
                <span class="font-sans text-[9px] text-red-400/80 text-center line-clamp-2">{{
                  item.error_message || 'Failed'
                }}</span>
              </div>
              <div
                v-else
                class="border border-white/10 rounded-lg bg-game-dark/50 flex items-center justify-center"
                :style="{
                  width: `${Math.min(job.pixel_size, 48)}px`,
                  height: `${Math.min(job.pixel_size, 48)}px`,
                }"
              >
                <span class="font-mono text-[10px] text-slate-600">{{ idx + 1 }}</span>
              </div>
            </div>

            <!-- Error message below preview -->
            <div
              v-if="item.status === 'failed' && item.error_message"
              class="px-2 py-1.5 bg-red-500/5 border-t border-red-500/10"
            >
              <p class="font-sans text-[10px] text-red-400 line-clamp-2">
                {{ item.error_message }}
              </p>
            </div>

            <div class="px-3 py-2.5">
              <!-- Editing mode -->
              <template v-if="editingItemId === item.id">
                <textarea
                  v-model="editItemDescription"
                  rows="2"
                  class="w-full px-2 py-1.5 rounded-lg bg-white/5 border border-white/10 font-sans text-[11px] text-white placeholder-slate-600 focus:outline-none focus:border-game-sakura/60 resize-none mb-2"
                ></textarea>
                <div class="flex items-center gap-1.5">
                  <button
                    class="flex-1 flex items-center justify-center gap-1 px-2 py-1 rounded-lg font-sans text-[10px] font-medium text-white bg-game-sakura hover:bg-game-sakura/90 transition-none"
                    @click="saveAndRegenerate(item.id)"
                  >
                    <svg
                      class="w-3 h-3"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <path
                        d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09Z"
                      />
                    </svg>
                    Regenerate
                  </button>
                  <button
                    class="px-2 py-1 rounded-lg font-sans text-[10px] text-slate-400 hover:text-white border border-white/10 transition-none"
                    @click="cancelEditItem"
                  >
                    Cancel
                  </button>
                </div>
              </template>

              <!-- Display mode -->
              <template v-else>
                <!-- Version tag -->
                <div class="flex items-center gap-1.5 mb-1">
                  <span
                    class="px-1.5 py-0.5 rounded font-mono text-[9px] font-medium"
                    :class="
                      item.tag === 'original'
                        ? 'bg-game-sakura/15 text-game-sakura'
                        : 'bg-game-gold/15 text-game-gold'
                    "
                    >{{ item.tag }}</span
                  >
                </div>
                <p class="font-sans text-xs font-medium text-white truncate mb-1.5">
                  {{ item.item_description }}
                </p>
                <div class="flex items-center gap-1.5">
                  <button
                    v-if="item.output_image_url"
                    class="flex items-center gap-1 px-2 py-0.5 rounded-md font-sans text-[10px] text-slate-500 hover:text-white hover:bg-white/5 transition-none"
                    @click="
                      downloadItem(
                        item.output_image_url,
                        `${item.item_description.replace(/[^a-zA-Z0-9]/g, '_')}.png`,
                      )
                    "
                  >
                    <svg
                      class="w-3 h-3"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <path
                        d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3"
                      />
                    </svg>
                  </button>
                  <button
                    class="flex items-center gap-1 px-2 py-0.5 rounded-md font-sans text-[10px] transition-none"
                    :class="
                      canEdit(item)
                        ? 'text-slate-500 hover:text-white hover:bg-white/5'
                        : 'text-slate-700 cursor-not-allowed'
                    "
                    :disabled="!canEdit(item) || regenerating === item.id"
                    @click="startEditItem(item.id, item.item_description)"
                  >
                    <svg
                      class="w-3 h-3"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <path
                        d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Z"
                      />
                    </svg>
                    Edit {{ item.edit_count }}/{{ MAX_EDITS }}
                  </button>
                  <button
                    class="flex items-center gap-1 px-2 py-0.5 rounded-md font-sans text-[10px] transition-none"
                    :class="
                      canRedo(item)
                        ? 'text-slate-500 hover:text-game-sakura hover:bg-game-sakura/5'
                        : 'text-slate-700 cursor-not-allowed'
                    "
                    :disabled="!canRedo(item) || regenerating === item.id"
                    @click="regenerateWithoutEdit(item.id)"
                  >
                    <svg
                      class="w-3 h-3"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <path
                        d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182M20.995 4.365v4.99"
                      />
                    </svg>
                    Redo {{ item.redo_count }}/{{ MAX_REDOS }}
                  </button>
                  <button
                    v-if="item.status === 'failed' && regenerating !== item.id"
                    class="flex items-center gap-1 px-2 py-0.5 rounded-md font-sans text-[10px] text-amber-500 hover:text-amber-400 hover:bg-amber-400/5 transition-none"
                    @click="retryItem(item.id)"
                  >
                    <svg
                      class="w-3 h-3"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <path
                        d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182M20.995 4.365v4.99"
                      />
                    </svg>
                    Retry
                  </button>
                  <button
                    class="flex items-center gap-1 px-2 py-0.5 rounded-md font-sans text-[10px] text-slate-600 hover:text-red-400 hover:bg-red-400/5 transition-none"
                    @click="handleDeleteItem(item.id)"
                  >
                    <svg
                      class="w-3 h-3"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <path
                        d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
                      />
                    </svg>
                  </button>
                </div>
              </template>
            </div>
          </div>

          <!-- Add new tile card -->
          <div
            class="rounded-xl border-2 border-dashed overflow-hidden transition-none"
            :class="showAddItem ? 'border-game-sakura/40' : 'border-white/10 hover:border-white/20'"
          >
            <template v-if="addingItem">
              <div class="checkerboard-bg h-28 flex items-center justify-center">
                <img
                  src="/assets/loading.webp"
                  alt="Generating..."
                  class="w-12 h-12 animate-spin"
                />
              </div>
              <div class="px-3 py-2.5">
                <p class="font-sans text-[11px] text-slate-400 text-center">Generating...</p>
              </div>
            </template>

            <template v-else-if="showAddItem">
              <div class="p-3 h-full flex flex-col justify-center">
                <span
                  class="font-sans text-[10px] font-medium text-slate-400 uppercase tracking-wider mb-1"
                  >Tile description</span
                >
                <textarea
                  v-model="addItemDescription"
                  rows="3"
                  placeholder="e.g. Healing potion with red liquid..."
                  class="w-full px-2 py-1.5 rounded-lg bg-white/5 border border-white/10 font-sans text-[11px] text-white placeholder-slate-600 focus:outline-none focus:border-game-sakura/60 resize-none mb-2"
                ></textarea>
                <div class="flex items-center gap-1.5">
                  <button
                    class="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded-lg font-sans text-[10px] font-medium text-white transition-none"
                    :class="
                      canSubmitAdd
                        ? 'bg-game-sakura hover:bg-game-sakura/90'
                        : 'bg-game-sakura/30 cursor-not-allowed'
                    "
                    :disabled="!canSubmitAdd"
                    @click="handleAddItem"
                  >
                    <svg
                      class="w-3 h-3"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <path
                        d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09Z"
                      />
                    </svg>
                    Generate
                  </button>
                  <button
                    class="px-2 py-1.5 rounded-lg font-sans text-[10px] text-slate-400 hover:text-white border border-white/10 transition-none"
                    @click="cancelAddItem"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </template>

            <template v-else>
              <button
                class="w-full h-full min-h-[168px] flex flex-col items-center justify-center gap-2"
                @click="openAddItem"
              >
                <svg
                  class="w-6 h-6 text-slate-600"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.5"
                >
                  <path d="M12 4.5v15m7.5-7.5h-15" />
                </svg>
                <span class="font-sans text-[11px] text-slate-600">Add tile</span>
              </button>
            </template>
          </div>
        </div>
      </section>
    </main>

    <!-- ═══════════════════════════════════════ -->
    <!-- ANIMATION MODAL                         -->
    <!-- ═══════════════════════════════════════ -->
    <Teleport to="body">
      <div
        v-if="showAnimation"
        class="fixed inset-0 z-[999] flex items-center justify-center px-4 bg-black/70 backdrop-blur-md"
        @click.self="closeAnimation"
      >
        <div class="relative bg-game-panel border border-white/10 rounded-2xl p-6 max-w-lg w-full shadow-2xl">
          <!-- Header -->
          <div class="flex items-center justify-between mb-4">
            <h3 class="font-pixel text-[11px] text-game-gold tracking-wider">Animation Preview</h3>
            <button
              class="text-slate-500 hover:text-white transition-none text-lg leading-none"
              @click="closeAnimation"
            >
              &#10005;
            </button>
          </div>

          <!-- Preview -->
          <div class="flex items-center justify-center bg-black/30 rounded-xl border border-white/5 p-4 mb-4 min-h-[280px]">
            <div v-if="animationLoading" class="flex flex-col items-center gap-3">
              <svg class="w-8 h-8 text-game-gold animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2v4m0 12v4m-7.07-3.93l2.83-2.83m8.48-8.48l2.83-2.83M2 12h4m12 0h4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83" />
              </svg>
              <span class="font-terminal text-sm text-slate-500">Generating GIF...</span>
            </div>
            <img
              v-else-if="animationUrl"
              :src="animationUrl"
              alt="Animation"
              class="max-w-full max-h-[260px] image-rendering-pixelated"
            />
            <span v-else class="font-terminal text-sm text-red-400">Failed to generate animation</span>
          </div>

          <!-- Speed control -->
          <div class="flex items-center gap-3 mb-5">
            <label class="font-terminal text-xs text-slate-500 whitespace-nowrap">Speed</label>
            <input
              v-model.number="animationSpeed"
              type="range"
              min="50"
              max="1000"
              step="50"
              class="flex-1 accent-game-gold h-1"
              @change="updateAnimationSpeed"
            />
            <span class="font-terminal text-xs text-slate-400 w-16 text-right">{{ animationSpeed }}ms</span>
          </div>

          <!-- Actions -->
          <div class="flex items-center justify-end gap-3">
            <button
              class="px-4 py-2 rounded-lg font-terminal text-xs text-slate-400 border border-white/10 hover:text-white transition-none"
              @click="closeAnimation"
            >
              Close
            </button>
            <button
              class="flex items-center gap-1.5 px-5 py-2 rounded-lg font-terminal text-xs font-semibold text-game-dark bg-game-gold hover:bg-game-gold/90 transition-none"
              :disabled="!animationUrl || animationLoading"
              :class="!animationUrl || animationLoading ? 'opacity-50 cursor-not-allowed' : ''"
              @click="downloadAnimation"
            >
              <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                <path d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
              </svg>
              Download GIF
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.image-rendering-pixelated {
  image-rendering: pixelated;
}
</style>
