<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const route = useRoute()

const alwaysSolid = computed(() => route.path !== '/')

const creditsResetLabel = computed(() => {
  const resetAt = authStore.user?.credits_reset_at
  if (!resetAt) return ''
  const date = new Date(resetAt)
  const now = new Date()
  const diffMs = date.getTime() - now.getTime()
  if (diffMs <= 0) return 'Credits resetting soon...'
  const days = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  const hours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))
  const resetDate = date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
  if (days > 0) return `Resets ${resetDate} (${days}d ${hours}h)`
  return `Resets ${resetDate} (${hours}h)`
})

const isDark = defineModel<boolean>('isDark', { required: true })

const emit = defineEmits<{
  login: []
}>()

const mobileMenuOpen = ref(false)
const navVisible = ref(true)
const navSolid = ref(false)

let lastScrollY = 0

function onScroll() {
  const currentY = window.scrollY
  navVisible.value = currentY <= 50 || currentY < lastScrollY
  navSolid.value = currentY > 80
  lastScrollY = currentY
}

onMounted(() => {
  window.addEventListener('scroll', onScroll, { passive: true })
})

onUnmounted(() => {
  window.removeEventListener('scroll', onScroll)
})

const navLinks = [
  { label: 'HOME', to: '/' },
  { label: 'CREATION', to: '/creation' },
  { label: 'OBJECTS', to: '/objects' },
  { label: 'GALLERY', to: '/gallery' },
]

function toggleTheme() {
  isDark.value = !isDark.value
}

function handleLogin() {
  mobileMenuOpen.value = false
  emit('login')
}
</script>

