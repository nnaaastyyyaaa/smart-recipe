import { render } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { vi } from 'vitest';
import App from '../../src/App.jsx';
import { AuthContext } from '../../src/auth/AuthContext.js';
import { USER } from './fixtures.js';
import LocationDisplay from './LocationDisplay.jsx';

export function makeAuth(overrides = {}) {
  return {
    user: USER,
    status: 'authenticated',
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
}

export function renderWithRouter(
  ui,
  { route = '/', path = '/', auth = makeAuth() } = {},
) {
  const user = userEvent.setup({ delay: null });

  const result = render(
    <AuthContext.Provider value={auth}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path={path} element={ui} />
          <Route path='*' element={null} />
        </Routes>
        <LocationDisplay />
      </MemoryRouter>
    </AuthContext.Provider>,
  );

  return { user, auth, ...result };
}

export function renderApp(route = '/') {
  window.history.pushState(null, '', route);
  const user = userEvent.setup({ delay: null });

  return { user, ...render(<App />) };
}
