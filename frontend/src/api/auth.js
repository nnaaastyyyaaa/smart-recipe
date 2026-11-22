import { apiFetch } from './client.js';

export function getMe({ signal } = {}) {
  return apiFetch('/auth/me', { signal });
}

export function login({ email, password }) {
  return apiFetch('/auth/login', {
    method: 'POST',
    body: { email, password },
  });
}

export function register({ name, email, password }) {
  return apiFetch('/auth/register', {
    method: 'POST',
    body: { name, email, password },
  });
}