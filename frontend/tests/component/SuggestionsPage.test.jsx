import { screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import SuggestionsPage from '../../src/pages/generation/SuggestionsPage.jsx';
import { apiError, deferred, json, mockApi } from '../support/api.js';
import { makeSuggestionsPage } from '../support/fixtures.js';
import { renderWithRouter } from '../support/render.jsx';

const SUGGESTIONS = 'GET /generations/g-1/suggestions';
const SHOW_MORE = { name: 'Показати інші рецепти' };

function suggestionsRoute(options) {
  return ({ query }) => json(makeSuggestionsPage(Number(query.page), options));
}

function renderPage() {
  return renderWithRouter(<SuggestionsPage />, {
    route: '/generate/g-1/suggestions',
    path: '/generate/:generationId/suggestions',
  });
}

function cardTitles() {
  return screen
    .getAllByRole('heading', { level: 2 })
    .map((heading) => heading.textContent);
}

describe('SuggestionsPage: suggestion list', () => {
  it('shows suggestions after loading', async () => {
    const pending = deferred();
    const api = mockApi({ [SUGGESTIONS]: () => pending.promise });
    renderPage();

    expect(screen.getByRole('status')).toHaveTextContent(
      'Завантаження варіантів…',
    );

    pending.resolve(json(makeSuggestionsPage(1, { total: 3 })));

    expect(await screen.findByText('Страва 0')).toBeInTheDocument();
    expect(cardTitles()).toEqual(['Страва 0', 'Страва 1', 'Страва 2']);
    expect(screen.getByText(/Знайдено варіантів:/)).toHaveTextContent(
      'Знайдено варіантів: 3',
    );
    expect(
      screen.getByRole('link', { name: 'Детальніше: Страва 1' }),
    ).toHaveAttribute('href', '/generate/g-1/recipe/1');
    expect(
      screen.getByRole('link', { name: 'Назад до продуктів' }),
    ).toHaveAttribute('href', '/generate/g-1/products');
    expect(api.requests[0].query).toEqual({ page: '1' });
  });

  it('shows empty result message', async () => {
    mockApi({ [SUGGESTIONS]: suggestionsRoute({ total: 0 }) });
    renderPage();

    expect(
      await screen.findByText(
        'За обраними інгредієнтами та дієтичними обмеженнями рецептів не знайдено',
      ),
    ).toBeInTheDocument();
  });

  it('redirects when not ready', async () => {
    mockApi({
      [SUGGESTIONS]: () =>
        apiError(409, {
          code: 'SUGGESTIONS_NOT_READY',
          message: 'Варіанти рецептів ще не готові.',
        }),
    });
    renderPage();

    await waitFor(() =>
      expect(screen.getByTestId('location')).toHaveTextContent(
        '/generate/g-1/products',
      ),
    );
  });

  it('retries after server error', async () => {
    let attempt = 0;
    mockApi({
      [SUGGESTIONS]: (request) => {
        attempt += 1;
        return attempt === 1
          ? apiError(503, {
              code: 'AI_SERVICE_UNAVAILABLE',
              message: 'Сервіс генерації рецептів тимчасово недоступний.',
            })
          : suggestionsRoute({ total: 2 })(request);
      },
    });
    const { user } = renderPage();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Сервіс генерації рецептів тимчасово недоступний.',
    );

    await user.click(screen.getByRole('button', { name: 'Спробувати ще раз' }));

    expect(await screen.findByText('Страва 0')).toBeInTheDocument();
  });
});

describe('SuggestionsPage: show more', () => {
  it('appends next page', async () => {
    const api = mockApi({ [SUGGESTIONS]: suggestionsRoute({ total: 12 }) });
    const { user } = renderPage();
    await screen.findByText('Страва 0');
    expect(cardTitles()).toHaveLength(8);

    await user.click(screen.getByRole('button', SHOW_MORE));

    await waitFor(() => expect(cardTitles()).toHaveLength(12));
    expect(
      screen.getByRole('link', { name: 'Детальніше: Страва 8' }),
    ).toHaveFocus();
    expect(screen.queryByRole('button', SHOW_MORE)).not.toBeInTheDocument();
    expect(api.requests.map(({ query }) => query.page)).toEqual(['1', '2']);
  });

  it('retries failed load', async () => {
    let failNext = true;
    mockApi({
      [SUGGESTIONS]: (request) => {
        if (request.query.page === '2' && failNext) {
          failNext = false;
          return apiError(500, 'Внутрішня помилка сервера.');
        }
        return suggestionsRoute({ total: 12 })(request);
      },
    });
    const { user } = renderPage();
    await screen.findByText('Страва 0');

    await user.click(screen.getByRole('button', SHOW_MORE));
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Внутрішня помилка сервера.',
    );
    expect(cardTitles()).toHaveLength(8);

    await user.click(screen.getByRole('button', SHOW_MORE));
    await waitFor(() => expect(cardTitles()).toHaveLength(12));
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});
