import { describe, expect, it, vi } from 'vitest';
import { ApiError, apiFetch } from '../../src/api/client.js';
import { apiError, json, mockApi, noContent } from '../support/api.js';

describe('apiFetch: request building', () => {
  it('adds API prefix and session cookie', async () => {
    const api = mockApi({ 'GET /auth/me': () => json({ id: 1 }) });

    await expect(apiFetch('/auth/me')).resolves.toEqual({ id: 1 });

    const [url, init] = api.fetchMock.mock.calls[0];
    expect(String(url)).toBe('http://localhost:8000/api/auth/me');
    expect(init).toMatchObject({ method: 'GET', credentials: 'include' });
    expect(init.headers).toBeUndefined();
  });

  it('skips empty query values', async () => {
    const api = mockApi({ 'GET /products': () => json([]) });

    await apiFetch('/products', {
      query: { search: '', limit: 12, offset: 0, category: null, ids: [1, 2] },
    });

    const [url] = api.fetchMock.mock.calls[0];
    expect(url.search).toBe('?limit=12&offset=0&ids=1&ids=2');
  });

  it('sends body as JSON', async () => {
    const api = mockApi({ 'POST /auth/login': () => json({ id: 1 }) });

    await apiFetch('/auth/login', {
      method: 'POST',
      body: { email: 'a@b.c', password: 'x' },
    });

    const { init, body } = api.requests[0];
    expect(init.headers).toEqual({ 'Content-Type': 'application/json' });
    expect(body).toEqual({ email: 'a@b.c', password: 'x' });
  });

  it('returns null for 204', async () => {
    mockApi({ 'POST /auth/logout': () => noContent() });

    await expect(
      apiFetch('/auth/logout', { method: 'POST' }),
    ).resolves.toBeNull();
  });
});

describe('apiFetch: error handling', () => {
  it.each([
    {
      kind: 'text detail',
      response: () => apiError(401, 'Невірний email або пароль.'),
      expected: {
        status: 401,
        code: null,
        message: 'Невірний email або пароль.',
      },
    },
    {
      kind: 'validation detail',
      response: () => apiError(422, [{ loc: ['body', 'email'] }]),
      expected: {
        status: 422,
        code: null,
        message: 'Перевірте правильність введених даних.',
      },
    },
    {
      kind: 'coded detail',
      response: () =>
        apiError(429, {
          code: 'AI_REQUEST_LIMIT_REACHED',
          message: 'Досягнуто ліміту запитів.',
        }),
      expected: {
        status: 429,
        code: 'AI_REQUEST_LIMIT_REACHED',
        message: 'Досягнуто ліміту запитів.',
      },
    },
    {
      kind: 'non-JSON body',
      response: () => new Response('<html>Bad Gateway</html>', { status: 502 }),
      expected: {
        status: 502,
        code: null,
        message: 'Сталася помилка. Спробуйте ще раз.',
      },
    },
  ])('maps $kind to ApiError', async ({ response, expected }) => {
    mockApi({ 'GET /auth/me': response });

    const error = await apiFetch('/auth/me').catch((caught) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject(expected);
  });

  it('reports network failure', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new TypeError('Failed to fetch')),
    );

    await expect(apiFetch('/auth/me')).rejects.toMatchObject({
      status: 0,
      code: 'NETWORK_ERROR',
      message:
        'Не вдалося зʼєднатися із сервером. Перевірте підключення до Інтернету.',
    });
  });

  it('rethrows aborted request', async () => {
    mockApi({ 'GET /auth/me': () => json({ id: 1 }) });
    const controller = new AbortController();
    controller.abort();

    await expect(
      apiFetch('/auth/me', { signal: controller.signal }),
    ).rejects.toMatchObject({ name: 'AbortError' });
  });
});
