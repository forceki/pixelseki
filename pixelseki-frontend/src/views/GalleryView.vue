<script setup lang="ts">
import { ref, onMounted } from 'vue'
import AppNavbar from '../components/AppNavbar.vue'
import { apiFetch } from '../lib/api'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const isDark = ref(true)

interface GalleryItem {
  id: string
  source: 'creation' | 'generation'
  description: string
  output_image_url: string
  width: number | null
  height: number | null
  created_at: string
}

interface GalleryResponse {
  items: GalleryItem[]
  total: number
  has_more: boolean
}

const items = ref<GalleryItem[]>([])
const total = ref(0)
const hasMore = ref(false)
const loading = ref(true)
const loadingMore = ref(false)
const PAGE_SIZE = 30

// Lightbox
const lightboxItem = ref<GalleryItem | null>(null)

function imageUrl(path: string): string {
  if (path.startsWith('http')) return path
  return `${API_URL}${path}`
}

async function fetchGallery(offset = 0) {
  try {
    const data = await apiFetch<GalleryResponse>(
      `/api/v1/gallery?limit=${PAGE_SIZE}&offset=${offset}`,
    )
    if (offset === 0) {
      items.value = data.items
    } else {
      items.value.push(...data.items)
    }
    total.value = data.total
    hasMore.value = data.has_more
  } catch {
    // silent — gallery is best-effort
  }
}

async function loadMore() {
  loadingMore.value = true
  await fetchGallery(items.value.length)
  loadingMore.value = false
}

const imageLoaded = ref<Set<string>>(new Set())

function onImageLoad(id: string) {
  imageLoaded.value.add(id)
}

async function downloadImage(item: GalleryItem, e: Event) {
  e.stopPropagation()
  const url = imageUrl(item.output_image_url)
  const res = await fetch(url)
  const blob = await res.blob()
  const blobUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = blobUrl
  const name = item.description.slice(0, 30).replace(/[^a-zA-Z0-9 -_]/g, '_').trim()
  a.download = `${name}.png`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(blobUrl)
}

function openLightbox(item: GalleryItem) {
  lightboxItem.value = item
}

function closeLightbox() {
  lightboxItem.value = null
}

onMounted(async () => {
  await fetchGallery()
  loading.value = false
})
</script>

