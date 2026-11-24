import { screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import FavoriteRecipePage from '../../src/pages/profile/FavoriteRecipePage.jsx';
import { apiError, json, mockApi, noContent } from '../support/api.js';
import { makeSavedRecipe } from '../support/fixtures.js';
import { renderWithRouter } from '../support/render.jsx';

const RECIPE = 'GET /recipes/saved/7';

function renderPage() {
  return renderWithRouter(<FavoriteRecipePage />, {
    route: '/profile/favorites/7',
    path: '/profile/favorites/:recipeId',
  });
}

describe('FavoriteRecipePage: recipe loading', () => {
  it('shows saved recipe', async () => {
    mockApi({ [RECIPE]: () => json(makeSavedRecipe(7)) });
    renderPage();

    expect(screen.getByRole('status')).toHaveTextContent(
      'Завантаження рецепта…',
    );
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Рецепт 7' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: 'До улюблених рецептів' }),
    ).toHaveAttribute('href', '/profile/favorites');
  });

  it('hides retry for 404', async () => {
    mockApi({
      [RECIPE]: () => apiError(404, 'Збережений рецепт не знайдений.'),
    });
    renderPage();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Збережений рецепт не знайдений.',
    );
    expect(
      screen.queryByRole('button', { name: 'Спробувати ще раз' }),
    ).not.toBeInTheDocument();
  });

  it('retries after server error', async () => {
    let attempt = 0;
    mockApi({
      [RECIPE]: () => {
        attempt += 1;
        return attempt === 1
          ? apiError(500, 'Внутрішня помилка сервера.')
          : json(makeSavedRecipe(7));
      },
    });
    const { user } = renderPage();

    await user.click(
      await screen.findByRole('button', { name: 'Спробувати ще раз' }),
    );

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Рецепт 7' }),
    ).toBeInTheDocument();
  });
});

describe('FavoriteRecipePage: recipe deletion', () => {
  it('deletes after confirmation', async () => {
    const api = mockApi({
      [RECIPE]: () => json(makeSavedRecipe(7)),
      'DELETE /recipes/saved/7': () => noContent(),
    });
    const { user } = renderPage();

    await user.click(
      await screen.findByRole('button', { name: 'Видалити рецепт' }),
    );
    await user.click(screen.getByRole('button', { name: 'Скасувати' }));
    expect(api.requestsTo('DELETE', '/recipes/saved/7')).toHaveLength(0);

    await user.click(screen.getByRole('button', { name: 'Видалити рецепт' }));
    await user.click(screen.getByRole('button', { name: 'Так, видалити' }));

    await waitFor(() =>
      expect(screen.getByTestId('location')).toHaveTextContent(
        /^\/profile\/favorites$/,
      ),
    );
    expect(api.requestsTo('DELETE', '/recipes/saved/7')).toHaveLength(1);
  });

  it('keeps recipe on error', async () => {
    mockApi({
      [RECIPE]: () => json(makeSavedRecipe(7)),
      'DELETE /recipes/saved/7': () =>
        apiError(500, 'Внутрішня помилка сервера.'),
    });
    const { user } = renderPage();

    await user.click(
      await screen.findByRole('button', { name: 'Видалити рецепт' }),
    );
    await user.click(screen.getByRole('button', { name: 'Так, видалити' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Внутрішня помилка сервера.',
    );
    expect(
      screen.getByRole('button', { name: 'Видалити рецепт' }),
    ).toBeEnabled();
    expect(screen.getByTestId('location')).toHaveTextContent(
      '/profile/favorites/7',
    );
  });
});
