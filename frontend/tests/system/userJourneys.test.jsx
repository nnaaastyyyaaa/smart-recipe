import { screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { createFakeBackend } from '../support/fakeBackend.js';
import { PASSWORD, USER } from '../support/fixtures.js';
import { renderApp } from '../support/render.jsx';

function expectPath(path) {
  return waitFor(() =>
    expect(`${window.location.pathname}${window.location.search}`).toBe(path),
  );
}

function cardTitles() {
  return screen
    .getAllByRole('heading', { level: 3 })
    .map((heading) => heading.textContent);
}

describe('User journeys: profile', () => {
  it('changes password and logs out', async () => {
    const backend = createFakeBackend({ isLoggedIn: true });
    const { user } = renderApp('/');

    await user.click(await screen.findByRole('link', { name: 'Профіль' }));
    await expectPath('/profile');
    expect(screen.getByText(USER.email)).toBeInTheDocument();

    await user.type(screen.getByLabelText('Поточний пароль'), PASSWORD);
    await user.type(screen.getByLabelText('Новий пароль'), 'NewPass123');
    await user.type(
      screen.getByLabelText('Повторіть новий пароль'),
      'NewPass123',
    );
    await user.click(screen.getByRole('button', { name: 'Змінити пароль' }));

    expect(
      await screen.findByRole('button', { name: 'Пароль змінено' }),
    ).toBeInTheDocument();
    expect(backend.state.password).toBe('NewPass123');

    await user.click(screen.getByRole('button', { name: 'Вийти' }));

    await expectPath('/');
    expect(
      await screen.findByRole('link', { name: 'Увійти' }),
    ).toBeInTheDocument();
    expect(backend.state.user).toBeNull();
  });
});

describe('User journeys: favorites', () => {
  it('browses and deletes recipe', async () => {
    const backend = createFakeBackend({ isLoggedIn: true, savedCount: 13 });
    const { user } = renderApp('/profile');

    await user.click(
      await screen.findByRole('link', { name: 'Улюблені рецепти' }),
    );
    expect(
      await screen.findByText('Збережено рецептів: 13'),
    ).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '2' }));
    await waitFor(() => expect(cardTitles()).toEqual(['Рецепт 13']));

    await user.click(
      screen.getByRole('link', { name: 'Детальніше: Рецепт 13' }),
    );
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Рецепт 13' }),
    ).toBeInTheDocument();
    const ingredients = screen.getByRole('heading', {
      name: 'Інгредієнти',
    }).parentElement;
    expect(within(ingredients).getAllByRole('listitem')).toHaveLength(3);

    await user.click(screen.getByRole('button', { name: 'Видалити рецепт' }));
    await user.click(screen.getByRole('button', { name: 'Так, видалити' }));

    await expectPath('/profile/favorites');
    expect(
      await screen.findByText('Збережено рецептів: 12'),
    ).toBeInTheDocument();
    expect(backend.state.saved).toHaveLength(12);
  });

  it('saves recipe from suggestions', async () => {
    const backend = createFakeBackend({ isLoggedIn: true });
    const { user } = renderApp('/generate/g-1/suggestions');

    expect(await screen.findByText('Страва 0')).toBeInTheDocument();
    await user.click(
      screen.getByRole('button', { name: 'Показати інші рецепти' }),
    );
    await user.click(
      await screen.findByRole('link', { name: 'Детальніше: Страва 9' }),
    );

    await expectPath('/generate/g-1/recipe/9');
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Страва 9' }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Зберегти' }));
    expect(
      await screen.findByRole('button', { name: 'Збережено' }),
    ).toBeInTheDocument();
    expect(backend.state.saved.map(({ title }) => title)).toEqual(['Страва 9']);

    await user.click(screen.getByRole('link', { name: 'Назад до варіантів' }));
    expect(await screen.findByText('Страва 0')).toBeInTheDocument();

    await user.click(screen.getByRole('link', { name: 'Профіль' }));
    await user.click(
      await screen.findByRole('link', { name: 'Улюблені рецепти' }),
    );

    expect(
      await screen.findByRole('heading', { name: 'Страва 9' }),
    ).toBeInTheDocument();
  });
});

describe('User journeys: unknown page', () => {
  it('shows 404 and returns home', async () => {
    createFakeBackend();
    const { user } = renderApp('/no-such-page');

    expect(
      await screen.findByRole('heading', { name: 'Сторінку не знайдено' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: 'SmartRecipe: на головну' }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole('link', { name: 'На головну' }));

    await expectPath('/');
  });
});
