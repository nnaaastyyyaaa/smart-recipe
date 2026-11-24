import { apiFetch } from './client.js';

export function startGeneration() {
  return apiFetch('/generations', { method: 'POST' });
}

export function getGeneration(generationId, { signal } = {}) {
  return apiFetch(`/generations/${generationId}`, { signal });
}

export function setGenerationRestrictions(generationId, restrictionIds) {
  return apiFetch(`/generations/${generationId}/restrictions`, {
    method: 'PUT',
    body: { restriction_ids: restrictionIds },
  });
}

export function getGenerationCategories(generationId, { signal } = {}) {
  return apiFetch(`/generations/${generationId}/categories`, { signal });
}

export function getGenerationProducts(
  generationId,
  { categoryId, search, limit, offset, signal } = {},
) {
  return apiFetch(`/generations/${generationId}/products`, {
    query: { category_id: categoryId, search, limit, offset },
    signal,
  });
}

export function suggestRecipes(generationId, productIds) {
  return apiFetch(`/generations/${generationId}/suggestions`, {
    method: 'POST',
    body: { product_ids: productIds },
  });
}

export function generateRecipe(generationId, suggestionId) {
  return apiFetch(`/generations/${generationId}/recipe`, {
    method: 'POST',
    body: { suggestion_id: suggestionId },
  });
}

export function getSuggestionsPage(generationId, page, { signal } = {}) {
  return apiFetch(`/generations/${generationId}/suggestions`, {
    query: { page },
    signal,
  });
}
