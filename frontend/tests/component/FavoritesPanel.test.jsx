import { screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import FavoriteRecipeCard from '../../src/components/favorites/FavoriteRecipeCard.jsx';
import FavoritesPanel from '../../src/components/favorites/FavoritesPanel.jsx';
import {
  apiError,
  deferred,
  json,
  mockApi,
  noContent,
} from '../support/api.js';
import { makeSavedRecipe, makeSavedRecipes } from '../support/fixtures.js';
import { renderWithRouter } from '../support/render.jsx';

function savedRecipesRoute(recipes) {
  return ({ query }) => {
    const offset = Number(query.offset);
    const limit = Number(query.limit);

    return json(recipes.slice(offset, offset + limit), {
      headers: { 'X-Total-Count': String(recipes.length) },
    });
  };
}

function renderPanel(route = '/profile/favorites') {
  return renderWithRouter(<FavoritesPanel />, {
    route,
    path: '/profile/favorites',
  });
}

function cardTitles() {
  return screen
    .getAllByRole('heading', { level: 3 })
    .map((heading) => heading.textContent);
}

describe('FavoriteRecipeCard: content and deletion', () => {
  it('shows recipe summary', () => {
    renderWithRouter(
      <FavoriteRecipeCard recipe={makeSavedRecipe(4)} onDelete={vi.fn()} />,
    );

    expect(
      screen.getByRole('heading', { name: 'Рецепт 4' }),
    ).toBeInTheDocument();
    expect(screen.getByText('Опис рецепта 4')).toBeInTheDocument();
    expect(screen.getByText('34 хв')).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: 'Детальніше: Рецепт 4' }),
    ).toHaveAttribute('href', '/profile/favorites/4');
  });

  it('asks before deleting', async () => {
    const onDelete = vi.fn().mockResolvedValue(true);
    const { user } = renderWithRouter(
      <FavoriteRecipeCard recipe={makeSavedRecipe(4)} onDelete={onDelete} />,
    );

    await user.click(screen.getByRole('button', { name: 'Видалити' }));
    await user.click(screen.getByRole('button', { name: 'Ні' }));
    expect(onDelete).not.toHaveBeenCalled();

    await user.click(screen.getByRole('button', { name: 'Видалити' }));
    await user.click(screen.getByRole('button', { name: 'Так' }));
    expect(onDelete).toHaveBeenCalledWith(makeSavedRecipe(4));
  });

  it('locks buttons while deleting', async () => {
    const pending = deferred();
    const { user } = renderWithRouter(
      <FavoriteRecipeCard
        recipe={makeSavedRecipe(4)}
        onDelete={() => pending.promise}
      />,
    );

    await user.click(screen.getByRole('button', { name: 'Видалити' }));
    await user.click(screen.getByRole('button', { name: 'Так' }));

    expect(screen.getByRole('button', { name: 'Так' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Ні' })).toBeDisabled();

    pending.resolve(false);
    expect(
      await screen.findByRole('button', { name: 'Видалити' }),
    ).toBeEnabled();
  });
});

describe('FavoritesPanel: list and paging', () => {
  it('shows first page', async () => {
    const api = mockApi({
      'GET /recipes/saved': savedRecipesRoute(makeSavedRecipes(13)),
    });
    renderPanel();

    expect(screen.getByText('Завантаження…')).toBeInTheDocument();
    expect(
      await screen.findByText('Збережено рецептів: 13'),
    ).toBeInTheDocument();
    expect(cardTitles()).toHaveLength(12);
    expect(api.requests[0].query).toEqual({ limit: '12', offset: '0' });
  });

  it('switches page', async () => {
    const api = mockApi({
      'GET /recipes/saved': savedRecipesRoute(makeSavedRecipes(13)),
    });
    const { user } = renderPanel();
    await screen.findByText('Збережено рецептів: 13');

    await user.click(screen.getByRole('button', { name: '2' }));

    await waitFor(() => expect(cardTitles()).toEqual(['Рецепт 13']));
    expect(screen.getByTestId('location')).toHaveTextContent(
      '/profile/favorites?page=2',
    );
    expect(api.requests.at(-1).query).toEqual({ limit: '12', offset: '12' });
    expect(window.scrollTo).toHaveBeenCalledWith({ top: 0 });
  });

  it('corrects page out of range', async () => {
    mockApi({ 'GET /recipes/saved': savedRecipesRoute(makeSavedRecipes(13)) });
    renderPanel('/profile/favorites?page=9');

    await waitFor(() => expect(cardTitles()).toEqual(['Рецепт 13']));
    expect(screen.getByTestId('location')).toHaveTextContent(
      '/profile/favorites?page=2',
    );
  });

  it('shows empty state', async () => {
    mockApi({ 'GET /recipes/saved': savedRecipesRoute([]) });
    renderPanel();

    expect(
      await screen.findByText('Ви ще не зберегли жодного рецепта'),
    ).toBeInTheDocument();
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
  });

  it('retries failed load', async () => {
    let attempt = 0;
    mockApi({
      'GET /recipes/saved': (request) => {
        attempt += 1;
        return attempt === 1
          ? apiError(500, 'Внутрішня помилка сервера.')
          : savedRecipesRoute(makeSavedRecipes(2))(request);
      },
    });
    const { user } = renderPanel();

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Внутрішня помилка сервера.');

    await user.click(
      within(alert).getByRole('button', { name: 'Спробувати ще раз' }),
    );

    expect(
      await screen.findByText('Збережено рецептів: 2'),
    ).toBeInTheDocument();
  });
});

describe('FavoritesPanel: recipe deletion', () => {
  it('reloads list after delete', async () => {
    const recipes = makeSavedRecipes(3);
    const api = mockApi({
      'GET /recipes/saved': (request) => savedRecipesRoute(recipes)(request),
      'DELETE /recipes/saved/:id': ({ params }) => {
        recipes.splice(
          recipes.findIndex(({ id }) => id === Number(params.id)),
          1,
        );
        return noContent();
      },
    });
    const { user } = renderPanel();
    await screen.findByText('Збережено рецептів: 3');

    const card = screen
      .getByRole('heading', { name: 'Рецепт 2' })
      .closest('article');
    await user.click(within(card).getByRole('button', { name: 'Видалити' }));
    await user.click(within(card).getByRole('button', { name: 'Так' }));

    expect(
      await screen.findByText('Збережено рецептів: 2'),
    ).toBeInTheDocument();
    expect(cardTitles()).toEqual(['Рецепт 1', 'Рецепт 3']);
    expect(api.requestsTo('DELETE', '/recipes/saved/2')).toHaveLength(1);
  });

  it('keeps recipe on error', async () => {
    mockApi({
      'GET /recipes/saved': savedRecipesRoute(makeSavedRecipes(1)),
      'DELETE /recipes/saved/1': () =>
        apiError(404, 'Збережений рецепт не знайдений.'),
    });
    const { user } = renderPanel();
    await screen.findByText('Збережено рецептів: 1');

    await user.click(screen.getByRole('button', { name: 'Видалити' }));
    await user.click(screen.getByRole('button', { name: 'Так' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Збережений рецепт не знайдений.',
    );
    expect(
      screen.getByRole('heading', { name: 'Рецепт 1' }),
    ).toBeInTheDocument();
  });
});
