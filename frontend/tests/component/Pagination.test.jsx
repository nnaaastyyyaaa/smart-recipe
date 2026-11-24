import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import Pagination from '../../src/components/common/Pagination.jsx';

function pageLabels() {
  return Array.from(screen.getByRole('list').children).map(
    (item) => item.textContent,
  );
}

describe('Pagination: page list', () => {
  it('hides single page', () => {
    const { container } = render(
      <Pagination page={1} totalPages={1} onChange={vi.fn()} />,
    );

    expect(container).toBeEmptyDOMElement();
  });

  it('shows up to seven pages', () => {
    render(<Pagination page={3} totalPages={7} onChange={vi.fn()} />);

    expect(pageLabels()).toEqual(['1', '2', '3', '4', '5', '6', '7']);
  });

  it.each([
    [1, ['1', '2', '…', '10']],
    [5, ['1', '…', '4', '5', '6', '…', '10']],
    [10, ['1', '…', '9', '10']],
  ])('shortens long list on page %i', (page, expected) => {
    render(<Pagination page={page} totalPages={10} onChange={vi.fn()} />);

    expect(pageLabels()).toEqual(expected);
  });
});

describe('Pagination: navigation controls', () => {
  it('marks current page', () => {
    render(<Pagination page={2} totalPages={3} onChange={vi.fn()} />);

    expect(screen.getByRole('button', { name: '2' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(screen.getByRole('button', { name: '1' })).not.toHaveAttribute(
      'aria-current',
    );
  });

  it('disables arrows at edges', () => {
    const { rerender } = render(
      <Pagination page={1} totalPages={3} onChange={vi.fn()} />,
    );
    expect(
      screen.getByRole('button', { name: 'Попередня сторінка' }),
    ).toBeDisabled();
    expect(
      screen.getByRole('button', { name: 'Наступна сторінка' }),
    ).toBeEnabled();

    rerender(<Pagination page={3} totalPages={3} onChange={vi.fn()} />);
    expect(
      screen.getByRole('button', { name: 'Наступна сторінка' }),
    ).toBeDisabled();
  });

  it('reports selected page', async () => {
    const user = userEvent.setup({ delay: null });
    const onChange = vi.fn();
    render(<Pagination page={2} totalPages={5} onChange={onChange} />);

    await user.click(screen.getByRole('button', { name: 'Наступна сторінка' }));
    await user.click(
      screen.getByRole('button', { name: 'Попередня сторінка' }),
    );
    await user.click(screen.getByRole('button', { name: '5' }));

    expect(onChange.mock.calls).toEqual([[3], [1], [5]]);
  });
});
