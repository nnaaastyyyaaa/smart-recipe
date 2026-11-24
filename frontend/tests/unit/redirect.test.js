import { describe, expect, it } from 'vitest';
import { getRedirectPath } from '../../src/auth/redirect.js';

describe('getRedirectPath: return after login', () => {
  it('defaults to home', () => {
    expect(getRedirectPath({ state: null })).toBe('/');
  });

  it('returns saved page with query', () => {
    const location = {
      state: { from: { pathname: '/profile/favorites', search: '?page=2' } },
    };

    expect(getRedirectPath(location)).toBe('/profile/favorites?page=2');
  });
});
