import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { createFakeBackend } from '../support/fakeBackend.js';
import { renderApp } from '../support/render.jsx';

const SOURCES = import.meta.glob('../../src/**/*.{js,jsx}', {
  query: '?raw',
  import: 'default',
  eager: true,
});

function sourcesMatching(pattern) {
  return Object.entries(SOURCES)
    .filter(([, source]) => pattern.test(source))
    .map(([path]) => path);
}

describe('Non-functional: security', () => {
  it('KAN-31: sends session cookie only', async () => {
    const backend = createFakeBackend({ isLoggedIn: true, savedCount: 3 });
    renderApp('/profile/favorites');

    await screen.findByText('Збережено рецептів: 3');

    expect(backend.requests.length).toBeGreaterThan(1);
    for (const { init } of backend.requests) {
      expect(init.credentials).toBe('include');
      expect(init.headers?.Authorization).toBeUndefined();
    }
  });

  it('KAN-30: never stores data in browser', () => {
    expect(Object.keys(SOURCES).length).toBeGreaterThan(0);
    expect(
      sourcesMatching(/localStorage|sessionStorage|document\.cookie/),
    ).toEqual([]);
  });
});

describe('Non-functional: online operation', () => {
  it('KAN-42: recovers after network failure', async () => {
    const backend = createFakeBackend({ isLoggedIn: true, savedCount: 2 });
    const listSaved = backend.routes['GET /recipes/saved'];
    let isOnline = false;
    backend.routes['GET /recipes/saved'] = (request) =>
      isOnline ? listSaved(request) : new TypeError('Failed to fetch');
    const { user } = renderApp('/profile/favorites');

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Не вдалося зʼєднатися із сервером. Перевірте підключення до Інтернету.',
    );
    expect(
      screen.getByRole('heading', { name: 'Профіль' }),
    ).toBeInTheDocument();

    isOnline = true;
    await user.click(screen.getByRole('button', { name: 'Спробувати ще раз' }));

    expect(
      await screen.findByText('Збережено рецептів: 2'),
    ).toBeInTheDocument();
  });

  it('KAN-43: has no offline cache', () => {
    expect(sourcesMatching(/serviceWorker|caches\.|indexedDB/)).toEqual([]);
  });
});

describe('Non-functional: architecture', () => {
  it('KAN-32: never calls Gemini directly', () => {
    expect(sourcesMatching(/generativelanguage|googleapis|gemini/i)).toEqual(
      [],
    );
  });
});
