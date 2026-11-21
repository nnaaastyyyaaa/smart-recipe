export const ROUTES = {
  home: '/',
  login: '/login',
  profile: '/profile',
  favorites: '/profile/favorites',
  favoriteRecipe: (recipeId) => `/profile/favorites/${recipeId}`,
};
