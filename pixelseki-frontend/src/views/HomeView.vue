<script setup lang="ts">
import { ref, watch, nextTick, onMounted, onUnmounted } from 'vue'
import AppNavbar from '../components/AppNavbar.vue'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()

// ── Time-based theme ──
function getIsNight(): boolean {
  const h = new Date().getHours()
  return h < 6 || h >= 18
}

const isDark = ref(getIsNight())

// ── Live clock ──
const currentTime = ref('')
const currentDate = ref('')
let clockTimer: ReturnType<typeof setInterval> | undefined

function updateClock() {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
  currentDate.value = now.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
}

onMounted(() => {
  updateClock()
  clockTimer = setInterval(updateClock, 1000)
})

onUnmounted(() => {
  clearInterval(clockTimer)
})

// ── Login Modal ──
const loginModalOpen = ref(false)
const loginGoogleBtn = ref<HTMLDivElement | null>(null)

function openLogin() {
  loginModalOpen.value = true
}

function closeLogin() {
  loginModalOpen.value = false
}

// ── Creation showcase cycling ──
const TOTAL_CREATIONS = 5
const currentCreation = ref(1)
let creationInterval: ReturnType<typeof setInterval>

onMounted(() => {
  creationInterval = setInterval(() => {
    currentCreation.value = (currentCreation.value % TOTAL_CREATIONS) + 1
  }, 5000)
})

onUnmounted(() => {
  clearInterval(creationInterval)
})

// Render Google button when modals open
watch(loginModalOpen, async (open) => {
  if (open) {
    await nextTick()
    if (loginGoogleBtn.value) {
      authStore.renderGoogleButton(loginGoogleBtn.value)
    }
  }
})

// Close modal on successful login
watch(() => authStore.isAuthenticated, (authenticated) => {
  if (authenticated) {
    loginModalOpen.value = false
  }
})
</script>

