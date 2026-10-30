<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { RouterLink } from 'vue-router'
import AppNavbar from '../components/AppNavbar.vue'
import {
  useGenerationsStore,
  mapCameraToApi,
  mapDirectionsToApi,
  cameraLabel,
  directionsCount,
} from '../stores/generations'
import { useAuthStore } from '../stores/auth'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const isDark = ref(true)
const store = useGenerationsStore()
const authStore = useAuthStore()

const credits = computed(() => authStore.user?.generation_credits ?? 0)
const generationCost = computed(() => {
  if (activeTab.value === 'object') {
    return objDirections.value === '8' ? 8 : objDirections.value === '4' ? 4 : 1
  }
  return tileItems.value.length
})
const hasEnoughCredits = computed(() => credits.value >= generationCost.value)

// ── Tour Guide ──
const TOUR_KEY = 'pixelseki_objects_tour_done'
const showTour = ref(false)
const tourStep = ref(0)
const tourPopoverStyle = ref<Record<string, string>>({})

const createBtnRef = ref<HTMLElement | null>(null)
const creditsBadgeRef = ref<HTMLElement | null>(null)

interface TourStep {
  target: ReturnType<typeof ref<HTMLElement | null>> | null
  title: string
  description: string
  position: 'center' | 'bottom'
}

const tourSteps: TourStep[] = [
  {
    target: null,
    title: 'Welcome to Assets!',
    description: 'This is where all your pixel art sprites and tilesets live. Let\'s take a quick tour!',
    position: 'center',
  },
  {
    target: createBtnRef,
    title: 'Create New Assets',
    description: 'Click here to generate new pixel art sprites or tilesets using AI. Choose directions, camera angles, and describe what you want.',
    position: 'bottom',
  },
  {
    target: creditsBadgeRef,
    title: 'Your Credits',
    description: 'Each generation costs credits. You get 5 free credits per week — plan your generations wisely!',
    position: 'bottom',
  },
]

function positionPopover() {
  const step = tourSteps[tourStep.value]!
  if (!step.target || step.position === 'center') {
    tourPopoverStyle.value = {}
    return
  }
  const el = step.target.value
  if (!el) {
    tourPopoverStyle.value = {}
    return
  }
  const rect = el.getBoundingClientRect()
  tourPopoverStyle.value = {
    position: 'fixed',
    top: `${rect.bottom + 12}px`,
    left: `${rect.left + rect.width / 2}px`,
    transform: 'translateX(-50%)',
  }
}

function startTour() {
  tourStep.value = 0
  showTour.value = true
}

function nextStep() {
  if (tourStep.value < tourSteps.length - 1) {
    tourStep.value++
    nextTick(positionPopover)
  } else {
    dismissTour()
  }
}

function dismissTour() {
  showTour.value = false
  localStorage.setItem(TOUR_KEY, 'true')
}

watch(tourStep, () => {
  nextTick(positionPopover)
})

// ── Load jobs on mount, resume streaming for in-progress ones ──
onMounted(async () => {
  await store.fetchJobs()
  for (const job of store.jobs) {
    if (job.status === 'pending' || job.status === 'processing') {
      store.streamJob(job.id)
    }
  }

  // Resolve credits badge ref from navbar DOM
  await nextTick()
  creditsBadgeRef.value = document.getElementById('credits-badge')

  // Show tour for first-time users with empty list
  if (store.jobs.length === 0 && !localStorage.getItem(TOUR_KEY)) {
    startTour()
    nextTick(positionPopover)
  }
})

// ── Create modal ──
const createModalOpen = ref(false)

function openCreate() {
  store.error = null
  submitted.value = false
  createModalOpen.value = true
}
function closeCreate() {
  createModalOpen.value = false
}

// ── Tab / Mode state ──
type GeneratorTab = 'object' | 'tileset'
const activeTab = ref<GeneratorTab>('object')

// ── Object Generator state ──
const objDirections = ref<'1' | '4' | '8'>('1')
const objMode = ref<'create' | 'reference'>('create')
const objDescription = ref('')
const objSize = ref(64)
const objCameraView = ref('side')
const objReferenceFile = ref<File | null>(null)
const objRefDragOver = ref(false)

const objSizeOptions = [32, 48, 64, 96, 128]
const objCameraDisabled = computed(() => objDirections.value === '8')

// ── Tileset Generator state ──
const tileSize = ref(64)
const tileView = ref('top-down')
const tileDescription = ref('')
const tileReferenceFile = ref<File | null>(null)
const tileRefDragOver = ref(false)
const tileItemsExpanded = ref(true)
const tileItems = ref(['', '', '', ''])

const tileSizeOptions = [32, 64, 128, 256]

watch(objDirections, (v) => {
  if (v === '8') objCameraView.value = 'side'
})

// ── File handling ──
function handleFileDrop(e: DragEvent, target: 'object' | 'tileset') {
  e.preventDefault()
  objRefDragOver.value = false
  tileRefDragOver.value = false
  const file = e.dataTransfer?.files[0]
  if (!file?.type.startsWith('image/')) return
  if (target === 'object') objReferenceFile.value = file
  else tileReferenceFile.value = file
}

