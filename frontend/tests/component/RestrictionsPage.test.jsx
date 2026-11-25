import { screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import RestrictionsPage from '../../src/pages/generation/RestrictionsPage.jsx';
import { apiError, json, mockApi } from '../support/api.js';
import { RESTRICTIONS, makeGeneration } from '../support/fixtures.js';
import { renderWithRouter } from '../support/render.jsx';

const NEXT = { name: 'Далі: вибір продуктів' };

function mockRestrictionsApi(
  generation = makeGeneration({
    status: 'awaiting_restrictions',
    restrictions: [],
  }),
) {
  return mockApi({
    'GET /dietary-restrictions': () => json(RESTRICTIONS),
    'GET /generations/g-1': () => json(generation),
    'PUT /generations/g-1/restrictions': ({ body }) =>
      json(makeGeneration({ restrictions: body.restriction_ids })),
  });
}

function renderPage() {
  return renderWithRouter(<RestrictionsPage />, {
    route: '/generate/g-1/restrictions',
    path: '/generate/:generationId/restrictions',
  });
}

function checkbox(name) {
  return screen.getByRole('checkbox', { name });
}

describe('RestrictionsPage: options', () => {
  it('lists restrictions and none option', async () => {
    mockRestrictionsApi();
    renderPage();

    expect(screen.getByText('Завантаження…')).toBeInTheDocument();
    expect(
      await screen.findByRole('checkbox', { name: 'Веганська' }),
    ).not.toBeChecked();
    expect(screen.getAllByRole('checkbox')).toHaveLength(4);
    expect(screen.getByText('Обмеження').closest('li')).toHaveAttribute(
      'aria-current',
      'step',
    );
  });

  it('restores previous choice', async () => {
    mockRestrictionsApi(makeGeneration({ restrictions: [RESTRICTIONS[1]] }));
    renderPage();

    expect(
      await screen.findByRole('checkbox', { name: 'Без глютену' }),
    ).toBeChecked();
    expect(checkbox('Веганська')).not.toBeChecked();
  });

  it('restores none choice', async () => {
    mockRestrictionsApi(makeGeneration({ restrictions: [] }));
    renderPage();

    expect(
      await screen.findByRole('checkbox', { name: 'Обмежень немає' }),
    ).toBeChecked();
  });

  it('makes none exclusive', async () => {
    mockRestrictionsApi();
    const { user } = renderPage();

    await user.click(
      await screen.findByRole('checkbox', { name: 'Веганська' }),
    );
    await user.click(checkbox('Обмежень немає'));

    expect(checkbox('Веганська')).not.toBeChecked();
    expect(checkbox('Обмежень немає')).toBeChecked();

    await user.click(checkbox('Без лактози'));

    expect(checkbox('Обмежень немає')).not.toBeChecked();
  });
});

describe('RestrictionsPage: submit', () => {
  it('requires a choice', async () => {
    const api = mockRestrictionsApi();
    const { user } = renderPage();

    await user.click(await screen.findByRole('button', NEXT));

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Оберіть хоча б одне обмеження або позначте «Обмежень немає».',
    );
    expect(api.requestsTo('PUT', '/generations/g-1/restrictions')).toHaveLength(
      0,
    );
  });

  it('saves restrictions and opens products', async () => {
    const api = mockRestrictionsApi();
    const { user } = renderPage();

    await user.click(
      await screen.findByRole('checkbox', { name: 'Веганська' }),
    );
    await user.click(checkbox('Без лактози'));
    await user.click(screen.getByRole('button', NEXT));

    await waitFor(() =>
      expect(screen.getByTestId('location')).toHaveTextContent(
        '/generate/g-1/products',
      ),
    );
    expect(
      api.requestsTo('PUT', '/generations/g-1/restrictions')[0].body,
    ).toEqual({ restriction_ids: [1, 3] });
  });

  it('sends empty list for none', async () => {
    const api = mockRestrictionsApi();
    const { user } = renderPage();

    await user.click(
      await screen.findByRole('checkbox', { name: 'Обмежень немає' }),
    );
    await user.click(screen.getByRole('button', NEXT));

    await waitFor(() =>
      expect(
        api.requestsTo('PUT', '/generations/g-1/restrictions')[0].body,
      ).toEqual({ restriction_ids: [] }),
    );
  });
});

describe('RestrictionsPage: errors', () => {
  it('offers new generation when expired', async () => {
    mockApi({
      'GET /dietary-restrictions': () => json(RESTRICTIONS),
      'GET /generations/g-1': () =>
        apiError(404, {
          code: 'GENERATION_NOT_FOUND',
          message: 'Генерацію не знайдено або її термін дії минув.',
        }),
    });
    renderPage();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Генерацію не знайдено',
    );
    expect(
      screen.getByRole('button', { name: 'Почати нову генерацію' }),
    ).toBeInTheDocument();
  });

  it('retries after server error', async () => {
    let attempt = 0;
    mockApi({
      'GET /dietary-restrictions': () => {
        attempt += 1;
        return attempt === 1
          ? apiError(500, 'Сталася помилка на сервері.')
          : json(RESTRICTIONS);
      },
      'GET /generations/g-1': () =>
        json(makeGeneration({ status: 'awaiting_restrictions' })),
    });
    const { user } = renderPage();

    await user.click(
      await screen.findByRole('button', { name: 'Спробувати ще раз' }),
    );

    expect(
      await screen.findByRole('checkbox', { name: 'Веганська' }),
    ).toBeInTheDocument();
  });
});