<template>
  <div
    data-scroll-root
    class="min-h-screen w-full overflow-y-auto overflow-x-hidden"
    :class="isDark ? 'bg-game-dark' : 'bg-[#1a0a2e]'"
  >
    <!-- ===== NAVBAR ===== -->
    <AppNavbar v-model:is-dark="isDark" @login="openLogin" />

    <!-- ===== HERO SECTION ===== -->
    <section class="relative w-full min-h-screen flex items-end justify-center pb-24 md:pb-32">
      <!-- Background Image -->
      <div class="absolute inset-0 z-0" :class="isDark ? 'hero-bg-dark' : 'hero-bg-light'"></div>

      <!-- Gradient overlay — heavier at bottom for text -->
      <div
        class="absolute inset-0 z-[1]"
        :class="isDark
          ? 'bg-gradient-to-t from-game-dark via-game-dark/50 to-transparent'
          : 'bg-gradient-to-t from-[#1a0a2e] via-[#1a0a2e]/50 to-transparent'"
      ></div>

      <!-- Scanline overlay -->
      <div class="scanline-light z-[2]"></div>

      <!-- Time display — top right corner -->
      <div class="absolute top-20 right-6 md:right-10 z-10 text-right">
        <p
          class="font-mono text-4xl md:text-5xl font-bold tracking-tight"
          :class="isDark ? 'text-white/80' : 'text-white/80'"
        >{{ currentTime }}</p>
        <p
          class="font-sans text-sm md:text-base mt-1 uppercase tracking-wider"
          :class="isDark ? 'text-slate-400' : 'text-purple-300'"
        >{{ currentDate }}</p>
      </div>

      <!-- Content — bottom center -->
      <div class="relative z-10 w-full max-w-4xl px-6 text-center">
        <!-- Main Heading -->
        <h1 class="text-white uppercase mb-4">
          <span
            class="font-terminal text-5xl md:text-7xl lg:text-8xl block leading-none"
            :class="isDark ? 'text-glow-accent' : 'text-glow-sakura'"
          >Generate</span>
          <span
            class="font-pixel text-base md:text-xl lg:text-2xl block mt-2 mb-1"
            :class="isDark ? 'text-game-accent text-glow-accent' : 'text-game-sakura text-glow-sakura'"
          >PIXEL ART</span>
          <span
            class="font-terminal text-4xl md:text-5xl lg:text-6xl block leading-none"
            :class="isDark ? 'text-glow-accent' : 'text-glow-sakura'"
          >with AI</span>
        </h1>

        <!-- Subheading -->
        <p
          class="font-terminal text-xl md:text-2xl leading-relaxed mb-8 max-w-xl mx-auto"
          :class="isDark ? 'text-slate-300/90' : 'text-purple-200/90'"
        >
          Transform ideas into pixel art sprites, tilesets, and game assets. No drawing skills needed.
        </p>

        <!-- CTA Button -->
        <RouterLink
          v-if="authStore.isAuthenticated"
          to="/objects"
          class="inline-block font-terminal text-2xl text-game-dark uppercase border-4 border-black px-10 py-3 tracking-wider shadow-[5px_5px_0px_0px_rgba(0,0,0,1)] hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:translate-x-[3px] hover:translate-y-[3px] active:shadow-none active:translate-x-[5px] active:translate-y-[5px] transition-none select-none rounded-none no-underline"
          :class="isDark ? 'bg-[#39ff14]' : 'bg-game-sakura'"
        >
          &#9654; PLAY NOW
        </RouterLink>
        <button
          v-else
          class="font-terminal text-2xl text-game-dark uppercase border-4 border-black px-10 py-3 tracking-wider shadow-[5px_5px_0px_0px_rgba(0,0,0,1)] hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:translate-x-[3px] hover:translate-y-[3px] active:shadow-none active:translate-x-[5px] active:translate-y-[5px] transition-none select-none rounded-none"
          :class="isDark ? 'bg-[#39ff14]' : 'bg-game-sakura'"
          @click="openLogin"
        >
          &#9654; PLAY NOW
        </button>
      </div>
    </section>

    <!-- ===== FEATURES SECTION ===== -->
    <section class="relative w-full px-4 py-16 md:py-24">
      <div class="mx-auto max-w-5xl">
        <h2
          class="font-terminal text-3xl md:text-4xl text-center text-white uppercase mb-12"
          :class="isDark ? 'text-glow-accent' : 'text-glow-sakura'"
        >
          &#9733; SELECT YOUR POWER-UP &#9733;
        </h2>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <!-- Feature Card 1 — Sprite Generator -->
          <div
            class="p-6 transition-none group"
            :class="
              isDark
                ? 'pixel-panel hover:border-game-accent'
                : 'pixel-panel-sunset hover:border-game-sakura'
            "
          >
            <div
              class="w-12 h-12 border-4 flex items-center justify-center mb-4 rounded-none"
              :class="
                isDark
                  ? 'border-game-accent bg-game-accent/10'
                  : 'border-game-sakura bg-game-sakura/10'
              "
            >
              <svg
                class="w-6 h-6"
                :class="isDark ? 'text-game-accent' : 'text-game-sakura'"
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
            </div>
            <h3 class="font-terminal text-xl text-white uppercase mb-2">Sprite Generator</h3>
            <p
              class="font-terminal text-base"
              :class="isDark ? 'text-slate-400' : 'text-purple-300'"
            >
              Create characters, items, and enemies from a text prompt. Export as PNG or sprite
              sheets.
            </p>
          </div>

          <!-- Feature Card 2 — Tileset Builder -->
          <div
            class="p-6 transition-none group"
            :class="
              isDark
                ? 'pixel-panel hover:border-game-sakura'
                : 'pixel-panel-sunset hover:border-game-accent'
            "
          >
            <div
              class="w-12 h-12 border-4 flex items-center justify-center mb-4 rounded-none"
              :class="
                isDark
                  ? 'border-game-sakura bg-game-sakura/10'
                  : 'border-game-accent bg-game-accent/10'
              "
            >
              <svg
                class="w-6 h-6"
                :class="isDark ? 'text-game-sakura' : 'text-game-accent'"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5" />
                <path d="M2 12l10 5 10-5" />
              </svg>
            </div>
            <h3 class="font-terminal text-xl text-white uppercase mb-2">Tileset Builder</h3>
            <p
              class="font-terminal text-base"
              :class="isDark ? 'text-slate-400' : 'text-purple-300'"
            >
              Generate seamless tile maps for platformers, RPGs, and top-down adventures.
            </p>
          </div>

          <!-- Feature Card 3 — Asset Detail -->
          <div
            class="p-6 transition-none group"
            :class="
              isDark
                ? 'pixel-panel hover:border-game-gold'
                : 'pixel-panel-sunset hover:border-game-gold'
            "
          >
            <div
              class="w-12 h-12 border-4 border-game-gold bg-game-gold/10 flex items-center justify-center mb-4 rounded-none"
            >
              <svg
                class="w-6 h-6 text-game-gold"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <path d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Z" />
                <path d="M19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />
              </svg>
            </div>
            <h3 class="font-terminal text-xl text-white uppercase mb-2">Asset Detail</h3>
            <p
              class="font-terminal text-base"
              :class="isDark ? 'text-slate-400' : 'text-purple-300'"
            >
              Edit prompts, regenerate individual directions, add new angles, and download ZIP bundles.
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- ===== AI PIXEL STUDIO ===== -->
    <section id="gallery" class="relative w-full px-4 py-16 md:py-24">
      <div class="mx-auto max-w-5xl space-y-20">

        <!-- 1. Sprite Generator -->
        <div class="flex flex-col md:flex-row items-center gap-8 md:gap-12">
          <div class="flex-1">
            <h3 class="font-sans text-2xl font-semibold text-white mb-3">Sprite Generator</h3>
            <p class="font-sans text-sm leading-relaxed" :class="isDark ? 'text-slate-400' : 'text-purple-300'">
              Create characters, items, and enemies from a text prompt. Generate multi-direction sprites with consistent style across all angles — front, back, left, right, and more.
            </p>
          </div>
          <div class="w-full md:w-[360px] flex-shrink-0 grid grid-cols-2 gap-2">
            <img src="/showcase/sprite-south.png" alt="South" class="w-full rounded-lg image-rendering-pixelated" />
            <img src="/showcase/sprite-east.png" alt="East" class="w-full rounded-lg image-rendering-pixelated" />
            <img src="/showcase/sprite-west.png" alt="West" class="w-full rounded-lg image-rendering-pixelated" />
            <img src="/showcase/sprite-north.png" alt="North" class="w-full rounded-lg image-rendering-pixelated" />
          </div>
        </div>

        <!-- 2. From Reference -->
        <div class="flex flex-col md:flex-row-reverse items-center gap-8 md:gap-12">
          <div class="flex-1">
            <h3 class="font-sans text-2xl font-semibold text-white mb-3">From Reference</h3>
            <p class="font-sans text-sm leading-relaxed" :class="isDark ? 'text-slate-400' : 'text-purple-300'">
              Upload a reference image and generate pixel art that matches its style, colors, and composition. Perfect for converting existing artwork into pixel art or maintaining consistency across assets.
            </p>
          </div>
          <div class="w-full md:w-[360px] flex-shrink-0 space-y-4">
            <div class="flex items-center gap-3">
              <img src="/showcase/from-ref-reference.png" alt="Reference" class="w-[45%] rounded-lg" />
              <svg class="w-5 h-5 flex-shrink-0 text-slate-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M5 12h14M13 5l7 7-7 7" />
              </svg>
              <img src="/showcase/from-ref-output.png" alt="Generated from reference" class="w-[45%] rounded-lg image-rendering-pixelated" />
            </div>
            <div class="flex items-center gap-3">
              <img src="/showcase/from-ref-reference-1.png" alt="Reference" class="w-[45%] rounded-lg" />
              <svg class="w-5 h-5 flex-shrink-0 text-slate-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M5 12h14M13 5l7 7-7 7" />
              </svg>
              <img src="/showcase/from-ref-output-1.png" alt="Generated from reference" class="w-[45%] rounded-lg image-rendering-pixelated" />
            </div>
          </div>
        </div>

        <!-- 3. Tileset Builder -->
        <div class="flex flex-col md:flex-row items-center gap-8 md:gap-12">
          <div class="flex-1">
            <h3 class="font-sans text-2xl font-semibold text-white mb-3">Tileset Builder</h3>
            <p class="font-sans text-sm leading-relaxed" :class="isDark ? 'text-slate-400' : 'text-purple-300'">
              Generate seamless tile maps for platformers, RPGs, and top-down adventures. Each tile shares the same art style and color palette for a cohesive tileset.
            </p>
          </div>
          <div class="w-full md:w-[360px] flex-shrink-0 grid grid-cols-3 gap-2">
            <img v-for="i in 6" :key="i" :src="`/showcase/tile-${i}.png`" :alt="`Tile ${i}`" class="w-full rounded-lg image-rendering-pixelated" />
          </div>
        </div>

        <!-- 4. Creation Studio -->
        <div class="flex flex-col md:flex-row-reverse items-center gap-8 md:gap-12">
          <div class="flex-1">
            <h3 class="font-sans text-2xl font-semibold text-white mb-3">Creation Studio</h3>
            <p class="font-sans text-sm leading-relaxed" :class="isDark ? 'text-slate-400' : 'text-purple-300'">
              Generate backgrounds, environments, places, and more with flexible canvas sizes. Choose category-specific perspectives and download as PNG or ZIP bundles.
            </p>
          </div>
          <div class="w-full md:w-[360px] flex-shrink-0 relative overflow-hidden rounded-xl" style="aspect-ratio: 1/1;">
            <img
              :src="`/showcase/creation-${currentCreation}.png`"
              alt="Creation showcase"
              class="absolute inset-0 w-full h-full rounded-xl object-cover image-rendering-pixelated creation-fade"
              :key="currentCreation"
            />
          </div>
        </div>

      </div>
    </section>

    <!-- ===== FOOTER ===== -->
    <footer
      class="w-full border-t-4 px-4 py-8"
      :class="isDark ? 'border-game-border' : 'border-[#4c1d95]'"
    >
      <div class="mx-auto max-w-5xl flex flex-col md:flex-row items-center justify-between gap-4">
        <p
          class="font-terminal text-base uppercase tracking-wider"
          :class="isDark ? 'text-slate-500' : 'text-purple-400'"
        >
          &copy; 2026 PIXELSEKI &mdash; ALL RIGHTS RESERVED
        </p>
        <div class="flex items-center gap-4">
          <a
            href="https://discord.gg/2N2tcZG9af"
            target="_blank"
            rel="noopener noreferrer"
            class="font-terminal text-sm uppercase tracking-wider flex items-center gap-2 transition-colors"
            :class="isDark ? 'text-slate-500 hover:text-indigo-400' : 'text-purple-400 hover:text-purple-600'"
          >
            JOIN OUR COMMUNITY
            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03z"/>
            </svg>
          </a>
          <a
            href="https://buymeacoffee.com/forceki"
            target="_blank"
            rel="noopener noreferrer"
            class="font-terminal text-sm uppercase tracking-wider flex items-center gap-2 transition-colors"
            :class="isDark ? 'text-slate-500 hover:text-yellow-400' : 'text-purple-400 hover:text-yellow-500'"
          >
            BUY ME A COFFEE
            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M20.216 6.415l-.132-.666c-.119-.598-.388-1.163-1.001-1.379-.197-.069-.42-.098-.57-.241-.152-.143-.196-.366-.231-.572-.065-.378-.125-.756-.192-1.133-.057-.325-.102-.69-.25-.987-.195-.4-.597-.634-.996-.788a5.723 5.723 0 00-.626-.194c-1-.263-2.05-.36-3.077-.416a25.834 25.834 0 00-3.7.062c-.915.083-1.88.184-2.75.5-.318.116-.646.256-.888.501-.297.302-.393.77-.177 1.146.154.267.415.456.692.58.36.162.737.284 1.123.366 1.075.238 2.189.331 3.287.37 1.218.05 2.437.01 3.65-.118.299-.033.598-.073.896-.119.352-.054.578-.513.474-.834-.124-.383-.457-.531-.834-.473-.466.074-.96.108-1.382.146-1.177.08-2.358.082-3.536.006a22.228 22.228 0 01-1.157-.107c-.086-.01-.18-.025-.258-.036-.243-.036-.484-.08-.724-.13-.111-.027-.111-.185 0-.212h.005c.277-.06.557-.108.838-.147h.002c.131-.009.263-.032.394-.048a25.076 25.076 0 013.426-.12c.674.019 1.347.062 2.014.13l.04.005c.11.01.234.016.347.023.11.007.15-.123.07-.18-.063-.044-.138-.068-.213-.088a10.856 10.856 0 00-.738-.164 25.39 25.39 0 00-1.81-.243c-.096-.007-.189-.019-.285-.024-.15-.009-.31-.01-.46-.015H8.68c-.027 0-.05-.006-.075-.006-.158 0-.313.009-.469.016l-.325.015c-.39.024-.781.058-1.168.103-.121.014-.244.028-.363.046a8.77 8.77 0 00-.606.112c-.246.06-.487.137-.716.238-.186.082-.365.192-.504.353-.07.081-.124.18-.149.29-.04.178.004.362.104.515a.93.93 0 00.41.345c.145.065.3.107.459.137.225.04.454.063.681.073 1.267.063 2.555.07 3.82-.001a19.52 19.52 0 001.842-.17c.15-.019.283-.107.35-.245.067-.14.058-.303-.032-.424a.63.63 0 00-.382-.19 19.32 19.32 0 01-1.473-.132c-1.127-.135-2.28-.22-3.39-.17-.128.006-.258.012-.385.02-.137.01-.27.024-.405.039-.106.012-.221.02-.323.04-.233.044-.38.263-.327.494.053.234.273.376.507.336zM6.24 20.538l.012-.174c.039-.59.085-1.18.134-1.77.012-.148.024-.297.037-.445a.632.632 0 00-.058-.378l-.012-.023H20.19c-.055.863-.108 1.725-.166 2.588-.016.234-.066.496-.271.648-.236.175-.59.178-.838.09-.248-.088-.44-.271-.626-.449-.217-.207-.42-.413-.65-.577-.308-.22-.667-.338-1.04-.342-.364-.005-.709.124-1.017.31-.24.143-.474.307-.73.402-.324.119-.698.108-1.008-.042-.29-.14-.525-.376-.784-.547-.305-.202-.656-.328-1.023-.323-.325.004-.637.137-.92.308-.223.137-.437.293-.673.398-.3.133-.655.152-.97.055-.314-.096-.59-.296-.833-.518a2.85 2.85 0 00-.26-.223l-.006-.003z"/>
            </svg>
          </a>
        </div>
      </div>
    </footer>

    <!-- ===== LOGIN MODAL ===== -->
    <Teleport to="body">
      <div
        v-if="loginModalOpen"
        class="fixed inset-0 z-[999] flex items-center justify-center px-4"
        :class="isDark ? 'bg-black/70 backdrop-blur-md' : 'bg-black/50 backdrop-blur-md'"
        @click.self="closeLogin"
      >
        <div
          class="w-full max-w-md rounded-2xl border relative overflow-hidden"
          :class="isDark
            ? 'bg-[#0f1219] border-white/10'
            : 'bg-[#1c1035] border-white/10'"
        >
          <!-- Top accent line -->
          <div
            class="h-1 w-full"
            :class="isDark
              ? 'bg-gradient-to-r from-transparent via-game-accent to-transparent'
              : 'bg-gradient-to-r from-transparent via-game-sakura to-transparent'"
          ></div>

          <div class="p-8 md:p-10">
            <!-- Close button -->
            <button
              class="absolute top-5 right-5 w-8 h-8 flex items-center justify-center rounded-full transition-none"
              :class="isDark
                ? 'text-slate-500 hover:text-white hover:bg-white/10'
                : 'text-purple-400 hover:text-white hover:bg-white/10'"
              @click="closeLogin"
            >
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>

            <!-- Header -->
            <div class="text-center mb-8">
              <div
                class="inline-flex items-center justify-center w-14 h-14 rounded-xl mb-4"
                :class="isDark ? 'bg-game-accent/10' : 'bg-game-sakura/10'"
              >
                <svg
                  class="w-7 h-7"
                  :class="isDark ? 'text-game-accent' : 'text-game-sakura'"
                  viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"
                >
                  <path d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
                </svg>
              </div>
              <h2 class="font-sans text-xl font-semibold text-white mb-1">Welcome back</h2>
              <p class="font-sans text-sm" :class="isDark ? 'text-slate-400' : 'text-purple-300'">
                Sign in to continue your adventure
              </p>
            </div>

            <!-- Google Sign-in (rendered by GIS) -->
            <div ref="loginGoogleBtn" class="w-full flex justify-center"></div>

            <!-- Auth error -->
            <p v-if="authStore.error" class="font-sans text-sm text-red-400 text-center mt-3">
              {{ authStore.error }}
            </p>

            <!-- Info -->
            <p class="font-sans text-xs text-center mt-6"
               :class="isDark ? 'text-slate-500' : 'text-purple-400'"
            >
              Sign in with your Google account to get started
            </p>
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

.creation-fade {
  animation: fade-in 0.4s ease-in;
}

@keyframes fade-in {
  0% { opacity: 0; }
  100% { opacity: 1; }
}
</style>
