import { apiError, json, mockApi, noContent } from './api.js';
import {
  PASSWORD,
  USER,
  makeGeneratedRecipe,
  makeSavedRecipes,
  makeSuggestionsPage,
} from './fixtures.js';

const UNAUTHORIZED = 'Не авторизовано.';
const RECIPE_NOT_FOUND = 'Збережений рецепт не знайдений.';

export function createFakeBackend({
  isLoggedIn = false,
  savedCount = 0,
  suggestionsTotal = 12,
} = {}) {
  const state = {
    user: isLoggedIn ? USER : null,
    password: PASSWORD,
    saved: makeSavedRecipes(savedCount),
    nextRecipeId: savedCount + 1,
  };

  function authorized(handler) {
    return (request) =>
      state.user ? handler(request) : apiError(401, UNAUTHORIZED);
  }

  function findSaved(id) {
    return state.saved.find((recipe) => recipe.id === Number(id));
  }

  const api = mockApi({
    'GET /auth/me': authorized(() => json(state.user)),

    'POST /auth/login': ({ body }) => {
      if (body.email !== USER.email || body.password !== state.password) {
        return apiError(401, 'Невірний email або пароль.');
      }
      state.user = USER;
      return json(USER);
    },

    'POST /auth/logout': () => {
      state.user = null;
      return noContent();
    },

    'PATCH /users/me/password': authorized(({ body }) => {
      if (body.current_password !== state.password) {
        return apiError(400, 'Невірний поточний пароль.');
      }
      state.password = body.new_password;
      return noContent();
    }),

    'GET /recipes/saved': authorized(({ query }) => {
      const offset = Number(query.offset);
      const limit = Number(query.limit);

      return json(state.saved.slice(offset, offset + limit), {
        headers: { 'X-Total-Count': String(state.saved.length) },
      });
    }),

    'GET /recipes/saved/:id': authorized(({ params }) => {
      const recipe = findSaved(params.id);
      return recipe ? json(recipe) : apiError(404, RECIPE_NOT_FOUND);
    }),

    'DELETE /recipes/saved/:id': authorized(({ params }) => {
      const recipe = findSaved(params.id);
      if (!recipe) return apiError(404, RECIPE_NOT_FOUND);

      state.saved = state.saved.filter((item) => item !== recipe);
      return noContent();
    }),

    'POST /recipes/saved': authorized(({ body }) => {
      const recipe = { id: state.nextRecipeId, ...body };
      state.nextRecipeId += 1;
      state.saved = [...state.saved, recipe];
      return json(recipe, { status: 201 });
    }),

    'GET /generations/:id/suggestions': authorized(({ query }) =>
      json(
        makeSuggestionsPage(Number(query.page), { total: suggestionsTotal }),
      ),
    ),

    'POST /generations/:id/recipe': authorized(({ body }) =>
      json(makeGeneratedRecipe(body.suggestion_id)),
    ),
  });

  return { state, ...api };
}
