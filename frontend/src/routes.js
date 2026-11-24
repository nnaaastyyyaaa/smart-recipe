export const ROUTES = {
  home: '/',
  login: '/login',
  register: '/register',
  profile: '/profile',
  favorites: '/profile/favorites',
  favoriteRecipe: (recipeId) => `/profile/favorites/${recipeId}`,
  generationRestrictions: (generationId) =>
    `/generate/${generationId}/restrictions`,
  generationProducts: (generationId) => `/generate/${generationId}/products`,
  generationSuggestions: (generationId) =>
    `/generate/${generationId}/suggestions`,
  generationRecipe: (generationId, suggestionId) =>
    `/generate/${generationId}/recipe/${suggestionId}`,
};