function handleFileSelect(e: Event, target: 'object' | 'tileset') {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (target === 'object') objReferenceFile.value = file
  else tileReferenceFile.value = file
}

function removeFile(target: 'object' | 'tileset') {
  if (target === 'object') objReferenceFile.value = null
  else tileReferenceFile.value = null
}

// ── Form validation ──
const submitted = ref(false)

const canGenerate = computed(() => {
  if (activeTab.value === 'object') {
    return !!objDescription.value.trim()
  }
  if (!tileDescription.value.trim()) return false
  return tileItems.value.every((desc) => desc.trim().length > 0)
})

// ── Generate ──
async function handleGenerate() {
  submitted.value = true
  if (!canGenerate.value) return

  let result = null

  if (activeTab.value === 'object') {
    result = await store.createJob({
      asset_type: 'object',
      directions: mapDirectionsToApi(objDirections.value),
      camera_view: mapCameraToApi(objCameraView.value),
      pixel_size: objSize.value,
      global_description: objDescription.value.trim(),
      referenceFile: objReferenceFile.value,
    })
  } else {
    const items = tileItems.value.map((desc, idx) => ({
      item_index: idx + 1,
      item_description: desc.trim(),
    }))

    result = await store.createJob({
      asset_type: 'tileset',
      directions: '1 Direction',
      camera_view: mapCameraToApi(tileView.value),
      pixel_size: tileSize.value,
      global_description: tileDescription.value.trim(),
      items,
      referenceFile: tileReferenceFile.value,
    })
  }

  // Only close & reset on success
  if (!result) return

  // Start SSE stream to watch for completion
  store.streamJob(result.id)

  objDescription.value = ''
  tileDescription.value = ''
  tileItems.value = ['', '', '', '']
  closeCreate()
}

// ── Delete ──
async function handleDeleteJob(jobId: string, e: Event) {
  e.preventDefault()
  e.stopPropagation()
  await store.deleteJob(jobId)
}

// ── Filter ──
type FilterType = 'all' | 'object' | 'tileset'
const filterType = ref<FilterType>('all')

const filteredAssets = computed(() => {
  if (filterType.value === 'all') return store.jobs
  return store.jobs.filter((j) => j.asset_type === filterType.value)
})
</script>

