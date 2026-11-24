import { screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ApiError } from '../../src/api/client.js';
import LoginPage from '../../src/pages/auth/LoginPage.jsx';
import { USER } from '../support/fixtures.js';
import { makeAuth, renderWithRouter } from '../support/render.jsx';

function renderLogin({ login = vi.fn().mockResolvedValue(USER), state } = {}) {
  return renderWithRouter(<LoginPage />, {
    route: { pathname: '/login', state },
    path: '/login',
    auth: makeAuth({ status: 'guest', user: null, login }),
  });
}

async function fillForm(user, password = 'Secret123') {
  await user.type(screen.getByLabelText('Електронна пошта'), USER.email);
  await user.type(screen.getByLabelText('Пароль'), password);
  await user.click(screen.getByRole('button', { name: 'Увійти' }));
}

describe('LoginPage: form validation', () => {
  it('shows errors for empty form', async () => {
    const { user, auth } = renderLogin();

    await user.click(screen.getByRole('button', { name: 'Увійти' }));

    expect(screen.getByText('Введіть електронну пошту')).toBeInTheDocument();
    expect(screen.getByText('Введіть пароль')).toBeInTheDocument();
    expect(screen.getByLabelText('Електронна пошта')).toHaveAttribute(
      'aria-invalid',
      'true',
    );
    expect(auth.login).not.toHaveBeenCalled();
  });

  it('clears field error on input', async () => {
    const { user } = renderLogin();

    await user.click(screen.getByRole('button', { name: 'Увійти' }));
    await user.type(screen.getByLabelText('Електронна пошта'), 'n');

    expect(
      screen.queryByText('Введіть електронну пошту'),
    ).not.toBeInTheDocument();
  });

  it('toggles password visibility', async () => {
    const { user } = renderLogin();
    const input = screen.getByLabelText('Пароль');

    await user.click(screen.getByRole('button', { name: 'Показати пароль' }));
    expect(input).toHaveAttribute('type', 'text');

    await user.click(screen.getByRole('button', { name: 'Сховати пароль' }));
    expect(input).toHaveAttribute('type', 'password');
  });
});

describe('LoginPage: submit', () => {
  it('logs in and goes home', async () => {
    const { user, auth } = renderLogin();

    await fillForm(user);

    expect(auth.login).toHaveBeenCalledWith({
      email: USER.email,
      password: 'Secret123',
    });
    await waitFor(() =>
      expect(screen.getByTestId('location')).toHaveTextContent(/^\/$/),
    );
  });

  it('returns to requested page', async () => {
    const { user } = renderLogin({
      state: { from: { pathname: '/profile/favorites', search: '' } },
    });

    await fillForm(user);

    await waitFor(() =>
      expect(screen.getByTestId('location')).toHaveTextContent(
        '/profile/favorites',
      ),
    );
  });

  it('shows server error', async () => {
    const login = vi
      .fn()
      .mockRejectedValue(
        new ApiError({ status: 401, message: 'Невірний email або пароль.' }),
      );
    const { user } = renderLogin({ login });

    await fillForm(user, 'WrongPass1');

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Невірний email або пароль.',
    );
    expect(screen.getByRole('button', { name: 'Увійти' })).toBeEnabled();
    expect(screen.getByTestId('location')).toHaveTextContent('/login');
  });
});
