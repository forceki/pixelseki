import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch } from '../lib/api'

export interface User {
  id: number
  email: string
  name: string | null
  avatar_url: string | null
  generation_credits: number
  credits_reset_at: string
}

interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

declare const google: {
  accounts: {
    id: {
      initialize(config: {
        client_id: string
        callback: (response: { credential: string }) => void
        auto_select?: boolean
      }): void
      prompt(): void
      renderButton(
        element: HTMLElement,
        config: { theme?: string; size?: string; text?: string; width?: number; locale?: string },
      ): void
      revoke(hint: string, callback?: () => void): void
    }
  }
}

export const useAuthStore = defineStore('auth', () => {
  const router = useRouter()
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => !!token.value)

  function _restoreSession() {
    const savedToken = localStorage.getItem('access_token')
    const savedUser = localStorage.getItem('user')
    if (savedToken && savedUser) {
      token.value = savedToken
      user.value = JSON.parse(savedUser)
    }
  }

  // Restore on store creation
  _restoreSession()

  function _saveSession(accessToken: string, userData: User) {
    token.value = accessToken
    user.value = userData
    localStorage.setItem('access_token', accessToken)
    localStorage.setItem('user', JSON.stringify(userData))
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('user')
    router.push('/')
  }

  async function loginWithGoogle(credential: string) {
    loading.value = true
    error.value = null
    try {
      const data = await apiFetch<TokenResponse>('/api/v1/auth/google/login', {
        method: 'POST',
        body: JSON.stringify({ id_token: credential }),
      })
      _saveSession(data.access_token, data.user)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Login failed'
      throw e
    } finally {
      loading.value = false
    }
  }

  function promptGoogleSignIn() {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID
    if (!clientId || clientId === 'your-google-client-id') {
      error.value = 'Google Client ID not configured'
      console.error('Set VITE_GOOGLE_CLIENT_ID in .env')
      return
    }

    google.accounts.id.initialize({
      client_id: clientId,
      callback: async (response) => {
        await loginWithGoogle(response.credential)
      },
    })

    google.accounts.id.prompt()
  }

  function renderGoogleButton(element: HTMLElement) {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID
    if (!clientId || clientId === 'your-google-client-id') {
      error.value = 'Google Client ID not configured'
      return
    }

    google.accounts.id.initialize({
      client_id: clientId,
      callback: async (response) => {
        await loginWithGoogle(response.credential)
      },
    })

    google.accounts.id.renderButton(element, {
      theme: 'filled_black',
      size: 'large',
      text: 'continue_with',
      width: 400,
      locale: 'en',
    })
  }

  async function fetchCurrentUser() {
    if (!token.value) return
    try {
      const data = await apiFetch<User>('/api/v1/users/me')
      user.value = data
      localStorage.setItem('user', JSON.stringify(data))
    } catch {
      logout()
    }
  }

  return {
    user,
    token,
    loading,
    error,
    isAuthenticated,
    loginWithGoogle,
    promptGoogleSignIn,
    renderGoogleButton,
    fetchCurrentUser,
    logout,
  }
})
