const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const STATUS_MESSAGES: Record<number, string> = {
  400: 'Invalid request. Please check your input and try again.',
  401: 'Your session has expired. Please sign in again.',
  403: 'You don\'t have permission to perform this action.',
  404: 'The requested resource was not found.',
  408: 'The request timed out. Please try again.',
  413: 'The file is too large. Please use a smaller file.',
  422: 'Invalid input. Please check your data and try again.',
  429: 'Too many requests. Please wait a moment and try again.',
  500: 'The server encountered an error. Please try again later.',
  502: 'The server is temporarily unavailable. Please try again later.',
  503: 'The service is currently unavailable. Please try again later.',
  504: 'The server took too long to respond. Please try again.',
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = localStorage.getItem('access_token')

  const isFormData = options.body instanceof FormData
  const headers: Record<string, string> = {
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
    ...((options.headers as Record<string, string>) ?? {}),
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  let res: Response
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...options,
      headers,
    })
  } catch {
    throw new Error('Unable to connect to the server. Please check your connection and try again.')
  }

  if (!res.ok) {
    if (res.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      window.location.href = '/'
    }

    const body = await res.json().catch(() => null)
    const detail = body?.detail
    const fallback = STATUS_MESSAGES[res.status] ?? `Something went wrong (error ${res.status}). Please try again.`
    throw new Error(detail ?? fallback)
  }

  if (res.status === 204) return undefined as T

  return res.json()
}
