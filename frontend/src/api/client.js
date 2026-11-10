import { API_URL } from '../config.js'

const DEFAULT_ERROR_MESSAGE = 'Сталася помилка. Спробуйте ще раз.'
const VALIDATION_ERROR_MESSAGE = 'Перевірте правильність введених даних.'
const NETWORK_ERROR_MESSAGE =
  'Не вдалося зʼєднатися із сервером. Перевірте підключення до Інтернету.'

export class ApiError extends Error {
  constructor({ status, code = null, message = DEFAULT_ERROR_MESSAGE }) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

function buildUrl(path, query) {
  const url = new URL(`${API_URL}${path}`, window.location.origin)

  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value === undefined || value === null || value === '') continue

      if (Array.isArray(value)) {
        value.forEach((item) => url.searchParams.append(key, item))
      } else {
        url.searchParams.append(key, value)
      }
    }
  }

  return url
}

async function parseError(response) {
  let detail = null

  try {
    const data = await response.json()
    detail = data?.detail ?? null
  } catch {
    detail = null
  }

  if (typeof detail === 'string') {
    return new ApiError({ status: response.status, message: detail })
  }

  if (Array.isArray(detail)) {
    return new ApiError({
      status: response.status,
      message: VALIDATION_ERROR_MESSAGE,
    })
  }

  if (detail && typeof detail === 'object') {
    return new ApiError({
      status: response.status,
      code: detail.code ?? null,
      message: detail.message ?? DEFAULT_ERROR_MESSAGE,
    })
  }

  return new ApiError({ status: response.status })
}

export async function apiFetch(
  path,
  { method = 'GET', body, query, signal } = {},
) {
  const hasBody = body !== undefined
  let response

  try {
    response = await fetch(buildUrl(path, query), {
      method,
      credentials: 'include',
      headers: hasBody ? { 'Content-Type': 'application/json' } : undefined,
      body: hasBody ? JSON.stringify(body) : undefined,
      signal,
    })
  } catch (error) {
    if (error.name === 'AbortError') throw error

    throw new ApiError({
      status: 0,
      code: 'NETWORK_ERROR',
      message: NETWORK_ERROR_MESSAGE,
    })
  }

  if (!response.ok) throw await parseError(response)

  if (response.status === 204) return null

  return response.json()
}