<template>
  <div class="min-h-screen w-full bg-game-dark text-slate-200">
    <AppNavbar v-model:is-dark="isDark" />
    <!-- ── App Bar ── -->
    <header
      class="sticky top-[49px] z-40 w-full border-b border-white/5 bg-game-dark/95 backdrop-blur-md"
    >
      <div class="mx-auto flex max-w-6xl items-center justify-between px-4 py-2.5 md:px-8">
        <div class="flex items-center gap-4">
          <RouterLink
            to="/"
            class="font-sans text-xs text-slate-500 hover:text-white transition-none no-underline flex items-center gap-1.5"
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
            Home
          </RouterLink>
          <span class="w-px h-4 bg-white/10"></span>
          <h1 class="font-sans text-sm font-medium text-white">Assets</h1>
        </div>
        <button
          ref="createBtnRef"
          class="flex items-center gap-1.5 px-4 py-1.5 rounded-lg font-sans text-xs font-semibold text-white bg-game-accent hover:bg-game-accent/90 transition-none"
          @click="openCreate"
        >
          <svg
            class="w-3.5 h-3.5"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2.5"
            stroke-linecap="round"
          >
            <path d="M12 5v14m-7-7h14" />
          </svg>
          Create
        </button>
      </div>
    </header>

    <main class="mx-auto max-w-6xl px-4 pt-6 pb-8 md:px-8 md:pt-8 md:pb-12">
      <!-- Header + Filters -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <p class="font-sans text-sm text-slate-400">{{ store.jobs.length }} assets</p>
      </div>

      <!-- Filters -->
      <div
        class="flex items-center gap-1 p-1 rounded-xl bg-white/5 border border-white/5 w-fit mb-6"
      >
        <button
          v-for="f in [
            { key: 'all', label: 'All' },
            { key: 'object', label: 'Objects' },
            { key: 'tileset', label: 'Tilesets' },
          ] as const"
          :key="f.key"
          class="px-4 py-1.5 rounded-lg font-sans text-sm font-medium transition-none"
          :class="
            filterType === f.key
              ? 'bg-game-accent/15 text-game-accent'
              : 'text-slate-400 hover:text-white'
          "
          @click="filterType = f.key"
        >
          {{ f.label }}
        </button>
      </div>

      <!-- Results Grid -->
      <div
        v-if="filteredAssets.length"
        class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
      >
        <component
          :is="asset.status === 'pending' || asset.status === 'processing' ? 'div' : RouterLink"
          v-for="asset in filteredAssets"
          :key="asset.id"
          :to="
            asset.status === 'pending' || asset.status === 'processing'
              ? undefined
              : `/objects/${asset.id}`
          "
          class="rounded-xl border overflow-hidden transition-none no-underline block"
          :class="
            asset.status === 'pending' || asset.status === 'processing'
              ? 'border-game-accent/30 bg-white/[0.02] cursor-default opacity-80'
              : 'border-white/10 bg-white/[0.02] hover:border-white/20 group cursor-pointer'
          "
        >
          <!-- Preview area -->
          <div class="checkerboard-bg h-40 flex items-center justify-center relative">
            <!-- Type badge -->
            <span
              class="absolute top-2.5 left-2.5 px-2 py-0.5 rounded-md font-sans text-[10px] font-medium uppercase tracking-wider"
              :class="
                asset.asset_type === 'object'
                  ? 'bg-game-accent/15 text-game-accent'
                  : 'bg-game-sakura/15 text-game-sakura'
              "
            >
              {{ asset.asset_type }}
            </span>

            <!-- Status badge -->
            <span
              class="absolute top-2.5 right-2.5 flex items-center gap-1 px-2 py-0.5 rounded-md font-sans text-[10px] font-medium"
              :class="{
                'bg-game-success/15 text-game-success': asset.status === 'completed',
                'bg-game-gold/15 text-game-gold':
                  asset.status === 'processing' || asset.status === 'pending',
                'bg-red-500/15 text-red-400': asset.status === 'failed',
              }"
            >
              <span
                class="w-1.5 h-1.5 rounded-full"
                :class="{
                  'bg-game-success': asset.status === 'completed',
                  'bg-game-gold': asset.status === 'processing' || asset.status === 'pending',
                  'bg-red-400': asset.status === 'failed',
                }"
              ></span>
              {{ asset.status === 'pending' ? 'queued' : asset.status }}
            </span>

            <!-- Loading spinner for pending/processing -->
            <template v-if="asset.status === 'pending' || asset.status === 'processing'">
              <img src="/assets/loading.webp" alt="Generating..." class="w-16 h-16 animate-spin" />
            </template>

            <!-- Preview: real images -->
            <template v-else-if="asset.items.length > 0 && asset.items[0]!.output_image_url">
              <!-- Single direction: one big preview -->
              <img
                v-if="asset.items.length === 1"
                :src="asset.items[0]!.output_image_url?.startsWith('http') ? asset.items[0]!.output_image_url : `${API_URL}${asset.items[0]!.output_image_url}`"
                alt=""
                class="max-h-[120px] object-contain image-rendering-pixelated"
                @error="($event.target as HTMLImageElement).style.display = 'none'"
              />
              <!-- Multi-direction object: row of thumbnails -->
              <div v-else-if="asset.asset_type === 'object'" class="flex items-center gap-2">
                <img
                  v-for="item in asset.items.slice(0, 4)"
                  :key="item.id"
                  :src="item.output_image_url?.startsWith('http') ? item.output_image_url : `${API_URL}${item.output_image_url}`"
                  alt=""
                  class="h-20 w-20 object-contain image-rendering-pixelated"
                  @error="($event.target as HTMLImageElement).style.display = 'none'"
                />
              </div>
              <!-- Tileset: 2x2 grid -->
              <div v-else class="grid grid-cols-2 gap-1.5">
                <img
                  v-for="item in asset.items.slice(0, 4)"
                  :key="item.id"
                  :src="item.output_image_url?.startsWith('http') ? item.output_image_url : `${API_URL}${item.output_image_url}`"
                  alt=""
                  class="w-16 h-16 object-contain image-rendering-pixelated"
                  @error="($event.target as HTMLImageElement).style.display = 'none'"
                />
              </div>
            </template>
            <template v-else>
              <div v-if="asset.asset_type === 'object'" class="flex items-center gap-2">
                <div
                  v-for="i in Math.min(directionsCount(asset.directions), 4)"
                  :key="i"
                  class="border border-white/10 rounded-lg bg-game-dark/60 flex items-center justify-center"
                  :style="{
                    width: `${Math.min(asset.pixel_size, 48)}px`,
                    height: `${Math.min(asset.pixel_size, 48)}px`,
                  }"
                >
                  <span class="font-mono text-[9px] text-slate-600">{{ i }}</span>
                </div>
              </div>
              <div v-else class="grid grid-cols-2 gap-1.5">
                <div
                  v-for="i in 4"
                  :key="i"
                  class="border border-white/10 rounded-lg bg-game-dark/60 flex items-center justify-center w-10 h-10"
                >
                  <span class="font-mono text-[9px] text-slate-600">{{ i }}</span>
                </div>
              </div>
            </template>
          </div>

          <!-- Info: skeleton when loading, real data otherwise -->
          <div class="p-4">
            <template v-if="asset.status === 'pending' || asset.status === 'processing'">
              <div class="h-4 w-3/4 rounded-md bg-white/5 skeleton-shimmer mb-3"></div>
              <div class="flex items-center gap-3">
                <div class="h-3 w-10 rounded bg-white/5 skeleton-shimmer"></div>
                <span class="w-px h-3 bg-white/10"></span>
                <div class="h-3 w-16 rounded bg-white/5 skeleton-shimmer"></div>
                <span class="w-px h-3 bg-white/10"></span>
                <div class="h-3 w-14 rounded bg-white/5 skeleton-shimmer"></div>
              </div>
              <div class="h-3 w-20 rounded bg-white/5 skeleton-shimmer mt-3"></div>
            </template>
            <template v-else>
              <div class="flex items-start justify-between gap-2">
                <h3 class="font-sans text-sm font-medium text-white truncate">
                  {{ asset.global_description }}
                </h3>
                <button
                  class="flex-shrink-0 p-1 rounded-lg text-slate-600 hover:text-red-400 hover:bg-red-400/10 transition-none"
                  title="Delete"
                  @click="handleDeleteJob(asset.id, $event)"
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
                </button>
              </div>
              <div class="flex items-center gap-3 mt-3">
                <span class="font-mono text-[11px] text-slate-500">{{ asset.pixel_size }}px</span>
                <span class="w-px h-3 bg-white/10"></span>
                <span class="font-sans text-[11px] text-slate-500">{{ asset.directions }}</span>
                <span class="w-px h-3 bg-white/10"></span>
                <span class="font-sans text-[11px] text-slate-500">{{
                  cameraLabel(asset.camera_view)
                }}</span>
              </div>
              <p class="font-sans text-[11px] text-slate-600 mt-2">
                {{ new Date(asset.created_at).toLocaleDateString() }}
              </p>
            </template>
          </div>
        </component>
      </div>

      <!-- Empty state -->
      <div v-else class="flex flex-col items-center justify-center py-20 text-center">
        <svg
          class="w-12 h-12 text-slate-600 mb-4"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
        >
          <path
            d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z"
          />
        </svg>
        <p class="font-sans text-sm text-slate-400 mb-1">No assets yet</p>
        <p class="font-sans text-xs text-slate-600">
          Create your first pixel art asset to get started
        </p>
      </div>
    </main>

    <!-- ═══════════════════════════════════════ -->
    <!-- CREATE MODAL                            -->
    <!-- ═══════════════════════════════════════ -->
    <Teleport to="body">
      <div
        v-if="createModalOpen"
        class="fixed inset-0 z-[999] flex items-start justify-center px-4 py-8 md:py-12 overflow-y-auto bg-black/70 backdrop-blur-md"
        @click.self="closeCreate"
      >
        <div
          class="w-full max-w-3xl rounded-2xl border border-white/10 bg-[#0f1219] relative overflow-hidden"
        >
          <!-- Top accent line -->
          <div
            class="h-1 w-full bg-gradient-to-r from-transparent via-game-accent to-transparent"
          ></div>

          <div class="p-6 md:p-8">
            <!-- Header -->
            <div class="flex items-center justify-between mb-6">
              <div>
                <h2 class="font-sans text-lg font-semibold text-white">Create New Object</h2>
                <p class="font-sans text-xs text-slate-400 mt-0.5">
                  Configure and generate pixel art
                </p>
              </div>
              <button
                class="w-8 h-8 flex items-center justify-center rounded-full text-slate-500 hover:text-white hover:bg-white/10 transition-none"
                @click="closeCreate"
              >
                <svg
                  class="w-4 h-4"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                >
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            </div>

            <!-- Error message -->
            <div
              v-if="store.error"
              class="flex items-center gap-3 font-sans text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded-xl px-4 py-2.5 mb-6"
            >
              <svg
                class="w-4 h-4 flex-shrink-0"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <circle cx="12" cy="12" r="10" />
                <path d="M12 8v4m0 4h.01" />
              </svg>
              {{ store.error }}
            </div>

            <!-- Tab Switcher -->
            <div
              class="flex items-center gap-1 p-1 rounded-xl bg-white/5 border border-white/5 w-fit mb-6"
            >
              <button
                class="px-4 py-1.5 rounded-lg font-sans text-sm font-medium transition-none"
                :class="
                  activeTab === 'object'
                    ? 'bg-game-accent/15 text-game-accent'
                    : 'text-slate-400 hover:text-white'
                "
                @click="activeTab = 'object'"
              >
                <span class="mr-1">&#9670;</span> Object
              </button>
              <button
                class="px-4 py-1.5 rounded-lg font-sans text-sm font-medium transition-none"
                :class="
                  activeTab === 'tileset'
                    ? 'bg-game-accent/15 text-game-accent'
                    : 'text-slate-400 hover:text-white'
                "
                @click="activeTab = 'tileset'"
              >
                <span class="mr-1">&#9638;</span> Tileset
              </button>
            </div>

            <!-- ──── OBJECT TAB ──── -->
            <template v-if="activeTab === 'object'">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <!-- Directions -->
                <label class="block">
                  <span
                    class="font-sans text-xs font-medium text-slate-400 uppercase tracking-wider mb-1.5 block"
                    >Directions</span
                  >
                  <select
                    v-model="objDirections"
                    class="w-full px-4 py-2.5 rounded-xl border bg-white/5 border-white/10 font-sans text-sm text-white focus:outline-none focus:ring-2 focus:ring-game-accent/40 focus:border-game-accent/60 transition-none appearance-none cursor-pointer"
                  >
                    <option value="1">1 Direction</option>
                    <option value="4">4 Directions</option>
                    <option value="8">8 Directions</option>
                  </select>
                </label>

                <!-- Camera View -->
                <label class="block">
                  <span
                    class="font-sans text-xs font-medium text-slate-400 uppercase tracking-wider mb-1.5 block"
                  >
                    Camera View
                    <span v-if="objCameraDisabled" class="text-slate-600 normal-case ml-1"
                      >(auto for 8-dir)</span
                    >
                  </span>
                  <select
                    v-model="objCameraView"
                    :disabled="objCameraDisabled"
                    class="w-full px-4 py-2.5 rounded-xl border font-sans text-sm text-white focus:outline-none focus:ring-2 focus:ring-game-accent/40 focus:border-game-accent/60 transition-none appearance-none cursor-pointer"
                    :class="
                      objCameraDisabled
                        ? 'bg-white/[0.02] border-white/5 text-slate-600 cursor-not-allowed'
                        : 'bg-white/5 border-white/10'
                    "
                  >
                    <option value="side">Side View</option>
                    <option value="top-down">Top-Down</option>
                    <option value="isometric">Isometric (2.5D)</option>
                  </select>
                </label>
              </div>

              <!-- Mode Toggle -->
              <div class="mb-4">
                <span
                  class="font-sans text-xs font-medium text-slate-400 uppercase tracking-wider mb-1.5 block"
                  >Mode</span
                >
                <div
                  class="flex items-center gap-1 p-1 rounded-xl bg-white/5 border border-white/5 w-fit"
                >
                  <button
                    class="px-4 py-1.5 rounded-lg font-sans text-sm font-medium transition-none"
                    :class="
                      objMode === 'create'
                        ? 'bg-game-accent/15 text-game-accent'
                        : 'text-slate-400 hover:text-white'
                    "
                    @click="objMode = 'create'"
                  >
                    Create
                  </button>
                  <button
                    class="px-4 py-1.5 rounded-lg font-sans text-sm font-medium transition-none"
                    :class="
                      objMode === 'reference'
                        ? 'bg-game-accent/15 text-game-accent'
                        : 'text-slate-400 hover:text-white'
                    "
                    @click="objMode = 'reference'"
                  >
                    From Reference
                  </button>
                </div>
              </div>

              <!-- Style Reference -->
              <div v-if="objMode === 'reference'" class="mb-4">
                <span
                  class="font-sans text-xs font-medium text-slate-400 uppercase tracking-wider mb-1.5 block"
                  >Style Reference</span
                >
                <div
                  v-if="!objReferenceFile"
                  class="relative border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-none"
                  :class="
                    objRefDragOver
                      ? 'border-game-accent/60 bg-game-accent/5'
                      : 'border-white/10 hover:border-white/20'
                  "
                  @dragover.prevent="objRefDragOver = true"
                  @dragleave="objRefDragOver = false"
                  @drop="handleFileDrop($event, 'object')"
                >
                  <input
                    type="file"
                    accept="image/*"
                    class="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    @change="handleFileSelect($event, 'object')"
                  />
                  <svg
                    class="w-6 h-6 mx-auto mb-1.5 text-slate-500"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="1.5"
                  >
                    <path
                      d="M12 16.5V9.75m0 0 3 3m-3-3-3 3M6.75 19.5a4.5 4.5 0 0 1-1.41-8.775 5.25 5.25 0 0 1 10.233-2.33 3 3 0 0 1 3.758 3.848A3.752 3.752 0 0 1 18 19.5H6.75Z"
                    />
                  </svg>
                  <p class="font-sans text-sm text-slate-400">
                    Drop image or <span class="text-game-accent">browse</span>
                  </p>
                </div>
                <div
                  v-else
                  class="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/10"
                >
                  <div
                    class="w-9 h-9 rounded-lg bg-game-accent/10 flex items-center justify-center flex-shrink-0"
                  >
                    <svg
                      class="w-4 h-4 text-game-accent"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="1.5"
                    >
                      <path
                        d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0 0 22.5 18.75V5.25A2.25 2.25 0 0 0 20.25 3H3.75A2.25 2.25 0 0 0 1.5 5.25v13.5A2.25 2.25 0 0 0 3.75 21Z"
                      />
                    </svg>
                  </div>
                  <div class="flex-1 min-w-0">
                    <p class="font-sans text-sm text-white truncate">{{ objReferenceFile.name }}</p>
                    <p class="font-sans text-xs text-slate-500">
                      {{ (objReferenceFile.size / 1024).toFixed(1) }} KB
                    </p>
                  </div>
                  <button
                    class="text-slate-500 hover:text-red-400 transition-none p-1"
                    @click="removeFile('object')"
                  >
                    <svg
                      class="w-4 h-4"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <path d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>

              <!-- Description -->
              <label class="block mb-4">
                <span
                  class="font-sans text-xs font-medium text-slate-400 uppercase tracking-wider mb-1.5 block"
                  >Description <span class="text-red-400">*</span></span
                >
                <textarea
                  v-model="objDescription"
                  rows="2"
                  placeholder="A treasure chest with gold coins overflowing..."
                  class="w-full px-4 py-3 rounded-xl border bg-white/5 font-sans text-sm text-white placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-game-accent/40 focus:border-game-accent/60 transition-none resize-none"
                  :class="
                    submitted && !objDescription.trim() ? 'border-red-400/60' : 'border-white/10'
                  "
                ></textarea>
                <p
                  v-if="submitted && !objDescription.trim()"
                  class="font-sans text-[11px] text-red-400 mt-1"
                >
                  Description is required
                </p>
              </label>

              <!-- Size -->
              <div class="mb-4">
                <span
                  class="font-sans text-xs font-medium text-slate-400 uppercase tracking-wider mb-2 block"
                >
                  Size <span class="text-game-accent font-mono ml-1">{{ objSize }}px</span>
                </span>
                <div class="flex items-center gap-2">
                  <button
                    v-for="size in objSizeOptions"
                    :key="size"
                    class="flex-1 py-2 rounded-lg font-mono text-xs font-medium border transition-none"
                    :class="
                      objSize === size
                        ? 'bg-game-accent/15 border-game-accent/40 text-game-accent'
                        : 'bg-white/5 border-white/5 text-slate-400 hover:text-white hover:border-white/10'
                    "
                    @click="objSize = size"
                  >
                    {{ size }}
                  </button>
                </div>
              </div>
            </template>

            <!-- ──── TILESET TAB ──── -->
            <template v-else>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <label class="block">
                  <span
                    class="font-sans text-xs font-medium text-slate-400 uppercase tracking-wider mb-1.5 block"
                    >View</span
                  >
                  <select
                    v-model="tileView"
                    class="w-full px-4 py-2.5 rounded-xl border bg-white/5 border-white/10 font-sans text-sm text-white focus:outline-none focus:ring-2 focus:ring-game-accent/40 focus:border-game-accent/60 transition-none appearance-none cursor-pointer"
                  >
                    <option value="top-down">Top-Down</option>
                    <option value="side">Side View</option>
                    <option value="orthographic">Orthographic</option>
                  </select>
                </label>

                <label class="block">
                  <span
                    class="font-sans text-xs font-medium text-slate-400 uppercase tracking-wider mb-1.5 block"
                    >Directions</span
                  >
                  <select
                    disabled
                    class="w-full px-4 py-2.5 rounded-xl border bg-white/[0.02] border-white/5 font-sans text-sm text-slate-600 cursor-not-allowed transition-none appearance-none"
                  >
                    <option>1 Direction (locked)</option>
                  </select>
                </label>
              </div>

              <!-- Style Reference (required) -->
              <div class="mb-4">
                <span
                  class="font-sans text-xs font-medium text-slate-400 uppercase tracking-wider mb-1.5 block"
                >
                  Style Reference <span class="text-red-400">*</span>
                </span>
                <div
                  v-if="!tileReferenceFile"
                  class="relative border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-none"
                  :class="
                    tileRefDragOver
                      ? 'border-game-accent/60 bg-game-accent/5'
                      : 'border-white/10 hover:border-white/20'
                  "
                  @dragover.prevent="tileRefDragOver = true"
                  @dragleave="tileRefDragOver = false"
                  @drop="handleFileDrop($event, 'tileset')"
                >
                  <input
                    type="file"
                    accept="image/*"
                    class="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    @change="handleFileSelect($event, 'tileset')"
                  />
                  <svg
                    class="w-6 h-6 mx-auto mb-1.5 text-slate-500"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="1.5"
                  >
                    <path
                      d="M12 16.5V9.75m0 0 3 3m-3-3-3 3M6.75 19.5a4.5 4.5 0 0 1-1.41-8.775 5.25 5.25 0 0 1 10.233-2.33 3 3 0 0 1 3.758 3.848A3.752 3.752 0 0 1 18 19.5H6.75Z"
                    />
                  </svg>
                  <p class="font-sans text-sm text-slate-400">
                    Drop image or <span class="text-game-accent">browse</span>
                  </p>
                </div>
                <div
                  v-else
                  class="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/10"
                >
                  <div
                    class="w-9 h-9 rounded-lg bg-game-accent/10 flex items-center justify-center flex-shrink-0"
                  >
                    <svg
                      class="w-4 h-4 text-game-accent"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="1.5"
                    >
                      <path
                        d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0 0 22.5 18.75V5.25A2.25 2.25 0 0 0 20.25 3H3.75A2.25 2.25 0 0 0 1.5 5.25v13.5A2.25 2.25 0 0 0 3.75 21Z"
                      />
                    </svg>
                  </div>
                  <div class="flex-1 min-w-0">
                    <p class="font-sans text-sm text-white truncate">
                      {{ tileReferenceFile.name }}
                    </p>
                    <p class="font-sans text-xs text-slate-500">
                      {{ (tileReferenceFile.size / 1024).toFixed(1) }} KB
                    </p>
                  </div>
                  <button
                    class="text-slate-500 hover:text-red-400 transition-none p-1"
                    @click="removeFile('tileset')"
                  >
                    <svg
                      class="w-4 h-4"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <path d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>

              <!-- Description -->
              <label class="block mb-4">
                <span
                  class="font-sans text-xs font-medium text-slate-400 uppercase tracking-wider mb-1.5 block"
                  >Description <span class="text-red-400">*</span></span
                >
                <textarea
                  v-model="tileDescription"
                  rows="2"
                  placeholder="Fantasy RPG potion items with a dark medieval style..."
                  class="w-full px-4 py-3 rounded-xl border bg-white/5 font-sans text-sm text-white placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-game-accent/40 focus:border-game-accent/60 transition-none resize-none"
                  :class="
                    submitted && !tileDescription.trim() ? 'border-red-400/60' : 'border-white/10'
                  "
                ></textarea>
                <p
                  v-if="submitted && !tileDescription.trim()"
                  class="font-sans text-[11px] text-red-400 mt-1"
                >
                  Description is required
                </p>
              </label>

              <!-- Size -->
              <div class="mb-4">
                <span
                  class="font-sans text-xs font-medium text-slate-400 uppercase tracking-wider mb-2 block"
                >
                  Size <span class="text-game-accent font-mono ml-1">{{ tileSize }}px</span>
                </span>
                <div class="flex items-center gap-2">
                  <button
                    v-for="size in tileSizeOptions"
                    :key="size"
                    class="flex-1 py-2 rounded-lg font-mono text-xs font-medium border transition-none"
                    :class="
                      tileSize === size
                        ? 'bg-game-accent/15 border-game-accent/40 text-game-accent'
                        : 'bg-white/5 border-white/5 text-slate-400 hover:text-white hover:border-white/10'
                    "
                    @click="tileSize = size"
                  >
                    {{ size }}
                  </button>
                </div>
              </div>

              <!-- Item Refinement -->
              <div class="rounded-xl border border-white/10 overflow-hidden mb-4">
                <button
                  class="w-full flex items-center justify-between px-4 py-3 font-sans text-sm font-medium text-white transition-none"
                  :class="tileItemsExpanded ? 'bg-white/5' : 'hover:bg-white/[0.03]'"
                  @click="tileItemsExpanded = !tileItemsExpanded"
                >
                  <span>
                    <svg
                      class="w-4 h-4 inline-block mr-1.5 text-game-accent"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <path d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
                    </svg>
                    Describe each item (4) <span class="text-red-400">*</span>
                  </span>
                  <svg
                    class="w-4 h-4 text-slate-400"
                    :class="tileItemsExpanded ? 'rotate-180' : ''"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                  >
                    <path d="m19.5 8.25-7.5 7.5-7.5-7.5" />
                  </svg>
                </button>
                <div
                  v-if="tileItemsExpanded"
                  class="px-4 pb-4 pt-2 space-y-2.5 border-t border-white/5"
                >
                  <div v-for="(_, idx) in tileItems" :key="idx" class="flex items-center gap-2.5">
                    <span class="font-mono text-xs text-slate-500 w-4 text-right flex-shrink-0"
                      >{{ idx + 1 }}.</span
                    >
                    <input
                      v-model="tileItems[idx]"
                      type="text"
                      :placeholder="
                        ['Common health potion', 'Mana potion', 'Antidote flask', 'Elixir of life'][
                          idx
                        ]
                      "
                      class="flex-1 px-3 py-2 rounded-xl border bg-white/5 font-sans text-sm text-white placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-game-accent/40 focus:border-game-accent/60 transition-none"
                      :class="
                        submitted && !tileItems[idx]!.trim()
                          ? 'border-red-400/60'
                          : 'border-white/10'
                      "
                    />
                  </div>
                </div>
              </div>
            </template>

            <!-- Footer: Cost + Generate -->
            <div
              class="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 pt-4 border-t border-white/5"
            >
              <!-- Cost info -->
              <div class="flex items-center gap-2.5">
                <div
                  class="w-8 h-8 rounded-lg bg-game-gold/10 flex items-center justify-center flex-shrink-0"
                >
                  <svg
                    class="w-4 h-4 text-game-gold"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="1.5"
                  >
                    <path
                      d="M12 6v12m-3-2.818.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
                    />
                  </svg>
                </div>
                <div>
                  <p class="font-sans text-[11px] text-slate-600">
                    <template v-if="activeTab === 'object'"
                      >{{
                        objDirections === '8' ? '8' : objDirections === '4' ? '4' : '1'
                      }}
                      rotation{{ objDirections !== '1' ? 's' : '' }} &middot;
                      {{ objSize }}px</template
                    >
                    <template v-else
                      >4 frames &middot; 2&times;2 grid &middot; {{ tileSize }}px</template
                    >
                  </p>
                  <p class="font-sans text-[11px]" :class="hasEnoughCredits ? 'text-game-gold' : 'text-red-400'">
                    Cost: {{ generationCost }} credit{{ generationCost !== 1 ? 's' : '' }}
                    &middot; &#9733; {{ credits }} remaining
                  </p>
                </div>
              </div>

              <!-- Buttons -->
              <div class="flex items-center gap-3">
                <button
                  class="px-5 py-2.5 rounded-xl font-sans text-sm font-medium text-slate-400 hover:text-white border border-white/10 hover:border-white/20 transition-none"
                  @click="closeCreate"
                >
                  Cancel
                </button>
                <button
                  class="flex items-center gap-2 px-6 py-2.5 rounded-xl font-sans text-sm font-semibold text-white transition-none"
                  :class="
                    store.generating || !canGenerate || !hasEnoughCredits
                      ? 'bg-game-accent/30 cursor-not-allowed'
                      : 'bg-game-accent hover:bg-game-accent/90'
                  "
                  :disabled="store.generating || !canGenerate || !hasEnoughCredits"
                  style="text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3)"
                  @click="handleGenerate"
                >
                  <svg
                    v-if="!store.generating"
                    class="w-4 h-4"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                  >
                    <path
                      d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 0 0-2.455 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z"
                    />
                  </svg>
                  <svg
                    v-else
                    class="w-4 h-4 animate-spin"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                  >
                    <path
                      d="M12 2v4m0 12v4m-7.07-3.93l2.83-2.83m8.48-8.48l2.83-2.83M2 12h4m12 0h4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83"
                    />
                  </svg>
                  {{ store.generating ? 'Generating...' : !hasEnoughCredits ? 'Not enough credits' : 'Generate' }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ═══════════════════════════════════════ -->
    <!-- TOUR GUIDE OVERLAY                      -->
    <!-- ═══════════════════════════════════════ -->
    <Teleport to="body">
      <div v-if="showTour" class="fixed inset-0 z-[9999]">
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/60" @click.self="dismissTour"></div>

        <!-- Centered popover (step 0: Welcome) -->
        <div
          v-if="tourSteps[tourStep]!.position === 'center'"
          class="absolute inset-0 flex items-center justify-center"
        >
          <div class="relative bg-game-panel border-2 border-game-accent/50 rounded-2xl px-8 py-6 max-w-sm text-center shadow-xl shadow-game-accent/10">
            <div class="w-12 h-12 mx-auto mb-4 rounded-xl bg-game-accent/10 flex items-center justify-center">
              <span class="text-2xl">&#9733;</span>
            </div>
            <h3 class="font-pixel text-[11px] text-game-accent tracking-wider mb-2">
              {{ tourSteps[tourStep]!.title }}
            </h3>
            <p class="font-terminal text-sm text-slate-400 mb-6">
              {{ tourSteps[tourStep]!.description }}
            </p>
            <div class="flex items-center justify-center gap-3">
              <button
                class="px-5 py-2 rounded-lg font-terminal text-sm text-slate-400 border border-white/10 hover:border-white/20 hover:text-white transition-none"
                @click="dismissTour"
              >
                Skip
              </button>
              <button
                class="px-5 py-2 rounded-lg font-terminal text-sm font-semibold text-white bg-game-accent hover:bg-game-accent/90 transition-none"
                @click="nextStep"
              >
                Let's go!
              </button>
            </div>
            <div class="flex items-center justify-center gap-1.5 mt-4">
              <span v-for="i in tourSteps.length" :key="i" class="w-1.5 h-1.5 rounded-full" :class="i - 1 === tourStep ? 'bg-game-accent' : 'bg-slate-600'"></span>
            </div>
          </div>
        </div>

        <!-- Anchored popover (steps with target ref) -->
        <div
          v-else
          :style="tourPopoverStyle"
          class="z-[10000] max-w-xs"
        >
          <div
            class="relative bg-game-panel border-2 rounded-2xl px-6 py-5 shadow-xl"
            :class="tourStep === tourSteps.length - 1 ? 'border-game-gold/50 shadow-game-gold/10' : 'border-game-accent/50 shadow-game-accent/10'"
          >
            <!-- Arrow pointing up -->
            <div
              class="absolute -top-2 left-1/2 -translate-x-1/2 w-4 h-4 bg-game-panel border-l-2 border-t-2 rotate-45"
              :class="tourStep === tourSteps.length - 1 ? 'border-game-gold/50' : 'border-game-accent/50'"
            ></div>
            <h3
              class="font-pixel text-[10px] tracking-wider mb-2"
              :class="tourStep === tourSteps.length - 1 ? 'text-game-gold' : 'text-game-accent'"
            >
              {{ tourSteps[tourStep]!.title }}
            </h3>
            <p class="font-terminal text-sm text-slate-400 mb-5">
              {{ tourSteps[tourStep]!.description }}
            </p>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-1.5">
                <span
                  v-for="i in tourSteps.length"
                  :key="i"
                  class="w-1.5 h-1.5 rounded-full"
                  :class="i - 1 === tourStep
                    ? (tourStep === tourSteps.length - 1 ? 'bg-game-gold' : 'bg-game-accent')
                    : 'bg-slate-600'"
                ></span>
              </div>
              <div class="flex items-center gap-2">
                <button
                  class="px-4 py-1.5 rounded-lg font-terminal text-xs text-slate-400 border border-white/10 hover:text-white transition-none"
                  @click="dismissTour"
                >
                  Skip
                </button>
                <button
                  class="px-4 py-1.5 rounded-lg font-terminal text-xs font-semibold transition-none"
                  :class="tourStep === tourSteps.length - 1
                    ? 'text-game-dark bg-game-gold hover:bg-game-gold/90'
                    : 'text-white bg-game-accent hover:bg-game-accent/90'"
                  @click="nextStep"
                >
                  {{ tourStep === tourSteps.length - 1 ? 'Got it!' : 'Next' }}
                </button>
              </div>
            </div>
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

.skeleton-shimmer {
  background: linear-gradient(
    90deg,
    rgba(255, 255, 255, 0.03) 25%,
    rgba(255, 255, 255, 0.08) 50%,
    rgba(255, 255, 255, 0.03) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
}

@keyframes shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}
</style>
