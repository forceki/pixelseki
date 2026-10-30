<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useCreationsStore, type Creation } from '../stores/creations'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const route = useRoute()
const store = useCreationsStore()

const creation = ref<Creation | null>(null)
const versions = ref<Creation[]>([])
const loading = ref(true)
const regenerating = ref(false)
const downloading = ref(false)

// ── Magnifying glass ──
const lensActive = ref(false)
const lensX = ref(0)
const lensY = ref(0)
const lensZoom = ref(4)
const previewRef = ref<HTMLDivElement | null>(null)
const imageRef = ref<HTMLImageElement | null>(null)

const LENS_SIZE = 150

function onPreviewMouseMove(e: MouseEvent) {
  if (!imageRef.value || !previewRef.value) return
  lensActive.value = true

  const containerRect = previewRef.value.getBoundingClientRect()
  lensX.value = e.clientX - containerRect.left
  lensY.value = e.clientY - containerRect.top
}

function onPreviewMouseLeave() {
  lensActive.value = false
}

function cycleLensZoom() {
  const steps = [2, 4, 6, 8]
  const idx = steps.indexOf(lensZoom.value)
  lensZoom.value = steps[(idx + 1) % steps.length]!
}

function lensBackgroundPosition(): string {
  if (!imageRef.value || !previewRef.value) return '0 0'

  const img = imageRef.value
  const imgRect = img.getBoundingClientRect()
  const containerRect = previewRef.value.getBoundingClientRect()

  // Mouse position relative to the image
  const imgX = (lensX.value - (imgRect.left - containerRect.left)) / imgRect.width
  const imgY = (lensY.value - (imgRect.top - containerRect.top)) / imgRect.height

  const bgW = imgRect.width * lensZoom.value
  const bgH = imgRect.height * lensZoom.value

  const bgX = -(imgX * bgW - LENS_SIZE / 2)
  const bgY = -(imgY * bgH - LENS_SIZE / 2)

  return `${bgX}px ${bgY}px`
}

function lensBackgroundSize(): string {
  if (!imageRef.value || !previewRef.value) return '0 0'

  const img = imageRef.value
  const imgRect = img.getBoundingClientRect()

  return `${imgRect.width * lensZoom.value}px ${imgRect.height * lensZoom.value}px`
}

// ── Edit description for regenerate ──
const showEditPrompt = ref(false)
const editDescription = ref('')

onMounted(async () => {
  const id = route.params.id as string
  creation.value = await store.getCreation(id)
  if (creation.value) {
    versions.value = await store.getVersions(id)
  }
  loading.value = false
})

function imageUrl(path: string | null): string {
  if (!path) return ''
  if (path.startsWith('http')) return path
  return `${API_URL}${path}`
}

function openEdit() {
  if (!creation.value) return
  editDescription.value = creation.value.description
  showEditPrompt.value = true
}

async function handleRegenerate(newDescription?: string) {
  if (!creation.value) return
  showEditPrompt.value = false
  regenerating.value = true

  const result = await store.regenerateCreation(creation.value.id, newDescription)
  if (!result) {
    regenerating.value = false
    return
  }

  // Poll for completion
  const poll = setInterval(async () => {
    const updated = await store.getCreation(result.id)
    if (!updated) {
      clearInterval(poll)
      regenerating.value = false
      return
    }
    if (updated.status === 'completed' || updated.status === 'failed') {
      creation.value = updated
      versions.value = await store.getVersions(result.id)
      regenerating.value = false
      clearInterval(poll)
    }
  }, 2000)
}

async function downloadImage() {
  if (!creation.value?.output_image_url) return
  downloading.value = true
  try {
    const token = localStorage.getItem('access_token')
    const res = await fetch(
      `${API_URL}/api/v1/creations/${creation.value.id}/download`,
      { headers: { Authorization: `Bearer ${token}` } },
    )
    if (!res.ok) throw new Error()
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = res.headers.get('content-disposition')?.match(/filename="(.+)"/)?.[1] ?? 'creation.zip'
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } finally {
    downloading.value = false
  }
}

