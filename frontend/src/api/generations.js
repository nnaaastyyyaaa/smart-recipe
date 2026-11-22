import { apiFetch } from './client.js';

export function startGeneration() {
  return apiFetch('/generations', { method: 'POST' });
}