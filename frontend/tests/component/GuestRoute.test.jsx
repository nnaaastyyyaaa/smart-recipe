import { screen } from '@testing-library/react';
import { Route, Routes } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import GuestRoute from '../../src/components/GuestRoute.jsx';
import { makeAuth, renderWithRouter } from '../support/render.jsx';

function renderGuestRoute(status, state) {
  return renderWithRouter(
    <Routes>
      <Route element={<GuestRoute />}>
        <Route path='/login' element={<p>Форма входу</p>} />
      </Route>
      <Route path='*' element={<p>Інша сторінка</p>} />
    </Routes>,
    {
      route: { pathname: '/login', state },
      path: '*',
      auth: makeAuth({ status }),
    },
  );
}

describe('GuestRoute: access control', () => {
  it('waits for session check', () => {
    renderGuestRoute('loading');

    expect(screen.getByText('Завантаження…')).toBeInTheDocument();
    expect(screen.queryByText('Форма входу')).not.toBeInTheDocument();
  });

  it('renders form for guest', () => {
    renderGuestRoute('guest');

    expect(screen.getByText('Форма входу')).toBeInTheDocument();
  });

  it('sends user home', () => {
    renderGuestRoute('authenticated');

    expect(screen.getByTestId('location')).toHaveTextContent(/^\/$/);
  });

  it('sends user to requested page', () => {
    renderGuestRoute('authenticated', { from: { pathname: '/profile' } });

    expect(screen.getByTestId('location')).toHaveTextContent('/profile');
  });
});
