import { render, screen } from '@testing-library/react';
import { Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import AuthProvider from '../../src/auth/AuthProvider.jsx';
import { useAuth } from '../../src/auth/useAuth.js';
import ProtectedRoute from '../../src/components/ProtectedRoute.jsx';
import {
  apiError,
  deferred,
  json,
  mockApi,
  noContent,
} from '../support/api.js';
import { USER } from '../support/fixtures.js';
import { makeAuth, renderWithRouter } from '../support/render.jsx';

function SessionProbe() {
  const { status, user, logout } = useAuth();

  return (
    <>
      <p data-testid='status'>{status}</p>
      <p data-testid='name'>{user?.name ?? '—'}</p>
      <button type='button' onClick={() => logout().catch(() => {})}>
        Вийти
      </button>
    </>
  );
}

function renderSession() {
  return renderWithRouter(
    <AuthProvider>
      <SessionProbe />
    </AuthProvider>,
    { route: '/profile', path: '*' },
  );
}

describe('AuthProvider: session state', () => {
  it('loads current user', async () => {
    const pending = deferred();
    const api = mockApi({ 'GET /auth/me': () => pending.promise });
    renderSession();

    expect(screen.getByTestId('status')).toHaveTextContent('loading');

    pending.resolve(json(USER));

    expect(await screen.findByText('authenticated')).toBeInTheDocument();
    expect(screen.getByTestId('name')).toHaveTextContent(USER.name);
    expect(api.requests[0].init.credentials).toBe('include');
  });

  it('treats 401 as guest', async () => {
    mockApi({ 'GET /auth/me': () => apiError(401, 'Не авторизовано.') });
    renderSession();

    expect(await screen.findByText('guest')).toBeInTheDocument();
  });

  it('logs out and goes home', async () => {
    const api = mockApi({
      'GET /auth/me': () => json(USER),
      'POST /auth/logout': () => noContent(),
    });
    const { user } = renderSession();
    await screen.findByText('authenticated');

    await user.click(screen.getByRole('button', { name: 'Вийти' }));

    expect(await screen.findByText('guest')).toBeInTheDocument();
    expect(screen.getByTestId('location')).toHaveTextContent(/^\/$/);
    expect(api.requestsTo('POST', '/auth/logout')).toHaveLength(1);
  });

  it('keeps session if logout fails', async () => {
    mockApi({
      'GET /auth/me': () => json(USER),
      'POST /auth/logout': () => apiError(500, 'Внутрішня помилка сервера.'),
    });
    const { user } = renderSession();
    await screen.findByText('authenticated');

    await user.click(screen.getByRole('button', { name: 'Вийти' }));

    expect(screen.getByTestId('status')).toHaveTextContent('authenticated');
    expect(screen.getByTestId('location')).toHaveTextContent('/profile');
  });

  it('requires provider for useAuth', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => render(<SessionProbe />)).toThrow(
      'useAuth потрібно викликати всередині <AuthProvider>',
    );
  });
});

describe('ProtectedRoute: access control', () => {
  function renderProtected(status) {
    return renderWithRouter(
      <Routes>
        <Route element={<ProtectedRoute />}>
          <Route path='/profile' element={<p>Закрита сторінка</p>} />
        </Route>
        <Route path='/login' element={<p>Сторінка входу</p>} />
      </Routes>,
      { route: '/profile', path: '*', auth: makeAuth({ status }) },
    );
  }

  it('waits for session check', () => {
    renderProtected('loading');

    expect(screen.getByText('Завантаження…')).toBeInTheDocument();
    expect(screen.queryByText('Закрита сторінка')).not.toBeInTheDocument();
  });

  it('redirects guest to login', () => {
    renderProtected('guest');

    expect(screen.getByText('Сторінка входу')).toBeInTheDocument();
    expect(screen.queryByText('Закрита сторінка')).not.toBeInTheDocument();
  });

  it('renders page for user', () => {
    renderProtected('authenticated');

    expect(screen.getByText('Закрита сторінка')).toBeInTheDocument();
  });
});
