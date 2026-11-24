import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import ChangePasswordForm from '../../src/components/profile/ChangePasswordForm.jsx';
import { apiError, deferred, mockApi, noContent } from '../support/api.js';

function renderForm() {
  const user = userEvent.setup({ delay: null });
  render(<ChangePasswordForm />);

  const fields = {
    current: screen.getByLabelText('Поточний пароль'),
    next: screen.getByLabelText('Новий пароль'),
    confirm: screen.getByLabelText('Повторіть новий пароль'),
  };

  async function fill(current, next, confirm = next) {
    await user.type(fields.current, current);
    await user.type(fields.next, next);
    await user.type(fields.confirm, confirm);
  }

  function submit() {
    return user.click(screen.getByRole('button', { name: 'Змінити пароль' }));
  }

  return { user, fields, fill, submit };
}

describe('ChangePasswordForm: input validation', () => {
  it('requires all fields', async () => {
    const api = mockApi();
    const { fields, submit } = renderForm();

    await submit();

    expect(fields.current).toHaveAttribute('aria-invalid', 'true');
    expect(fields.current).toHaveAccessibleDescription(
      'Введіть поточний пароль',
    );
    expect(fields.next).toHaveAccessibleDescription(/Введіть новий пароль$/);
    expect(fields.confirm).toHaveAccessibleDescription(
      'Повторіть новий пароль',
    );
    expect(api.requests).toHaveLength(0);
  });

  it.each([
    ['Short1', 'Пароль має містити від 8 до 16 символів'],
    [
      'Пароль1234',
      'Пароль може містити лише латинські літери, цифри та спеціальні символи',
    ],
  ])('rejects new password "%s"', async (password, message) => {
    const api = mockApi();
    const { fill, submit } = renderForm();

    await fill('OldPass123', password);
    await submit();

    expect(screen.getByText(message)).toBeInTheDocument();
    expect(api.requests).toHaveLength(0);
  });

  it('rejects mismatched confirmation', async () => {
    const { fill, submit } = renderForm();

    await fill('OldPass123', 'NewPass123', 'NewPass124');
    await submit();

    expect(screen.getByText('Паролі не збігаються')).toBeInTheDocument();
  });
});

describe('ChangePasswordForm: server response', () => {
  it('changes password and clears form', async () => {
    const pending = deferred();
    const api = mockApi({ 'PATCH /users/me/password': () => pending.promise });
    const { fields, fill, submit } = renderForm();

    await fill('OldPass123', 'NewPass123!');
    await submit();

    expect(screen.getByRole('button', { name: 'Збереження…' })).toBeDisabled();

    pending.resolve(noContent());

    expect(
      await screen.findByRole('button', { name: 'Пароль змінено' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent(
      'Пароль успішно змінено.',
    );
    expect(api.requests[0].body).toEqual({
      current_password: 'OldPass123',
      new_password: 'NewPass123!',
    });
    expect(fields.current).toHaveValue('');
    expect(fields.next).toHaveValue('');
    expect(fields.confirm).toHaveValue('');
  });

  it('marks wrong current password', async () => {
    mockApi({
      'PATCH /users/me/password': () =>
        apiError(400, 'Невірний поточний пароль.'),
    });
    const { fields, fill, submit } = renderForm();

    await fill('WrongPass1', 'NewPass123');
    await submit();

    expect(
      await screen.findByText('Невірний поточний пароль.'),
    ).toBeInTheDocument();
    expect(fields.current).toHaveAttribute('aria-invalid', 'true');
    expect(
      screen.getByRole('button', { name: 'Змінити пароль' }),
    ).toBeEnabled();
  });

  it('shows server error', async () => {
    mockApi({
      'PATCH /users/me/password': () =>
        apiError(500, 'Внутрішня помилка сервера.'),
    });
    const { fill, submit } = renderForm();

    await fill('OldPass123', 'NewPass123');
    await submit();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Внутрішня помилка сервера.',
    );
  });
});

describe('ChangePasswordForm: password visibility', () => {
  it('toggles password visibility', async () => {
    const { user, fields } = renderForm();
    const [toggle] = screen.getAllByRole('button', { name: 'Показати пароль' });

    await user.click(toggle);

    expect(fields.current).toHaveAttribute('type', 'text');
    expect(toggle).toHaveAccessibleName('Сховати пароль');
  });
});
