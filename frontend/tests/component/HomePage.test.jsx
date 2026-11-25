import { screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import HomePage from '../../src/pages/home/HomePage.jsx';
import { apiError, deferred, json, mockApi } from '../support/api.js';
import { USER } from '../support/fixtures.js';
import { makeAuth, renderWithRouter } from '../support/render.jsx';

const START = 'POST /generations';

function renderHome(auth = makeAuth()) {
  return renderWithRouter(<HomePage />, { auth });
}

describe('HomePage: content', () => {
  it('explains steps in order', () => {
    renderHome(makeAuth({ status: 'guest', user: null }));

    expect(
      screen.getByRole('heading', {
        level: 1,
        name: 'Що приготувати з того, що вже є вдома?',
      }),
    ).toBeInTheDocument();
    expect(
      screen
        .getAllByRole('heading', { level: 3 })
        .map((heading) => heading.textContent),
    ).toEqual([
      'Оберіть обмеження',
      'Відмітьте продукти',
      'Отримайте ідеї',
      'Збережіть рецепт',
    ]);
  });

  it('hides illustration from screen readers', () => {
    const { container } = renderHome();

    expect(container.querySelector('.fridge')).toHaveAttribute(
      'aria-hidden',
      'true',
    );
  });
});

describe('HomePage: actions', () => {
  it('waits for session check', () => {
    renderHome(makeAuth({ status: 'loading', user: null }));

    expect(screen.getByText('Завантаження…')).toBeInTheDocument();
  });

  it('offers guest to sign up', () => {
    renderHome(makeAuth({ status: 'guest', user: null }));

    expect(
      screen.getByRole('link', { name: 'Зареєструватися' }),
    ).toHaveAttribute('href', '/register');
    expect(screen.getByRole('link', { name: 'Увійти' })).toHaveAttribute(
      'href',
      '/login',
    );
    expect(
      screen.queryByRole('button', { name: 'Почати генерацію' }),
    ).not.toBeInTheDocument();
  });

  it('greets user', () => {
    renderHome();

    expect(screen.getByText(`Вітаємо, ${USER.name}!`)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Мої рецепти' })).toHaveAttribute(
      'href',
      '/profile/favorites',
    );
  });

  it('starts generation', async () => {
    const pending = deferred();
    const api = mockApi({ [START]: () => pending.promise });
    const { user } = renderHome();

    await user.click(screen.getByRole('button', { name: 'Почати генерацію' }));

    expect(screen.getByRole('button', { name: 'Створення…' })).toBeDisabled();

    pending.resolve(json({ id: 'g-1' }, { status: 201 }));

    await waitFor(() =>
      expect(screen.getByTestId('location')).toHaveTextContent(
        '/generate/g-1/restrictions',
      ),
    );
    expect(api.requestsTo('POST', '/generations')).toHaveLength(1);
  });

  it('shows start error', async () => {
    mockApi({ [START]: () => apiError(500, 'Сталася помилка на сервері.') });
    const { user } = renderHome();

    await user.click(screen.getByRole('button', { name: 'Почати генерацію' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Сталася помилка на сервері.',
    );
    expect(
      screen.getByRole('button', { name: 'Почати генерацію' }),
    ).toBeEnabled();
  });
});
