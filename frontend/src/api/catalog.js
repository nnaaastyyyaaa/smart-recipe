import { apiFetch } from './client.js';

export function getDietaryRestrictions({ signal } = {}) {
  return apiFetch('/dietary-restrictions', { signal });
}