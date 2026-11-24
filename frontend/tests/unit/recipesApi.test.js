import { describe, expect, it } from 'vitest';
import { getSavedRecipes, saveRecipe } from '../../src/api/recipes.js';
import { json, mockApi } from '../support/api.js';
import { makeSavedRecipe, makeSavedRecipes } from '../support/fixtures.js';

describe('Saved recipes API: count and payload', () => {
  it('reads total from header', async () => {
    const api = mockApi({
      'GET /recipes/saved': () =>
        json(makeSavedRecipes(12), { headers: { 'X-Total-Count': '13' } }),
    });

    const result = await getSavedRecipes({ limit: 12, offset: 12 });

    expect(api.requests[0].query).toEqual({ limit: '12', offset: '12' });
    expect(result).toMatchObject({ total: 13 });
  });

  it('falls back to list length', async () => {
    mockApi({ 'GET /recipes/saved': () => json(makeSavedRecipes(3)) });

    const result = await getSavedRecipes({ limit: 12, offset: 0 });

    expect(result.total).toBe(3);
  });

  it('sends only backend fields', async () => {
    const api = mockApi({
      'POST /recipes/saved': ({ body }) =>
        json({ id: 1, ...body }, { status: 201 }),
    });
    const { id, ...fields } = makeSavedRecipe(1);

    await saveRecipe({ id, ...fields, extra: 'зайве' });

    expect(api.requests[0].body).toEqual(fields);
  });
});
