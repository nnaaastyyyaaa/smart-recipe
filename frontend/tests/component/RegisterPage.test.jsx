import { screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ApiError } from '../../src/api/client.js';
import RegisterPage from '../../src/pages/auth/RegisterPage.jsx';
import { USER } from '../support/fixtures.js';
import { makeAuth, renderWithRouter } from '../support/render.jsx';

function renderRegister(register = vi.fn().mockResolvedValue(USER)) {
  return renderWithRouter(<RegisterPage />, {
    route: '/register',
    path: '/register',
    auth: makeAuth({ status: 'guest', user: null, register }),
  });
}

async function fillForm(
  user,
  {
    name = USER.name,
    email = USER.email,
    password = 'Secret123',
    confirmPassword = password,
  } = {},
) {
  await user.type(screen.getByLabelText("Ім'я"), name);
  await user.type(screen.getByLabelText('Електронна пошта'), email);
  await user.type(screen.getByLabelText('Пароль'), password);
  await user.type(screen.getByLabelText('Повторіть пароль'), confirmPassword);
  await user.click(screen.getByRole('button', { name: 'Зареєструватися' }));
}

describe('RegisterPage: form validation', () => {
  it('describes password rules', () => {
    renderRegister();

    expect(screen.getByLabelText('Пароль')).toHaveAccessibleDescription(
      /Від 8 до 16 символів/,
    );
  });

  it('blocks invalid data', async () => {
    const { user, auth } = renderRegister();

    await fillForm(user, {
      name: 'В',
      email: 'nika@',
      password: 'short',
      confirmPassword: 'other',
    });

    expect(screen.getByText(/від 2 до 24 символів/)).toBeInTheDocument();
    expect(
      screen.getByText('Введіть коректну електронну пошту'),
    ).toBeInTheDocument();
    expect(screen.getByText(/від 8 до 16 символів/)).toBeInTheDocument();
    expect(screen.getByText('Паролі не збігаються')).toBeInTheDocument();
    expect(auth.register).not.toHaveBeenCalled();
  });
});

describe('RegisterPage: submit', () => {
  it('registers and goes home', async () => {
    const { user, auth } = renderRegister();

    await fillForm(user, { name: `  ${USER.name}  ` });

    expect(auth.register).toHaveBeenCalledWith({
      name: USER.name,
      email: USER.email,
      password: 'Secret123',
    });
    await waitFor(() =>
      expect(screen.getByTestId('location')).toHaveTextContent(/^\/$/),
    );
  });

  it('marks taken email', async () => {
    const register = vi.fn().mockRejectedValue(
      new ApiError({
        status: 409,
        message: 'Користувач із таким email уже існує.',
      }),
    );
    const { user } = renderRegister(register);

    await fillForm(user);

    const email = screen.getByLabelText('Електронна пошта');
    await waitFor(() => expect(email).toHaveAttribute('aria-invalid', 'true'));
    expect(email).toHaveAccessibleDescription(
      'Користувач із таким email уже існує.',
    );
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('shows other server errors', async () => {
    const register = vi.fn().mockRejectedValue(
      new ApiError({
        status: 0,
        message: 'Не вдалося зʼєднатися із сервером.',
      }),
    );
    const { user } = renderRegister(register);

    await fillForm(user);

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Не вдалося зʼєднатися із сервером.',
    );
    expect(
      screen.getByRole('button', { name: 'Зареєструватися' }),
    ).toBeEnabled();
  });
});
