import { apiFetch } from './client.js';

export function getDietaryRestrictions({ signal } = {}) {
  return apiFetch('/dietary-restrictions', { signal });
}

export function getProduct(productId, { signal } = {}) {
  return apiFetch(`/products/${productId}`, { signal });
}
