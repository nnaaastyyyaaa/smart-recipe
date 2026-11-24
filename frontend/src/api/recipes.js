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

export function getSavedRecipe(recipeId, { signal } = {}) {
  return apiFetch(`/recipes/saved/${recipeId}`, { signal });
}

export function saveRecipe(recipe) {
  return apiFetch('/recipes/saved', {
    method: 'POST',
    body: {
      title: recipe.title,
      description: recipe.description,
      ingredients: recipe.ingredients,
      instructions: recipe.instructions,
      cooking_time: recipe.cooking_time,
    },
  });
}
