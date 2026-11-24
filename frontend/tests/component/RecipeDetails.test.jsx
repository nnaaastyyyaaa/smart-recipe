import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import RecipeDetails from '../../src/components/recipe/RecipeDetails.jsx';
import RecipeStatus from '../../src/components/recipe/RecipeStatus.jsx';
import { makeGeneratedRecipe } from '../support/fixtures.js';

function itemsOf(element) {
  return within(element)
    .getAllByRole('listitem')
    .map((item) => item.textContent);
}

describe('RecipeDetails: recipe content', () => {
  it('shows title, time and description', () => {
    render(<RecipeDetails recipe={makeGeneratedRecipe(1)} />);

    expect(
      screen.getByRole('heading', { level: 1, name: 'Страва 1' }),
    ).toBeInTheDocument();
    expect(screen.getByText('45 хв')).toBeInTheDocument();
    expect(screen.getByText('Ситна домашня страва')).toBeInTheDocument();
  });

  it('lists ingredients', () => {
    render(<RecipeDetails recipe={makeGeneratedRecipe(1)} />);

    const section = screen.getByRole('heading', {
      name: 'Інгредієнти',
    }).parentElement;
    expect(itemsOf(section)).toEqual([
      'Картопля 500 г',
      'Цибуля 1 шт.',
      'Олія 1,5 ст. л.',
    ]);
  });

  it('lists steps in scroll region', () => {
    render(<RecipeDetails recipe={makeGeneratedRecipe(1)} />);

    const region = screen.getByRole('region', { name: 'Приготування' });
    expect(region).toHaveAttribute('tabindex', '0');
    expect(itemsOf(region)).toEqual([
      'Наріжте картоплю.',
      'Обсмажте цибулю 5 хв.',
      'Тушкуйте разом 20 хв.',
    ]);
  });

  it('shows single step as text', () => {
    render(
      <RecipeDetails
        recipe={{ ...makeGeneratedRecipe(1), instructions: 'просто змішайте' }}
      />,
    );

    const region = screen.getByRole('region', { name: 'Приготування' });
    expect(within(region).queryByRole('list')).not.toBeInTheDocument();
    expect(within(region).getByText('Просто змішайте')).toBeInTheDocument();
  });
});

describe('RecipeStatus: loading and errors', () => {
  it('announces loading as status', () => {
    render(<RecipeStatus message='Готуємо ваш рецепт…' hint='Зачекайте' />);

    const status = screen.getByRole('status');
    expect(status).toHaveTextContent('Готуємо ваш рецепт…');
    expect(status).toHaveTextContent('Зачекайте');
  });

  it('announces error as alert', () => {
    render(
      <RecipeStatus isError message='Сервіс недоступний'>
        <button type='button'>Спробувати ще раз</button>
      </RecipeStatus>,
    );

    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent('Сервіс недоступний');
    expect(
      within(alert).getByRole('button', { name: 'Спробувати ще раз' }),
    ).toBeInTheDocument();
  });
});