<template>
  <div class="min-h-screen w-full bg-game-dark text-slate-200">
    <AppNavbar v-model:is-dark="isDark" />

    <main class="mx-auto max-w-6xl px-4 pt-16 pb-8 md:px-8 md:pt-20 md:pb-12">

      <!-- Page header -->
      <div class="mb-8">
        <h1 class="font-sans text-2xl font-semibold text-white mb-1">Gallery</h1>
        <p class="font-sans text-sm text-slate-400">
          All pixel art generated on PixelSeki
          <span v-if="!loading" class="text-slate-600">— {{ total }} images</span>
        </p>
      </div>

      <!-- Loading skeleton -->
      <div v-if="loading" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
        <div
          v-for="i in 15"
          :key="i"
          class="aspect-square rounded-xl bg-white/[0.03] border border-white/5 animate-pulse"
        ></div>
      </div>

      <!-- Empty state -->
      <div v-else-if="!items.length" class="flex flex-col items-center justify-center py-24 text-center">
        <svg class="w-12 h-12 text-slate-600 mb-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0 0 22.5 18.75V5.25A2.25 2.25 0 0 0 20.25 3H3.75A2.25 2.25 0 0 0 1.5 5.25v13.5A2.25 2.25 0 0 0 3.75 21Z" />
        </svg>
        <p class="font-sans text-sm text-slate-400">No images yet</p>
        <p class="font-sans text-xs text-slate-600 mt-1">Generated pixel art will appear here</p>
      </div>

      <!-- Image grid -->
      <div v-else>
        <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
          <button
            v-for="item in items"
            :key="item.id"
            class="group relative aspect-square rounded-xl border border-white/10 bg-white/[0.02] overflow-hidden transition-none hover:border-white/25 cursor-pointer"
            @click="openLightbox(item)"
          >
            <!-- Loading shimmer -->
            <div
              v-if="!imageLoaded.has(item.id)"
              class="absolute inset-0 bg-white/[0.03] animate-pulse"
            ></div>

            <!-- Image -->
            <img
              :src="imageUrl(item.output_image_url)"
              alt=""
              class="w-full h-full object-cover image-rendering-pixelated"
              :class="imageLoaded.has(item.id) ? 'opacity-100' : 'opacity-0'"
              loading="lazy"
              @error="($event.target as HTMLImageElement).style.display = 'none'"
              @load="onImageLoad(item.id)"
            />

            <!-- Hover overlay -->
            <div class="absolute inset-0 bg-black/0 group-hover:bg-black/50 flex items-end p-2.5 opacity-0 group-hover:opacity-100">
              <div class="w-full flex items-end justify-between gap-2">
                <div class="min-w-0">
                  <p class="font-sans text-[11px] text-white line-clamp-2 leading-tight">{{ item.description }}</p>
                  <div class="flex items-center gap-2 mt-1">
                    <span
                      class="px-1.5 py-0.5 rounded font-sans text-[9px] font-medium uppercase"
                      :class="item.source === 'creation'
                        ? 'bg-game-sakura/20 text-game-sakura'
                        : 'bg-game-accent/20 text-game-accent'"
                    >{{ item.source === 'creation' ? 'creation' : 'sprite' }}</span>
                    <span v-if="item.width" class="font-mono text-[9px] text-slate-400">{{ item.width }}×{{ item.height }}</span>
                  </div>
                </div>
                <button
                  class="flex-shrink-0 p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-white/10 transition-none"
                  title="Download"
                  @click="downloadImage(item, $event)"
                >
                  <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
                  </svg>
                </button>
              </div>
            </div>
          </button>
        </div>

        <!-- Load more -->
        <div v-if="hasMore" class="flex justify-center mt-8">
          <button
            class="flex items-center gap-2 px-6 py-2.5 rounded-xl font-sans text-sm font-medium border border-white/10 text-slate-400 hover:text-white hover:border-white/20 transition-none"
            :disabled="loadingMore"
            @click="loadMore"
          >
            <svg v-if="loadingMore" class="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2v4m0 12v4m-7.07-3.93l2.83-2.83m8.48-8.48l2.83-2.83M2 12h4m12 0h4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83" />
            </svg>
            {{ loadingMore ? 'Loading...' : 'Load more' }}
          </button>
        </div>
      </div>
    </main>

    <!-- Lightbox -->
    <Teleport to="body">
      <div
        v-if="lightboxItem"
        class="fixed inset-0 z-[999] flex items-center justify-center px-4 bg-black/80 backdrop-blur-md"
        @click.self="closeLightbox"
      >
        <div class="relative max-w-3xl w-full">
          <!-- Close button -->
          <button
            class="absolute -top-10 right-0 w-8 h-8 flex items-center justify-center rounded-full text-slate-400 hover:text-white hover:bg-white/10 transition-none"
            @click="closeLightbox"
          >
            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>

          <!-- Image -->
          <div class="rounded-2xl border border-white/10 bg-game-dark overflow-hidden">
            <div class="checkerboard-bg flex items-center justify-center p-6 min-h-[300px]">
              <img
                :src="imageUrl(lightboxItem.output_image_url)"
                alt=""
                class="max-w-full max-h-[60vh] object-contain image-rendering-pixelated"
                @error="($event.target as HTMLImageElement).style.display = 'none'"
              />
            </div>

            <!-- Info -->
            <div class="px-5 py-4 border-t border-white/5 flex items-start justify-between gap-4">
              <div>
                <p class="font-sans text-sm text-white mb-2">{{ lightboxItem.description }}</p>
                <div class="flex items-center gap-3">
                  <span
                    class="px-2 py-0.5 rounded-md font-sans text-[10px] font-medium uppercase tracking-wider"
                    :class="lightboxItem.source === 'creation'
                      ? 'bg-game-sakura/15 text-game-sakura'
                      : 'bg-game-accent/15 text-game-accent'"
                  >{{ lightboxItem.source === 'creation' ? 'creation' : 'sprite' }}</span>
                  <span v-if="lightboxItem.width" class="font-mono text-[11px] text-slate-500">{{ lightboxItem.width }}×{{ lightboxItem.height }}px</span>
                  <span class="font-sans text-[11px] text-slate-600">{{ new Date(lightboxItem.created_at).toLocaleDateString() }}</span>
                </div>
              </div>
              <button
                class="flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-sans text-xs font-medium text-slate-300 hover:text-white border border-white/10 hover:border-white/20 transition-none"
                @click="downloadImage(lightboxItem, $event)"
              >
                <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
                </svg>
                Download
              </button>
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
</style>
