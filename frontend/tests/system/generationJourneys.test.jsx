import { screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { json } from '../support/api.js';
import { createFakeBackend } from '../support/fakeBackend.js';
import {
  CATEGORIES,
  PASSWORD,
  RESTRICTIONS,
  USER,
  makeGeneration,
  makeProduct,
  makeProducts,
} from '../support/fixtures.js';
import { renderApp } from '../support/render.jsx';

function expectPath(path) {
  return waitFor(() => expect(window.location.pathname).toBe(path));
}

function addGenerationRoutes(backend) {
  const session = { restrictionIds: null, productIds: [] };

  const generation = () =>
    makeGeneration({
      status:
        session.restrictionIds === null
          ? 'awaiting_restrictions'
          : 'awaiting_products',
      restrictions: RESTRICTIONS.filter(({ id }) =>
        session.restrictionIds?.includes(id),
      ),
      product_ids: session.productIds,
    });

  Object.assign(backend.routes, {
    'POST /generations': () => json(generation(), { status: 201 }),
    'GET /generations/g-1': () => json(generation()),
    'GET /dietary-restrictions': () => json(RESTRICTIONS),
    'PUT /generations/g-1/restrictions': ({ body }) => {
      session.restrictionIds = body.restriction_ids;
      session.productIds = [];
      return json(generation());
    },
    'GET /generations/g-1/categories': () => json(CATEGORIES),
    'GET /generations/g-1/products': () => json(makeProducts(3)),
    'GET /products/:id': ({ params }) => json(makeProduct(Number(params.id))),
    'POST /generations/g-1/suggestions': ({ body }) => {
      session.productIds = body.product_ids;
      return json({ items: [], page: 1, page_size: 8, total: 12 });
    },
  });

  return session;
}

describe('Generation journeys: access', () => {
  it('returns to closed page after login', async () => {
    createFakeBackend({ savedCount: 1 });
    const { user } = renderApp('/profile/favorites');

    await expectPath('/login');
    await user.type(
      await screen.findByLabelText('Електронна пошта'),
      USER.email,
    );
    await user.type(screen.getByLabelText('Пароль'), PASSWORD);
    await user.click(screen.getByRole('button', { name: 'Увійти' }));

    await expectPath('/profile/favorites');
    expect(
      await screen.findByRole('heading', { name: 'Рецепт 1' }),
    ).toBeInTheDocument();
  });
});

describe('Generation journeys: recipe search', () => {
  it('goes from home to suggestions', async () => {
    const backend = createFakeBackend({ isLoggedIn: true });
    const session = addGenerationRoutes(backend);
    const { user } = renderApp('/');

    await user.click(
      await screen.findByRole('button', { name: 'Почати генерацію' }),
    );
    await expectPath('/generate/g-1/restrictions');

    await user.click(
      await screen.findByRole('checkbox', { name: 'Без глютену' }),
    );
    await user.click(
      screen.getByRole('button', { name: 'Далі: вибір продуктів' }),
    );
    await expectPath('/generate/g-1/products');
    expect(await screen.findByText('Без глютену')).toBeInTheDocument();

    await user.click(await screen.findByRole('button', { name: /^Продукт 1/ }));
    await user.click(screen.getByRole('button', { name: /^Продукт 3/ }));
    await user.click(screen.getByRole('button', { name: 'Підібрати рецепти' }));

    await expectPath('/generate/g-1/suggestions');
    expect(await screen.findByText('Страва 0')).toBeInTheDocument();
    expect(session.productIds).toEqual([1, 3]);
    expect(backend.requestsTo('POST', '/generations/g-1/recipe')).toHaveLength(
      0,
    );

    await user.click(screen.getByRole('link', { name: 'Назад до продуктів' }));

    expect(
      await screen.findByRole('button', { name: 'Прибрати «Продукт 3»' }),
    ).toBeInTheDocument();
  });
});