async function switchVersion(v: Creation) {
  creation.value = v
}
</script>

<template>
  <div class="min-h-screen w-full bg-game-dark text-slate-200">
    <!-- App Bar -->
    <header class="sticky top-0 z-40 w-full border-b border-white/5 bg-game-dark/95 backdrop-blur-md">
      <div class="mx-auto flex max-w-5xl items-center justify-between px-4 py-2.5 md:px-8">
        <div class="flex items-center gap-4 min-w-0">
          <RouterLink
            to="/creation"
            class="font-sans text-xs text-slate-500 hover:text-white transition-none no-underline flex items-center gap-1.5 flex-shrink-0"
          >
            <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="M15 19l-7-7 7-7" />
            </svg>
            Studio
          </RouterLink>
          <span class="w-px h-4 bg-white/10 flex-shrink-0"></span>
          <h1 class="font-sans text-sm font-medium text-white truncate">
            {{ creation ? creation.description.slice(0, 50) : 'Loading...' }}
          </h1>
        </div>
        <div v-if="creation?.status === 'completed'" class="flex items-center gap-2 flex-shrink-0">
          <button
            class="flex items-center gap-1.5 px-4 py-1.5 rounded-lg font-sans text-xs font-semibold text-white bg-game-accent hover:bg-game-accent/90 transition-none"
            :disabled="downloading"
            @click="downloadImage"
          >
            <svg v-if="!downloading" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
            </svg>
            <svg v-else class="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2v4m0 12v4m-7.07-3.93l2.83-2.83m8.48-8.48l2.83-2.83M2 12h4m12 0h4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83" />
            </svg>
            {{ downloading ? 'Zipping...' : 'Download' }}
          </button>
        </div>
      </div>
    </header>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-32">
      <p class="font-sans text-sm text-slate-500">Loading...</p>
    </div>

    <!-- Not Found -->
    <div v-else-if="!creation" class="flex flex-col items-center justify-center py-32 text-center">
      <p class="font-sans text-lg text-slate-400 mb-2">Creation not found</p>
      <RouterLink to="/creation" class="font-sans text-sm text-game-accent hover:underline transition-none no-underline">Back to studio</RouterLink>
    </div>

    <!-- Detail -->
    <main v-else class="mx-auto max-w-5xl px-4 pt-6 pb-12 md:px-8 md:pt-8">
      <!-- Large Preview -->
      <div class="rounded-2xl border border-white/10 bg-white/[0.02] overflow-hidden mb-8">
        <div
          ref="previewRef"
          class="checkerboard-bg min-h-[300px] md:min-h-[400px] flex items-center justify-center p-8 relative"
          :class="creation.output_image_url && !regenerating ? 'cursor-none' : ''"
          @mousemove="onPreviewMouseMove"
          @mouseleave="onPreviewMouseLeave"
        >
          <!-- Status badge -->
          <span
            class="absolute top-4 left-4 z-10 flex items-center gap-1.5 px-2.5 py-1 rounded-lg font-sans text-[10px] font-medium"
            :class="{
              'bg-game-success/15 text-game-success': creation.status === 'completed',
              'bg-game-gold/15 text-game-gold': creation.status === 'processing' || creation.status === 'pending',
              'bg-red-500/15 text-red-400': creation.status === 'failed',
            }"
          >
            <span class="w-1.5 h-1.5 rounded-full" :class="{
              'bg-game-success': creation.status === 'completed',
              'bg-game-gold': creation.status === 'processing' || creation.status === 'pending',
              'bg-red-400': creation.status === 'failed',
            }"></span>
            {{ creation.status }}
          </span>

          <!-- Version tag -->
          <span class="absolute top-4 right-4 z-10 px-2 py-0.5 rounded-md font-mono text-[10px] font-medium"
            :class="creation.version === 0 ? 'bg-game-accent/15 text-game-accent' : 'bg-game-gold/15 text-game-gold'"
          >
            {{ creation.version === 0 ? 'original' : `v${creation.version}` }}
          </span>

          <!-- Lens zoom badge -->
          <button
            v-if="creation.output_image_url && !regenerating"
            class="absolute bottom-4 right-4 z-10 flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-game-dark/80 border border-white/10 font-mono text-[11px] text-slate-400 hover:text-white transition-none"
            @click.stop="cycleLensZoom"
          >
            <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" />
            </svg>
            {{ lensZoom }}x
          </button>

          <!-- Magnifying glass lens -->
          <div
            v-if="lensActive && creation.output_image_url && !regenerating"
            class="lens-glass pointer-events-none"
            :style="{
              left: `${lensX - LENS_SIZE / 2}px`,
              top: `${lensY - LENS_SIZE / 2}px`,
              width: `${LENS_SIZE}px`,
              height: `${LENS_SIZE}px`,
              backgroundImage: `url(${imageUrl(creation.output_image_url)})`,
              backgroundPosition: lensBackgroundPosition(),
              backgroundSize: lensBackgroundSize(),
            }"
          ></div>

          <!-- Image -->
          <img
            v-if="creation.output_image_url && !regenerating"
            ref="imageRef"
            :src="imageUrl(creation.output_image_url)"
            alt=""
            class="max-w-full max-h-[360px] object-contain image-rendering-pixelated"
            @error="($event.target as HTMLImageElement).style.display = 'none'"
          />
          <img
            v-else-if="regenerating"
            src="/assets/loading.webp"
            alt="Regenerating..."
            class="w-16 h-16 animate-spin"
          />
          <div v-else class="flex flex-col items-center gap-2 text-slate-500">
            <svg class="w-12 h-12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0 0 22.5 18.75V5.25A2.25 2.25 0 0 0 20.25 3H3.75A2.25 2.25 0 0 0 1.5 5.25v13.5A2.25 2.25 0 0 0 3.75 21Z" />
            </svg>
            <p class="font-sans text-sm">{{ creation.status === 'failed' ? 'Generation failed' : 'No image' }}</p>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-[1fr_320px] gap-8">
        <!-- Left: Info + Actions -->
        <div>
          <!-- Description -->
          <h2 class="font-sans text-xl font-semibold text-white mb-2">{{ creation.description }}</h2>

          <!-- Meta -->
          <div class="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm mb-6">
            <span class="px-2 py-0.5 rounded-md font-sans text-[10px] font-medium uppercase tracking-wider bg-white/5 text-slate-400">{{ creation.category }}</span>
            <span class="font-mono text-[11px] text-slate-500">{{ creation.width }}×{{ creation.height }}px</span>
            <span class="w-px h-3 bg-white/10"></span>
            <span class="font-sans text-[11px] text-slate-500 capitalize">{{ creation.direction === 'none' ? 'No direction' : creation.direction }}</span>
            <span class="w-px h-3 bg-white/10"></span>
            <span class="font-sans text-[11px] text-slate-500">{{ creation.transparent_bg ? 'Transparent' : 'Solid' }}</span>
            <span class="w-px h-3 bg-white/10"></span>
            <span class="font-sans text-[11px] text-slate-600">{{ new Date(creation.created_at).toLocaleString() }}</span>
          </div>

          <!-- Actions -->
          <div class="flex flex-wrap gap-3">
            <!-- Redo (same prompt) -->
            <!-- <button
              class="flex items-center gap-2 px-4 py-2.5 rounded-xl font-sans text-sm font-medium border transition-none"
              :class="regenerating ? 'border-white/5 text-slate-600 cursor-not-allowed' : 'border-white/10 text-slate-400 hover:text-white hover:border-white/20'"
              :disabled="regenerating"
              @click="handleRegenerate()"
            >
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182M20.995 4.365v4.99" />
              </svg>
              Regenerate
            </button> -->

            <!-- Edit + Regenerate -->
            <button
              class="flex items-center gap-2 px-4 py-2.5 rounded-xl font-sans text-sm font-medium border transition-none"
              :class="regenerating ? 'border-white/5 text-slate-600 cursor-not-allowed' : 'border-white/10 text-slate-400 hover:text-white hover:border-white/20'"
              :disabled="regenerating"
              @click="openEdit"
            >
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Z" />
              </svg>
              Edit &amp; Regenerate
            </button>
          </div>

          <!-- Edit prompt inline -->
          <div v-if="showEditPrompt" class="mt-4 p-4 rounded-xl border border-white/10 bg-white/[0.02]">
            <span class="font-sans text-xs font-medium text-slate-400 uppercase tracking-wider mb-1.5 block">New description</span>
            <textarea
              v-model="editDescription"
              rows="3"
              class="w-full px-4 py-3 rounded-xl border bg-white/5 border-white/10 font-sans text-sm text-white placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-game-accent/40 focus:border-game-accent/60 transition-none resize-none mb-3"
            ></textarea>
            <div class="flex items-center gap-2">
              <button
                class="flex items-center gap-1.5 px-4 py-2 rounded-xl font-sans text-sm font-medium text-white bg-game-accent hover:bg-game-accent/90 transition-none"
                :disabled="!editDescription.trim()"
                @click="handleRegenerate(editDescription.trim())"
              >
                <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09Z" />
                </svg>
                Generate New Version
              </button>
              <button
                class="px-4 py-2 rounded-xl font-sans text-sm text-slate-400 hover:text-white border border-white/10 transition-none"
                @click="showEditPrompt = false"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>

        <!-- Right: Version History -->
        <div>
          <h3 class="font-sans text-sm font-medium text-slate-400 mb-3">
            Versions <span class="text-slate-600">({{ versions.length }})</span>
          </h3>
          <div class="space-y-2">
            <button
              v-for="v in versions"
              :key="v.id"
              class="w-full flex items-center gap-3 p-3 rounded-xl border transition-none text-left"
              :class="v.id === creation.id
                ? 'border-game-accent/40 bg-game-accent/5'
                : 'border-white/10 bg-white/[0.02] hover:border-white/20'"
              @click="switchVersion(v)"
            >
              <!-- Thumbnail -->
              <div class="w-12 h-12 rounded-lg checkerboard-bg flex items-center justify-center flex-shrink-0 overflow-hidden">
                <img
                  v-if="v.output_image_url"
                  :src="imageUrl(v.output_image_url)"
                  alt=""
                  class="max-w-full max-h-full object-contain image-rendering-pixelated"
                  @error="($event.target as HTMLImageElement).style.display = 'none'"
                />
                <img
                  v-else-if="v.status === 'pending' || v.status === 'processing'"
                  src="/assets/loading.webp"
                  alt="..."
                  class="w-6 h-6 animate-spin"
                />
                <span v-else class="font-mono text-[8px] text-slate-600">--</span>
              </div>

              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-1.5 mb-0.5">
                  <span
                    class="px-1.5 py-0.5 rounded font-mono text-[9px] font-medium"
                    :class="v.version === 0 ? 'bg-game-accent/15 text-game-accent' : 'bg-game-gold/15 text-game-gold'"
                  >{{ v.version === 0 ? 'original' : `v${v.version}` }}</span>
                  <span
                    class="flex items-center gap-1 text-[9px] font-medium"
                    :class="{
                      'text-game-success': v.status === 'completed',
                      'text-game-gold': v.status === 'processing' || v.status === 'pending',
                      'text-red-400': v.status === 'failed',
                    }"
                  >
                    <span class="w-1 h-1 rounded-full" :class="{
                      'bg-game-success': v.status === 'completed',
                      'bg-game-gold': v.status === 'processing' || v.status === 'pending',
                      'bg-red-400': v.status === 'failed',
                    }"></span>
                    {{ v.status }}
                  </span>
                </div>
                <p class="font-sans text-[11px] text-slate-400 truncate">{{ v.description }}</p>
              </div>
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.image-rendering-pixelated {
  image-rendering: pixelated;
}

.lens-glass {
  position: absolute;
  z-index: 20;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.3);
  box-shadow:
    0 0 0 1px rgba(0, 0, 0, 0.4),
    0 4px 16px rgba(0, 0, 0, 0.5),
    inset 0 0 20px rgba(255, 255, 255, 0.05);
  image-rendering: pixelated;
  background-repeat: no-repeat;
}
</style>