<template>
  <nav
    class="fixed top-0 left-0 right-0 z-50 w-full border-b-2 backdrop-blur-sm"
    :class="[
      isDark ? 'border-game-border/50' : 'border-[#4c1d95]/50',
      navSolid || alwaysSolid
        ? isDark
          ? 'bg-game-dark/95'
          : 'bg-[#1a0a2e]/95'
        : 'bg-transparent border-transparent',
    ]"
    style="
      transition:
        background-color 0.15s step-end,
        border-color 0.15s step-end;
    "
  >
    <div class="mx-auto flex max-w-6xl items-center justify-between px-4 py-2 md:px-8">
      <!-- Brand -->
      <RouterLink
        to="/"
        class="font-pixel text-[10px] md:text-xs tracking-widest uppercase select-none no-underline"
        :class="
          isDark ? 'text-game-accent text-glow-accent' : 'text-game-sakura text-glow-sakura'
        "
      >
        PIXELSEKI
      </RouterLink>

      <!-- Desktop Nav Links (only when authenticated) -->
      <ul v-if="authStore.isAuthenticated" class="hidden md:flex items-center gap-6">
        <li v-for="link in navLinks" :key="link.label">
          <RouterLink
            :to="link.to"
            class="font-terminal text-lg uppercase tracking-wider hover:translate-y-[2px] transition-none relative group select-none no-underline"
            :class="
              isDark
                ? 'text-slate-400 hover:text-game-accent'
                : 'text-purple-300 hover:text-game-sakura'
            "
          >
            <span
              class="opacity-0 group-hover:opacity-100 mr-0.5 transition-none"
              :class="isDark ? 'text-game-accent' : 'text-game-sakura'"
              >&#9654;</span
            >
            {{ link.label }}
          </RouterLink>
        </li>
      </ul>

      <div class="hidden md:flex items-center gap-3">
        <button
          class="font-terminal text-xl border-2 px-2 py-0.5 uppercase transition-none select-none rounded-none"
          :class="
            isDark
              ? 'text-game-gold border-game-gold/50 hover:bg-game-gold/10'
              : 'text-game-accent border-game-accent/50 hover:bg-game-accent/10'
          "
          @click="toggleTheme"
        >
          {{ isDark ? '&#9788;' : '&#9790;' }}
        </button>

        <!-- Authenticated: credits + user info + logout -->
        <template v-if="authStore.isAuthenticated">
          <!-- Credits badge -->
          <div id="credits-badge" class="relative group">
            <div
              class="flex items-center gap-1 border-2 px-2 py-0.5 font-terminal text-sm tracking-wider select-none cursor-help"
              :class="
                isDark
                  ? 'border-game-gold/50 text-game-gold'
                  : 'border-yellow-400/50 text-yellow-300'
              "
            >
              <span>&#9733;</span>
              <span>{{ authStore.user?.generation_credits ?? 0 }}</span>
            </div>
            <!-- Tooltip -->
            <div
              class="absolute top-full left-1/2 -translate-x-1/2 mt-2 px-3 py-2 whitespace-nowrap font-terminal text-xs tracking-wider opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity border-2 z-50"
              :class="
                isDark
                  ? 'bg-game-panel text-slate-300 border-game-border'
                  : 'bg-[#2d1b4e] text-purple-200 border-[#4c1d95]'
              "
            >
              {{ creditsResetLabel }}
            </div>
          </div>

          <div class="flex items-center gap-2">
            <img
              v-if="authStore.user?.avatar_url"
              :src="authStore.user.avatar_url"
              :alt="authStore.user.name ?? 'User'"
              class="w-8 h-8 rounded-full border-2"
              :class="isDark ? 'border-game-accent' : 'border-game-sakura'"
              referrerpolicy="no-referrer"
            />
            <span
              class="font-terminal text-sm uppercase tracking-wider max-w-[120px] truncate"
              :class="isDark ? 'text-slate-300' : 'text-purple-200'"
            >
              {{ authStore.user?.name ?? authStore.user?.email }}
            </span>
          </div>
          <button
            class="font-pixel text-[9px] border-3 border-black px-4 py-2 uppercase tracking-wider shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] hover:shadow-[1px_1px_0px_0px_rgba(0,0,0,1)] hover:translate-x-[2px] hover:translate-y-[2px] active:shadow-none active:translate-x-[3px] active:translate-y-[3px] transition-none select-none rounded-none bg-red-500 text-white"
            @click="authStore.logout()"
          >
            LOGOUT
          </button>
        </template>

        <!-- Not authenticated: START button only -->
        <button
          v-else
          class="font-pixel text-[9px] border-3 border-black px-4 py-2 uppercase tracking-wider shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] hover:shadow-[1px_1px_0px_0px_rgba(0,0,0,1)] hover:translate-x-[2px] hover:translate-y-[2px] active:shadow-none active:translate-x-[3px] active:translate-y-[3px] transition-none select-none rounded-none"
          :class="isDark ? 'text-game-dark bg-game-accent' : 'text-game-dark bg-game-sakura'"
          @click="handleLogin"
        >
          START
        </button>
      </div>

      <!-- Mobile: only show menu toggle when authenticated -->
      <div class="flex md:hidden items-center gap-2">
        <button
          class="font-terminal text-2xl p-1 transition-none"
          :class="isDark ? 'text-game-gold' : 'text-game-accent'"
          @click="toggleTheme"
        >
          {{ isDark ? '&#9788;' : '&#9790;' }}
        </button>
        <button
          v-if="authStore.isAuthenticated"
          class="font-terminal text-2xl p-1 transition-none"
          :class="isDark ? 'text-game-accent' : 'text-game-sakura'"
          aria-label="Toggle menu"
          @click="mobileMenuOpen = !mobileMenuOpen"
        >
          <span v-if="!mobileMenuOpen">&#9776;</span>
          <span v-else>&#10005;</span>
        </button>
        <!-- Mobile START button when not authenticated -->
        <button
          v-if="!authStore.isAuthenticated"
          class="font-pixel text-[9px] border-3 border-black px-4 py-1.5 uppercase tracking-wider shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] hover:shadow-[1px_1px_0px_0px_rgba(0,0,0,1)] hover:translate-x-[2px] hover:translate-y-[2px] active:shadow-none active:translate-x-[3px] active:translate-y-[3px] transition-none select-none rounded-none"
          :class="isDark ? 'text-game-dark bg-game-accent' : 'text-game-dark bg-game-sakura'"
          @click="handleLogin"
        >
          START
        </button>
      </div>
    </div>

    <!-- Mobile Menu Dropdown -->
    <div
      v-if="mobileMenuOpen"
      class="md:hidden border-t-2 px-4 pb-4"
      :class="isDark ? 'border-game-border/50 bg-game-panel' : 'border-[#4c1d95]/50 bg-[#2d1b4e]'"
    >
      <ul class="flex flex-col gap-1 pt-2">
        <li v-for="link in navLinks" :key="link.label">
          <RouterLink
            :to="link.to"
            class="font-terminal text-lg uppercase tracking-wider block py-2.5 px-2 border-b transition-none no-underline"
            :class="
              isDark
                ? 'text-slate-400 border-game-border/30 hover:text-game-accent hover:bg-game-dark'
                : 'text-purple-300 border-[#4c1d95]/30 hover:text-game-sakura hover:bg-[#1a0a2e]'
            "
            @click="mobileMenuOpen = false"
          >
            &#9654; {{ link.label }}
          </RouterLink>
        </li>
      </ul>
      <template v-if="authStore.isAuthenticated">
        <div class="flex items-center justify-between mt-4 px-2">
          <div class="flex items-center gap-2">
            <img
              v-if="authStore.user?.avatar_url"
              :src="authStore.user.avatar_url"
              :alt="authStore.user.name ?? 'User'"
              class="w-8 h-8 rounded-full border-2"
              :class="isDark ? 'border-game-accent' : 'border-game-sakura'"
              referrerpolicy="no-referrer"
            />
            <span
              class="font-terminal text-sm uppercase tracking-wider truncate"
              :class="isDark ? 'text-slate-300' : 'text-purple-200'"
            >
              {{ authStore.user?.name ?? authStore.user?.email }}
            </span>
          </div>
          <!-- Credits badge (mobile) -->
          <div
            class="flex items-center gap-1 border-2 px-2 py-0.5 font-terminal text-sm tracking-wider select-none"
            :class="
              isDark
                ? 'border-game-gold/50 text-game-gold'
                : 'border-yellow-400/50 text-yellow-300'
            "
          >
            <span>&#9733;</span>
            <span>{{ authStore.user?.generation_credits ?? 0 }}</span>
          </div>
        </div>
        <!-- Credits reset info (mobile) -->
        <div
          class="mt-1 px-2 font-terminal text-xs tracking-wider"
          :class="isDark ? 'text-slate-500' : 'text-purple-400'"
        >
          {{ creditsResetLabel }}
        </div>
        <button
          class="w-full mt-2 font-pixel text-[9px] text-white border-3 border-black px-4 py-2.5 uppercase tracking-wider shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] active:shadow-none active:translate-x-[3px] active:translate-y-[3px] transition-none rounded-none bg-red-500"
          @click="authStore.logout(); mobileMenuOpen = false"
        >
          LOGOUT
        </button>
      </template>
      <button
        v-else
        class="w-full mt-4 font-pixel text-[9px] text-game-dark border-3 border-black px-4 py-2.5 uppercase tracking-wider shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] active:shadow-none active:translate-x-[3px] active:translate-y-[3px] transition-none rounded-none"
        :class="isDark ? 'bg-game-accent' : 'bg-game-sakura'"
        @click="handleLogin"
      >
        START
      </button>
    </div>
  </nav>
</template>
