<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import AppNavbar from '../components/AppNavbar.vue'
import { useCreationsStore, categoryDirectionMapping, type CreationCategory } from '../stores/creations'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const isDark = ref(true)
const store = useCreationsStore()

onMounted(async () => {
  await store.fetchCreations()
  // Resume polling for in-progress items
  for (const item of store.items) {
    if (item.status === 'pending' || item.status === 'processing') {
      store.pollCreation(item.id)
    }
  }
})

// ── Form state ──
const description = ref('')
const category = ref<CreationCategory>('other')
const direction = ref(categoryDirectionMapping['other'][0]!.value)
const width = ref(64)
const height = ref(64)
const transparent = ref(false)
const referenceFile = ref<File | null>(null)
const refDragOver = ref(false)
const lockAspect = ref(true)
const submitted = ref(false)

const categoryOptions: { value: CreationCategory; label: string }[] = [
  { value: 'character', label: 'Character' },
  { value: 'background', label: 'Background' },
  { value: 'place', label: 'Place' },
  { value: 'environment', label: 'Environment' },
  { value: 'item', label: 'Item' },
  { value: 'other', label: 'Other' },
]

const directionOptions = computed(() => categoryDirectionMapping[category.value])

// Reset direction when category changes
watch(category, () => {
  const options = categoryDirectionMapping[category.value]
  direction.value = options[0]?.value ?? 'none'
})

const presetSizes = [
  { label: '32×32', w: 32, h: 32 },
  { label: '64×64', w: 64, h: 64 },
  { label: '128×128', w: 128, h: 128 },
  { label: '256×256', w: 256, h: 256 },
  { label: '320×180', w: 320, h: 180 },
  { label: '480×270', w: 480, h: 270 },
]

const activePreset = computed(() =>
  presetSizes.find((p) => p.w === width.value && p.h === height.value) ?? null,
)

const canGenerate = computed(() => !!description.value.trim())

function applyPreset(p: { w: number; h: number }) {
  width.value = p.w
  height.value = p.h
}

function onWidthChange(val: number) {
  width.value = val
  if (lockAspect.value) height.value = val
}

function onHeightChange(val: number) {
  height.value = val
  if (lockAspect.value) width.value = val
}

// ── File handling ──
function handleFileDrop(e: DragEvent) {
  e.preventDefault()
  refDragOver.value = false
  const file = e.dataTransfer?.files[0]
  if (file?.type.startsWith('image/')) referenceFile.value = file
}

function handleFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) referenceFile.value = file
}

function removeFile() {
  referenceFile.value = null
}

// ── Generate ──
async function handleGenerate() {
  submitted.value = true
  if (!canGenerate.value) return

  const result = await store.createCreation(
    {
      description: description.value.trim(),
      category: category.value,
      direction: direction.value,
      width: width.value,
      height: height.value,
      transparent_bg: transparent.value,
    },
    referenceFile.value,
  )

  if (!result) return

  // Poll for completion
  store.pollCreation(result.id)

  // Reset form
  description.value = ''
  category.value = 'other'
  direction.value = 'none'
  width.value = 64
  height.value = 64
  transparent.value = false
  referenceFile.value = null
  submitted.value = false
}

function imageUrl(path: string | null): string {
  if (!path) return ''
  if (path.startsWith('http')) return path
  return `${API_URL}${path}`
}
</script>

