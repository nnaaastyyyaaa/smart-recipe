import { ROUTES } from '../routes.js';

export function getRedirectPath(location) {
  const from = location.state?.from;

  if (!from?.pathname) return ROUTES.home;

  return `${from.pathname}${from.search ?? ''}`;
}