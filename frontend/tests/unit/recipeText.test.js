import { describe, expect, it } from 'vitest';
import { splitIngredients, splitSteps } from '../../src/utils/recipeText.js';

describe('splitIngredients: list parsing', () => {
  it('splits by line breaks', () => {
    expect(splitIngredients('Борошно — 200 г\r\nЯйця — 2 шт.\nМолоко')).toEqual(
      ['Борошно — 200 г', 'Яйця — 2 шт.', 'Молоко'],
    );
  });

  it('strips list markers and separators', () => {
    expect(
      splitIngredients('- борошно 200 г,\n• яйця 2 шт;\n3. молоко'),
    ).toEqual(['Борошно 200 г', 'Яйця 2 шт', 'Молоко']);
  });

  it('splits one line by commas', () => {
    expect(splitIngredients('картопля 500 г, цибуля; , сіль,')).toEqual([
      'Картопля 500 г',
      'Цибуля',
      'Сіль',
    ]);
  });

  it('keeps decimal commas', () => {
    expect(splitIngredients('цукор 1,5 ст. л., вода 0,5 л')).toEqual([
      'Цукор 1,5 ст. л.',
      'Вода 0,5 л',
    ]);
  });

  it('keeps commas in parentheses', () => {
    expect(
      splitIngredients('сіль (дрібна, морська) за смаком, перець'),
    ).toEqual(['Сіль (дрібна, морська) за смаком', 'Перець']);
  });
});

describe('splitSteps: step parsing', () => {
  it('splits by line breaks', () => {
    expect(
      splitSteps('1. Нагрійте духовку.\n2. Змішайте борошно.\n3. Випікайте.'),
    ).toEqual(['Нагрійте духовку.', 'Змішайте борошно.', 'Випікайте.']);
  });

  it('splits by sequential numbers', () => {
    expect(
      splitSteps(
        '1. Нагрійте духовку до 180 градусів. 2. Змішайте 2 яйця з цукром. 3. Випікайте 25 хв.',
      ),
    ).toEqual([
      'Нагрійте духовку до 180 градусів.',
      'Змішайте 2 яйця з цукром.',
      'Випікайте 25 хв.',
    ]);
  });

  it('ignores out-of-order numbers', () => {
    expect(splitSteps('1. Змішайте все 3. подавайте')).toEqual([
      'Змішайте все 3. подавайте',
    ]);
  });

  it('keeps unnumbered text whole', () => {
    expect(splitSteps('Змішайте все й подавайте')).toEqual([
      'Змішайте все й подавайте',
    ]);
  });
});

describe('splitSteps: capitalization', () => {
  it('capitalizes each sentence', () => {
    expect(splitSteps('нагрійте духовку. змішайте все.')).toEqual([
      'Нагрійте духовку. Змішайте все.',
    ]);
  });

  it('skips letters after abbreviations', () => {
    expect(splitSteps('варіть 10 хв. на слабкому вогні')).toEqual([
      'Варіть 10 хв. на слабкому вогні',
    ]);
  });
});