<template>
  <div class="min-h-screen w-full bg-game-dark text-slate-200">
    <AppNavbar v-model:is-dark="isDark" />

    <main class="mx-auto max-w-6xl px-4 pt-16 pb-8 md:px-8 md:pt-20 md:pb-12">

      <!-- Page header -->
      <div class="mb-8">
        <h1 class="font-sans text-2xl font-semibold text-white mb-1">Creation Studio</h1>
        <p class="font-sans text-sm text-slate-400">Generate pixel art — characters, backgrounds, places, and more</p>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-8">

        <!-- ═══════════ LEFT: History ═══════════ -->
        <div>
          <div class="flex items-center justify-between mb-4">
            <h2 class="font-sans text-sm font-medium text-slate-400">Recent creations</h2>
            <span class="font-sans text-xs text-slate-600">{{ store.items.length }} items</span>
          </div>

          <div v-if="store.items.length" class="space-y-3">
            <RouterLink
              v-for="item in store.items"
              :key="item.id"
              :to="`/creation/${item.id}`"
              class="flex gap-4 p-4 rounded-xl border border-white/10 bg-white/[0.02] hover:border-white/20 transition-none no-underline block cursor-pointer"
            >
              <!-- Preview -->
              <div
                class="checkerboard-bg rounded-lg flex items-center justify-center flex-shrink-0 border border-white/5 overflow-hidden"
                :style="{ width: '80px', height: '80px' }"
              >
                <img
                  v-if="item.output_image_url"
                  :src="imageUrl(item.output_image_url)"
                  alt=""
                  class="max-w-full max-h-full object-contain image-rendering-pixelated"
                  @error="($event.target as HTMLImageElement).style.display = 'none'"
                />
                <img
                  v-else-if="item.status === 'pending' || item.status === 'processing'"
                  src="/assets/loading.webp"
                  alt="Generating..."
                  class="w-8 h-8 animate-spin"
                />
                <div
                  v-else-if="item.status === 'failed'"
                  class="w-full h-full flex items-center justify-center"
                >
                  <svg class="w-6 h-6 text-red-400/60" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
                  </svg>
                </div>
                <div
                  v-else
                  class="bg-game-dark/50 border border-white/10 rounded flex items-center justify-center"
                  :style="{
                    width: `${Math.min(item.width / (item.width > 128 ? 6 : 2), 56)}px`,
                    height: `${Math.min(item.height / (item.height > 128 ? 6 : 2), 56)}px`,
                  }"
                >
                  <span class="font-mono text-[8px] text-slate-600">{{ item.width }}×{{ item.height }}</span>
                </div>
              </div>

              <!-- Info -->
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-1">
                  <span class="px-2 py-0.5 rounded-md font-sans text-[10px] font-medium uppercase tracking-wider bg-white/5 text-slate-400">
                    {{ item.category }}
                  </span>
                  <span
                    class="flex items-center gap-1 px-2 py-0.5 rounded-md font-sans text-[10px] font-medium"
                    :class="{
                      'bg-game-success/15 text-game-success': item.status === 'completed',
                      'bg-game-gold/15 text-game-gold': item.status === 'processing' || item.status === 'pending',
                      'bg-red-500/15 text-red-400': item.status === 'failed',
                    }"
                  >
                    <span class="w-1.5 h-1.5 rounded-full" :class="{
                      'bg-game-success': item.status === 'completed',
                      'bg-game-gold': item.status === 'processing' || item.status === 'pending',
                      'bg-red-400': item.status === 'failed',
                    }"></span>
                    {{ item.status === 'pending' ? 'queued' : item.status }}
                  </span>
                </div>
                <p class="font-sans text-sm text-white line-clamp-2">{{ item.description }}</p>
                <div class="flex items-center gap-3 mt-2">
                  <span class="font-mono text-[11px] text-slate-500">{{ item.width }}×{{ item.height }}px</span>
                  <span class="w-px h-3 bg-white/10"></span>
                  <span class="font-sans text-[11px] text-slate-500 capitalize">{{ item.direction === 'none' ? '—' : item.direction }}</span>
                  <span class="w-px h-3 bg-white/10"></span>
                  <span class="font-sans text-[11px] text-slate-500">{{ item.transparent_bg ? 'Transparent' : 'Solid' }}</span>
                  <span class="w-px h-3 bg-white/10"></span>
                  <span class="font-sans text-[11px] text-slate-600">{{ new Date(item.created_at).toLocaleDateString() }}</span>
                </div>
              </div>

              <!-- Download button for completed -->
              <div v-if="item.status === 'completed' && item.output_image_url" class="flex items-center flex-shrink-0">
                <a
                  :href="imageUrl(item.output_image_url)"
                  download
                  class="p-2 rounded-lg text-slate-500 hover:text-white hover:bg-white/5 transition-none no-underline"
                  title="Download"
                >
                  <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
                  </svg>
                </a>
              </div>
            </RouterLink>
          </div>

          <div v-else class="flex flex-col items-center justify-center py-16 text-center">
            <p class="font-sans text-sm text-slate-400 mb-1">No creations yet</p>
            <p class="font-sans text-xs text-slate-600">Use the form to generate your first pixel art</p>
          </div>
        </div>

        <!-- ═══════════ RIGHT: Create Form ═══════════ -->
        <div class="lg:sticky lg:top-20 lg:self-start">
          <div class="rounded-2xl border border-white/10 bg-white/[0.02] overflow-hidden">
            <!-- Header -->
            <div class="h-1 w-full bg-gradient-to-r from-transparent via-game-accent to-transparent"></div>
            <div class="px-5 py-4 border-b border-white/5">
              <h2 class="font-sans text-base font-semibold text-white">New Creation</h2>
              <p class="font-sans text-xs text-slate-500 mt-0.5">Describe what you want to generate</p>
            </div>

            <!-- Error -->
            <div
              v-if="store.error"
              class="mx-5 mt-4 flex items-center gap-2 font-sans text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded-xl px-3 py-2"
            >
              <svg class="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10" /><path d="M12 8v4m0 4h.01" />
              </svg>
              {{ store.error }}
            </div>

            <div class="p-5 space-y-5">
              <!-- Description -->
              <label class="block">
                <span class="font-sans text-xs font-medium text-slate-400 uppercase tracking-wider mb-1.5 block">
                  Description <span class="text-red-400">*</span>
                </span>
                <textarea
                  v-model="description"
                  rows="3"
                  placeholder="A fantasy forest background with distant mountains and a glowing sunset..."
                  class="w-full px-4 py-3 rounded-xl border bg-white/5 font-sans text-sm text-white placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-game-accent/40 focus:border-game-accent/60 transition-none resize-none"
                  :class="submitted && !description.trim() ? 'border-red-400/60' : 'border-white/10'"
                ></textarea>
                <p v-if="submitted && !description.trim()" class="font-sans text-[11px] text-red-400 mt-1">Description is required</p>
              </label>

              <!-- Category -->
              <label class="block">
                <span class="font-sans text-xs font-medium text-slate-400 uppercase tracking-wider mb-1.5 block">Category</span>
                <select
                  v-model="category"
                  class="w-full px-4 py-2.5 rounded-xl border bg-white/5 border-white/10 font-sans text-sm text-white focus:outline-none focus:ring-2 focus:ring-game-accent/40 focus:border-game-accent/60 transition-none appearance-none cursor-pointer"
                >
                  <option
                    v-for="opt in categoryOptions"
                    :key="opt.value"
                    :value="opt.value"
                    class="bg-game-dark text-white"
                  >
                    {{ opt.label }}
                  </option>
                </select>
              </label>

              <!-- Direction -->
              <label class="block">
                <span class="font-sans text-xs font-medium text-slate-400 uppercase tracking-wider mb-1.5 block">Direction</span>
                <select
                  v-model="direction"
                  class="w-full px-4 py-2.5 rounded-xl border bg-white/5 border-white/10 font-sans text-sm text-white focus:outline-none focus:ring-2 focus:ring-game-accent/40 focus:border-game-accent/60 transition-none appearance-none cursor-pointer"
                >
                  <option
                    v-for="opt in directionOptions"
                    :key="opt.value"
                    :value="opt.value"
                    class="bg-game-dark text-white"
                  >
                    {{ opt.label }}
                  </option>
                </select>
              </label>

              <!-- Reference Image -->
              <div>
                <span class="font-sans text-xs font-medium text-slate-400 uppercase tracking-wider mb-1.5 block">
                  Reference Image <span class="text-slate-600 normal-case">(optional)</span>
                </span>
                <div
                  v-if="!referenceFile"
                  class="relative border-2 border-dashed rounded-xl p-5 text-center cursor-pointer transition-none"
                  :class="refDragOver
                    ? 'border-game-accent/60 bg-game-accent/5'
                    : 'border-white/10 hover:border-white/20'"
                  @dragover.prevent="refDragOver = true"
                  @dragleave="refDragOver = false"
                  @drop="handleFileDrop"
                >
                  <input type="file" accept="image/*" class="absolute inset-0 w-full h-full opacity-0 cursor-pointer" @change="handleFileSelect" />
                  <svg class="w-5 h-5 mx-auto mb-1 text-slate-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M12 16.5V9.75m0 0 3 3m-3-3-3 3M6.75 19.5a4.5 4.5 0 0 1-1.41-8.775 5.25 5.25 0 0 1 10.233-2.33 3 3 0 0 1 3.758 3.848A3.752 3.752 0 0 1 18 19.5H6.75Z" />
                  </svg>
                  <p class="font-sans text-xs text-slate-400">Drop or <span class="text-game-accent">browse</span></p>
                </div>
                <div v-else class="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/10">
                  <div class="w-8 h-8 rounded-lg bg-game-accent/10 flex items-center justify-center flex-shrink-0">
                    <svg class="w-4 h-4 text-game-accent" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                      <path d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0 0 22.5 18.75V5.25A2.25 2.25 0 0 0 20.25 3H3.75A2.25 2.25 0 0 0 1.5 5.25v13.5A2.25 2.25 0 0 0 3.75 21Z" />
                    </svg>
                  </div>
                  <div class="flex-1 min-w-0">
                    <p class="font-sans text-xs text-white truncate">{{ referenceFile.name }}</p>
                    <p class="font-sans text-[10px] text-slate-500">{{ (referenceFile.size / 1024).toFixed(1) }} KB</p>
                  </div>
                  <button class="text-slate-500 hover:text-red-400 transition-none p-1" @click="removeFile">
                    <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 18L18 6M6 6l12 12"/></svg>
                  </button>
                </div>
              </div>

              <!-- Size: Presets -->
              <div>
                <span class="font-sans text-xs font-medium text-slate-400 uppercase tracking-wider mb-2 block">Size</span>
                <div class="flex flex-wrap gap-1.5 mb-3">
                  <button
                    v-for="p in presetSizes"
                    :key="p.label"
                    class="px-3 py-1.5 rounded-lg font-mono text-[11px] font-medium border transition-none"
                    :class="activePreset?.label === p.label
                      ? 'bg-game-accent/15 border-game-accent/40 text-game-accent'
                      : 'bg-white/5 border-white/5 text-slate-400 hover:text-white hover:border-white/10'"
                    @click="applyPreset(p)"
                  >
                    {{ p.label }}
                  </button>
                </div>
                <!-- Width + Height inputs -->
                <div class="flex items-center gap-2">
                  <label class="flex-1">
                    <span class="font-sans text-[10px] text-slate-500 uppercase block mb-1">Width (px)</span>
                    <input
                      type="number"
                      :value="width"
                      min="16"
                      max="1024"
                      step="1"
                      class="w-full px-3 py-2 rounded-lg border bg-white/5 border-white/10 font-mono text-sm text-white focus:outline-none focus:ring-2 focus:ring-game-accent/40 focus:border-game-accent/60 transition-none"
                      @input="onWidthChange(Number(($event.target as HTMLInputElement).value))"
                    />
                  </label>
                  <!-- Lock aspect ratio -->
                  <button
                    class="mt-4 p-1.5 rounded-lg border transition-none"
                    :class="lockAspect
                      ? 'border-game-accent/40 text-game-accent bg-game-accent/10'
                      : 'border-white/10 text-slate-500 hover:text-white'"
                    @click="lockAspect = !lockAspect"
                    title="Lock aspect ratio"
                  >
                    <svg v-if="lockAspect" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                    <svg v-else class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 9.9-1"/></svg>
                  </button>
                  <label class="flex-1">
                    <span class="font-sans text-[10px] text-slate-500 uppercase block mb-1">Height (px)</span>
                    <input
                      type="number"
                      :value="height"
                      min="16"
                      max="1024"
                      step="1"
                      class="w-full px-3 py-2 rounded-lg border bg-white/5 border-white/10 font-mono text-sm text-white focus:outline-none focus:ring-2 focus:ring-game-accent/40 focus:border-game-accent/60 transition-none"
                      @input="onHeightChange(Number(($event.target as HTMLInputElement).value))"
                    />
                  </label>
                </div>
              </div>

              <!-- Transparent -->
              <label class="flex items-center gap-3 cursor-pointer select-none">
                <div
                  class="w-5 h-5 rounded-md border-2 flex items-center justify-center transition-none"
                  :class="transparent
                    ? 'bg-game-accent border-game-accent'
                    : 'bg-white/5 border-white/20'"
                >
                  <svg v-if="transparent" class="w-3 h-3 text-game-dark" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>
                </div>
                <input v-model="transparent" type="checkbox" class="sr-only" />
                <div>
                  <span class="font-sans text-sm text-white">Transparent background</span>
                  <p class="font-sans text-[11px] text-slate-500">Remove background for sprites and overlays</p>
                </div>
              </label>

              <!-- Generate button -->
              <button
                class="w-full flex items-center justify-center gap-2 py-3 rounded-xl font-sans text-sm font-semibold text-white transition-none mt-2"
                :class="store.generating || !canGenerate ? 'bg-game-accent/30 cursor-not-allowed' : 'bg-game-accent hover:bg-game-accent/90'"
                :disabled="store.generating || !canGenerate"
                style="text-shadow: 0 1px 2px rgba(0,0,0,0.3);"
                @click="handleGenerate"
              >
                <svg v-if="!store.generating" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 0 0-2.455 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" />
                </svg>
                <svg v-else class="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 2v4m0 12v4m-7.07-3.93l2.83-2.83m8.48-8.48l2.83-2.83M2 12h4m12 0h4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83" />
                </svg>
                {{ store.generating ? 'Generating...' : 'Generate' }}
              </button>
            </div>
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
</style>
