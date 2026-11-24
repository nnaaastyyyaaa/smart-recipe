import { StrictMode } from 'react';
import { screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import GeneratedRecipePage from '../../src/pages/generation/GeneratedRecipePage.jsx';
import {
  apiError,
  deferred,
  json,
  mockApi,
  noContent,
} from '../support/api.js';
import { makeGeneratedRecipe } from '../support/fixtures.js';
import { renderWithRouter } from '../support/render.jsx';

const RECIPE = 'POST /generations/g-1/recipe';
const LIMIT_MESSAGE =
  'Досягнуто ліміту запитів. Спробуйте ще раз трохи пізніше.';

function renderPage() {
  return renderWithRouter(
    <StrictMode>
      <GeneratedRecipePage />
    </StrictMode>,
    {
      route: '/generate/g-1/recipe/3',
      path: '/generate/:generationId/recipe/:suggestionId',
    },
  );
}

describe('GeneratedRecipePage: recipe loading', () => {
  it('shows recipe after waiting', async () => {
    const pending = deferred();
    const api = mockApi({ [RECIPE]: () => pending.promise });
    renderPage();

    expect(screen.getByRole('status')).toHaveTextContent('Готуємо ваш рецепт…');
    expect(
      screen.getByRole('link', { name: 'Назад до варіантів' }),
    ).toHaveAttribute('href', '/generate/g-1/suggestions');

    pending.resolve(json(makeGeneratedRecipe(3)));

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Страва 3' }),
    ).toBeInTheDocument();
    expect(api.requests[0].body).toEqual({ suggestion_id: 3 });
  });

  it('sends a single request', async () => {
    const api = mockApi({ [RECIPE]: () => json(makeGeneratedRecipe(3)) });
    renderPage();

    await screen.findByRole('heading', { level: 1 });

    expect(api.requestsTo('POST', '/generations/g-1/recipe')).toHaveLength(1);
  });

  it('retries after rate limit', async () => {
    let attempt = 0;
    mockApi({
      [RECIPE]: () => {
        attempt += 1;
        return attempt === 1
          ? apiError(429, {
              code: 'AI_REQUEST_LIMIT_REACHED',
              message: LIMIT_MESSAGE,
            })
          : json(makeGeneratedRecipe(3));
      },
    });
    const { user } = renderPage();

    expect(await screen.findByRole('alert')).toHaveTextContent(LIMIT_MESSAGE);

    await user.click(screen.getByRole('button', { name: 'Спробувати ще раз' }));

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Страва 3' }),
    ).toBeInTheDocument();
  });

  it('hides retry for missing suggestion', async () => {
    mockApi({
      [RECIPE]: () =>
        apiError(404, {
          code: 'SUGGESTION_NOT_FOUND',
          message: 'Обраний варіант рецепта не знайдено.',
        }),
    });
    renderPage();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Обраний варіант рецепта не знайдено.',
    );
    expect(
      screen.queryByRole('button', { name: 'Спробувати ще раз' }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'На головну' })).toHaveAttribute(
      'href',
      '/',
    );
  });
});

describe('GeneratedRecipePage: favorites toggle', () => {
  it('saves and unsaves recipe', async () => {
    const saving = deferred();
    const api = mockApi({
      [RECIPE]: () => json(makeGeneratedRecipe(3)),
      'POST /recipes/saved': () => saving.promise,
      'DELETE /recipes/saved/42': () => noContent(),
    });
    const { user } = renderPage();

    await user.click(await screen.findByRole('button', { name: 'Зберегти' }));
    expect(screen.getByRole('button', { name: 'Зберегти' })).toBeDisabled();

    saving.resolve(
      json({ id: 42, ...makeGeneratedRecipe(3) }, { status: 201 }),
    );

    const saved = await screen.findByRole('button', { name: 'Збережено' });
    expect(saved).toHaveAttribute('title', 'Прибрати з улюблених');
    expect(api.requestsTo('POST', '/recipes/saved')[0].body).toEqual(
      makeGeneratedRecipe(3),
    );

    await user.click(saved);

    expect(
      await screen.findByRole('button', { name: 'Зберегти' }),
    ).toBeEnabled();
    expect(api.requestsTo('DELETE', '/recipes/saved/42')).toHaveLength(1);
  });

  it('shows save error', async () => {
    mockApi({
      [RECIPE]: () => json(makeGeneratedRecipe(3)),
      'POST /recipes/saved': () => apiError(500, 'Внутрішня помилка сервера.'),
    });
    const { user } = renderPage();

    await user.click(await screen.findByRole('button', { name: 'Зберегти' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Внутрішня помилка сервера.',
    );
    expect(screen.getByRole('button', { name: 'Зберегти' })).toBeEnabled();
  });

  it('accepts already removed recipe', async () => {
    mockApi({
      [RECIPE]: () => json(makeGeneratedRecipe(3)),
      'POST /recipes/saved': () => json({ id: 42 }, { status: 201 }),
      'DELETE /recipes/saved/42': () =>
        apiError(404, 'Збережений рецепт не знайдений.'),
    });
    const { user } = renderPage();

    await user.click(await screen.findByRole('button', { name: 'Зберегти' }));
    await user.click(await screen.findByRole('button', { name: 'Збережено' }));

    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Зберегти' })).toBeEnabled(),
    );
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});
