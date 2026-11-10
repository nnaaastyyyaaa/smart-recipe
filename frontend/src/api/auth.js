import { apiFetch } from './client.js'

export function getMe({ signal } = {}) {
  return apiFetch('/auth/me', { signal })
}
