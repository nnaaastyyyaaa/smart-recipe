import { apiFetch } from './client.js';

export async function getSavedRecipes({ limit, offset, signal } = {}) {
  const { data, headers } = await apiFetch('/recipes/saved', {
    query: { limit, offset },
    signal,
    withHeaders: true,
  });

  const total = Number(headers.get('X-Total-Count'));

  return { items: data, total: Number.isFinite(total) ? total : data.length };
}

export function deleteSavedRecipe(recipeId) {
  return apiFetch(`/recipes/saved/${recipeId}`, { method: 'DELETE' });
}
