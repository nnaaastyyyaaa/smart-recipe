import { FaChevronLeft, FaChevronRight } from 'react-icons/fa';
import './Pagination.css';

function getPageItems(page, totalPages) {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }

  const items = [1];
  const start = Math.max(2, page - 1);
  const end = Math.min(totalPages - 1, page + 1);

  if (start > 2) items.push('gap-start');
  for (let current = start; current <= end; current += 1) items.push(current);
  if (end < totalPages - 1) items.push('gap-end');

  items.push(totalPages);
  return items;
}

export default function Pagination({ page, totalPages, onChange }) {
  if (totalPages <= 1) return null;

  return (
    <nav className='pagination' aria-label='Сторінки'>
      <button
        className='pagination__button'
        type='button'
        onClick={() => onChange(page - 1)}
        disabled={page <= 1}
        aria-label='Попередня сторінка'
      >
        <FaChevronLeft aria-hidden='true' />
      </button>

      <ul className='pagination__list'>
        {getPageItems(page, totalPages).map((item) =>
          typeof item === 'string' ? (
            <li className='pagination__gap' key={item} aria-hidden='true'>
              …
            </li>
          ) : (
            <li key={item}>
              <button
                className={`pagination__page${item === page ? ' pagination__page--active' : ''}`}
                type='button'
                onClick={() => onChange(item)}
                aria-current={item === page ? 'page' : undefined}
              >
                {item}
              </button>
            </li>
          ),
        )}
      </ul>

      <button
        className='pagination__button'
        type='button'
        onClick={() => onChange(page + 1)}
        disabled={page >= totalPages}
        aria-label='Наступна сторінка'
      >
        <FaChevronRight aria-hidden='true' />
      </button>
    </nav>
  );
}
