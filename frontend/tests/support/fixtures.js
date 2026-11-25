export const USER = {
  id: '7c9e6679-7425-40de-944b-e07fc1f90ae7',
  name: 'Станіслав',
  email: 'stanislav@example.com',
};

export const PASSWORD = 'Secret123';

export function makeSavedRecipe(id) {
  return {
    id,
    title: `Рецепт ${id}`,
    description: `Опис рецепта ${id}`,
    ingredients: 'Борошно — 200 г\nЯйця — 2 шт.\nМолоко — 300 мл',
    instructions:
      '1. Змішайте борошно з яйцями. 2. Додайте молоко. 3. Смажте 5 хв.',
    cooking_time: 30 + id,
  };
}

export function makeSavedRecipes(count) {
  return Array.from({ length: count }, (_, index) =>
    makeSavedRecipe(index + 1),
  );
}

export function makeSuggestion(id) {
  return {
    id,
    title: `Страва ${id}`,
    description: `Опис страви ${id}`,
    cooking_time: 20 + id,
    used_product_ids: [1, 2],
  };
}

export function makeSuggestionsPage(page, { total = 12, pageSize = 8 } = {}) {
  const start = (page - 1) * pageSize;
  const count = Math.max(0, Math.min(pageSize, total - start));

  return {
    items: Array.from({ length: count }, (_, index) =>
      makeSuggestion(start + index),
    ),
    page,
    page_size: pageSize,
    total,
    total_pages: Math.ceil(total / pageSize),
  };
}

export function makeGeneratedRecipe(suggestionId) {
  return {
    title: `Страва ${suggestionId}`,
    description: 'Ситна домашня страва',
    ingredients: 'картопля 500 г, цибуля 1 шт., олія 1,5 ст. л.',
    instructions:
      '1. Наріжте картоплю. 2. Обсмажте цибулю 5 хв. 3. Тушкуйте разом 20 хв.',
    cooking_time: 45,
  };
}

export const RESTRICTIONS = [
  { id: 1, name: 'Веганська' },
  { id: 2, name: 'Без глютену' },
  { id: 3, name: 'Без лактози' },
];

export const CATEGORIES = [
  { id: 1, name: 'Овочі' },
  { id: 2, name: 'Крупи' },
];

export function makeGeneration(overrides = {}) {
  return {
    id: 'g-1',
    status: 'awaiting_products',
    restrictions: [RESTRICTIONS[0]],
    product_ids: [],
    suggestions_total: 0,
    ...overrides,
  };
}

export function makeProduct(id) {
  return { id, name: `Продукт ${id}`, category_id: 1 };
}

export function makeProducts(count, startId = 1) {
  return Array.from({ length: count }, (_, index) =>
    makeProduct(startId + index),
  );
}
