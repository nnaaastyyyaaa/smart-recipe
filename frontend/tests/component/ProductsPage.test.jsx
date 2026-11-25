import { screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import ProductsPage, {
  MAX_PRODUCTS,
  PAGE_SIZE,
} from '../../src/pages/generation/ProductsPage.jsx';
import { apiError, json, mockApi } from '../support/api.js';
import {
  CATEGORIES,
  makeGeneration,
  makeProduct,
  makeProducts,
} from '../support/fixtures.js';
import { renderWithRouter } from '../support/render.jsx';

const PRODUCTS = 'GET /generations/g-1/products';
const SUGGEST = 'POST /generations/g-1/suggestions';
const SUBMIT = { name: 'Підібрати рецепти' };

function productsRoute(all) {
  return ({ query }) => {
    const offset = Number(query.offset);
    return json(all.slice(offset, offset + Number(query.limit)));
  };
}

function mockProductsApi({
  generation = makeGeneration(),
  products = makeProducts(5),
  routes = {},
} = {}) {
  return mockApi({
    'GET /generations/g-1': () => json(generation),
    'GET /generations/g-1/categories': () => json(CATEGORIES),
    'GET /products/:id': ({ params }) => json(makeProduct(Number(params.id))),
    [PRODUCTS]: productsRoute(products),
    [SUGGEST]: () => json({ items: [], page: 1, page_size: 8, total: 3 }),
    ...routes,
  });
}

function renderPage() {
  return renderWithRouter(<ProductsPage />, {
    route: '/generate/g-1/products',
    path: '/generate/:generationId/products',
  });
}

function product(name) {
  return screen.findByRole('button', { name: new RegExp(`^${name}(?!\\d)`) });
}

function counter() {
  return screen.getByRole('heading', { name: /Ваш вибір/ });
}

describe('ProductsPage: catalog', () => {
  it('shows restrictions and categories', async () => {
    mockProductsApi();
    renderPage();

    expect(await product('Продукт 1')).toBeInTheDocument();
    expect(screen.getByText('Веганська')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Змінити' })).toHaveAttribute(
      'href',
      '/generate/g-1/restrictions',
    );
    expect(
      within(screen.getByRole('combobox', { name: 'Категорія' }))
        .getAllByRole('option')
        .map((option) => option.textContent),
    ).toEqual(['Усі категорії', 'Овочі', 'Крупи']);
  });

  it(`shows ${PAGE_SIZE} products per page`, async () => {
    const api = mockProductsApi({ products: makeProducts(30) });
    const { user } = renderPage();

    expect(await product('Продукт 12')).toBeInTheDocument();
    expect(screen.queryByText('Продукт 13')).not.toBeInTheDocument();
    expect(api.requestsTo('GET', '/generations/g-1/products')[0].query).toEqual(
      { limit: String(PAGE_SIZE + 1), offset: '0' },
    );
    expect(
      screen.getByRole('button', { name: 'Попередня сторінка' }),
    ).toBeDisabled();

    await user.click(screen.getByRole('button', { name: 'Наступна сторінка' }));

    expect(await product('Продукт 13')).toBeInTheDocument();
    expect(screen.getByText('Сторінка 2')).toBeInTheDocument();
  });

  it('filters by category', async () => {
    const api = mockProductsApi();
    const { user } = renderPage();
    await product('Продукт 1');

    await user.selectOptions(
      screen.getByRole('combobox', { name: 'Категорія' }),
      'Крупи',
    );

    await waitFor(() =>
      expect(
        api.requestsTo('GET', '/generations/g-1/products').at(-1).query,
      ).toMatchObject({ category_id: '2', offset: '0' }),
    );
  });

  it('debounces search', async () => {
    const api = mockProductsApi();
    const { user } = renderPage();
    await product('Продукт 1');

    await user.type(screen.getByRole('searchbox'), ' рис ');

    await waitFor(() =>
      expect(
        api.requestsTo('GET', '/generations/g-1/products').at(-1).query.search,
      ).toBe('рис'),
    );
    expect(
      api
        .requestsTo('GET', '/generations/g-1/products')
        .filter(({ query }) => query.search),
    ).toHaveLength(1);
  });

  it('shows empty result', async () => {
    mockProductsApi({ products: [] });
    renderPage();

    expect(await screen.findByText(/Нічого не знайдено/)).toBeInTheDocument();
  });

  it('returns to restrictions step', async () => {
    mockProductsApi({
      generation: makeGeneration({ status: 'awaiting_restrictions' }),
    });
    renderPage();

    await waitFor(() =>
      expect(screen.getByTestId('location')).toHaveTextContent(
        '/generate/g-1/restrictions',
      ),
    );
  });
});

describe('ProductsPage: selection', () => {
  it('adds and removes products', async () => {
    mockProductsApi();
    const { user } = renderPage();

    const first = await product('Продукт 1');
    await user.click(first);

    expect(first).toHaveAttribute('aria-pressed', 'true');
    expect(counter()).toHaveTextContent(`1/${MAX_PRODUCTS}`);

    await user.click(
      screen.getByRole('button', { name: 'Прибрати «Продукт 1»' }),
    );

    expect(first).toHaveAttribute('aria-pressed', 'false');
    expect(counter()).toHaveTextContent(`0/${MAX_PRODUCTS}`);
  });

  it('explains minimum of two', async () => {
    mockProductsApi();
    const { user } = renderPage();

    await user.click(await product('Продукт 1'));

    expect(screen.getByRole('button', SUBMIT)).toBeDisabled();
    expect(screen.getByRole('button', SUBMIT)).toHaveAccessibleDescription(
      'Оберіть щонайменше 2 продукти, щоб підібрати рецепти.',
    );

    await user.click(await product('Продукт 2'));

    expect(screen.getByRole('button', SUBMIT)).toBeEnabled();
    expect(
      screen.queryByText(/Оберіть щонайменше 2 продукти/),
    ).not.toBeInTheDocument();
  });

  it('keeps choice between pages', async () => {
    mockProductsApi({ products: makeProducts(20) });
    const { user } = renderPage();

    await user.click(await product('Продукт 1'));
    await user.click(screen.getByRole('button', { name: 'Наступна сторінка' }));
    await user.click(await product('Продукт 13'));

    expect(counter()).toHaveTextContent(`2/${MAX_PRODUCTS}`);
    expect(
      screen.getByRole('button', { name: 'Прибрати «Продукт 1»' }),
    ).toBeInTheDocument();
  });

  it(`limits choice to ${MAX_PRODUCTS}`, async () => {
    mockProductsApi({ products: makeProducts(40) });
    const { user } = renderPage();
    await product('Продукт 1');

    const selectPage = async (count) => {
      const buttons = screen
        .getAllByRole('button', { pressed: false })
        .slice(0, count);
      for (const button of buttons) await user.click(button);
    };

    await selectPage(PAGE_SIZE);
    await user.click(screen.getByRole('button', { name: 'Наступна сторінка' }));
    await product('Продукт 13');
    await selectPage(PAGE_SIZE);
    await user.click(screen.getByRole('button', { name: 'Наступна сторінка' }));
    await product('Продукт 25');
    await selectPage(MAX_PRODUCTS - PAGE_SIZE * 2);

    expect(counter()).toHaveTextContent(`${MAX_PRODUCTS}/${MAX_PRODUCTS}`);
    expect(
      screen.getByText('Обрано максимальну кількість продуктів.'),
    ).toBeInTheDocument();
    expect(await product('Продукт 31')).toBeDisabled();
  });

  it('restores saved cart', async () => {
    const api = mockProductsApi({
      generation: makeGeneration({ product_ids: [2, 5] }),
    });
    renderPage();

    expect(
      await screen.findByRole('button', { name: 'Прибрати «Продукт 5»' }),
    ).toBeInTheDocument();
    expect(counter()).toHaveTextContent(`2/${MAX_PRODUCTS}`);
    expect(screen.getByRole('button', SUBMIT)).toBeEnabled();
    expect(
      api.requests.filter(({ path }) => path.startsWith('/products/')),
    ).toHaveLength(2);
  });
});

describe('ProductsPage: submit', () => {
  it('sends products and opens suggestions', async () => {
    const api = mockProductsApi();
    const { user } = renderPage();

    await user.click(await product('Продукт 1'));
    await user.click(await product('Продукт 3'));
    await user.click(screen.getByRole('button', SUBMIT));

    await waitFor(() =>
      expect(screen.getByTestId('location')).toHaveTextContent(
        '/generate/g-1/suggestions',
      ),
    );
    expect(
      api.requestsTo('POST', '/generations/g-1/suggestions')[0].body,
    ).toEqual({ product_ids: [1, 3] });
  });

  it('shows no recipes error', async () => {
    mockProductsApi({
      routes: {
        [SUGGEST]: () =>
          apiError(422, {
            code: 'NO_SUITABLE_RECIPES',
            message: 'За обраними інгредієнтами рецептів не знайдено.',
          }),
      },
    });
    const { user } = renderPage();

    await user.click(await product('Продукт 1'));
    await user.click(await product('Продукт 2'));
    await user.click(screen.getByRole('button', SUBMIT));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'рецептів не знайдено',
    );
    expect(screen.getByRole('button', SUBMIT)).toBeEnabled();
  });
});