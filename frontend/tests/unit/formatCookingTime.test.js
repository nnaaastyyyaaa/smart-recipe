import { describe, expect, it } from 'vitest';
import { formatCookingTime } from '../../src/utils/formatCookingTime.js';

describe('formatCookingTime: time formatting', () => {
  it.each([
    [45, '45 хв'],
    [60, '1 год'],
    [90, '1 год 30 хв'],
    [125, '2 год 5 хв'],
  ])('formats %i minutes as "%s"', (minutes, expected) => {
    expect(formatCookingTime(minutes)).toBe(expected);
  });
});
