import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ApiError } from '../../src/api/client.js';
import Header from '../../src/components/header/Header.jsx';
import ProfilePage from '../../src/pages/profile/ProfilePage.jsx';
import { deferred } from '../support/api.js';
import { USER } from '../support/fixtures.js';
import { makeAuth, renderWithRouter } from '../support/render.jsx';

const GUEST = makeAuth({ status: 'guest', user: null });

function renderProfile(auth = makeAuth()) {
  return renderWithRouter(<ProfilePage />, {
    route: '/profile',
    path: '/profile',
    auth,
  });
}

describe('ProfilePage: user info', () => {
  it('shows name and email', () => {
    renderProfile();

    expect(
      screen.getByRole('heading', { level: 1, name: 'Профіль' }),
    ).toBeInTheDocument();
    expect(screen.getByText(USER.name)).toBeInTheDocument();
    expect(screen.getByText(USER.email)).toBeInTheDocument();
  });

  it('shows profile tabs', () => {
    renderProfile();

    expect(screen.getByRole('link', { name: 'Особисті дані' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(
      screen.getByRole('link', { name: 'Улюблені рецепти' }),
    ).toHaveAttribute('href', '/profile/favorites');
  });
});

describe('ProfilePage: logout button', () => {
  it('locks button while logging out', async () => {
    const pending = deferred();
    const auth = makeAuth({ logout: vi.fn(() => pending.promise) });
    const { user } = renderProfile(auth);

    await user.click(screen.getByRole('button', { name: 'Вийти' }));

    expect(screen.getByRole('button', { name: 'Вихід…' })).toBeDisabled();
    expect(auth.logout).toHaveBeenCalledTimes(1);
  });

  it('shows logout error', async () => {
    const auth = makeAuth({
      logout: vi.fn().mockRejectedValue(
        new ApiError({
          status: 0,
          message: 'Не вдалося зʼєднатися із сервером.',
        }),
      ),
    });
    const { user } = renderProfile(auth);

    await user.click(screen.getByRole('button', { name: 'Вийти' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Не вдалося зʼєднатися із сервером.',
    );
    expect(screen.getByRole('button', { name: 'Вийти' })).toBeEnabled();
  });
});

describe('Header: profile avatar', () => {
  it('hides avatar for guest', () => {
    renderWithRouter(<Header />, { auth: GUEST });

    expect(
      screen.getByRole('link', { name: 'SmartRecipe: на головну' }),
    ).toHaveAttribute('href', '/');
    expect(
      screen.queryByRole('link', { name: 'Профіль' }),
    ).not.toBeInTheDocument();
  });

  it('shows user initial', () => {
    renderWithRouter(<Header />);

    const avatar = screen.getByRole('link', { name: 'Профіль' });
    expect(avatar).toHaveAttribute('href', '/profile');
    expect(avatar).toHaveTextContent('С');
  });

  it('hides avatar in profile', () => {
    renderWithRouter(<Header />, { route: '/profile/favorites', path: '*' });

    expect(
      screen.queryByRole('link', { name: 'Профіль' }),
    ).not.toBeInTheDocument();
  });
});
