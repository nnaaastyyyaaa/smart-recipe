import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { deleteSavedRecipe, getSavedRecipes } from '../../api/recipes.js';
import Pagination from '../common/Pagination.jsx';
import FavoriteRecipeCard from './FavoriteRecipeCard.jsx';
import './FavoritesPanel.css';

const PAGE_SIZE = 12;

export default function FavoritesPanel() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Math.max(1, Number.parseInt(searchParams.get('page'), 10) || 1);

  const [result, setResult] = useState(null);
  const [loadError, setLoadError] = useState('');
  const [deleteError, setDeleteError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();

    getSavedRecipes({
      limit: PAGE_SIZE,
      offset: (page - 1) * PAGE_SIZE,
      signal: controller.signal,
    })
      .then(({ items, total }) => {
        const lastPage = Math.max(1, Math.ceil(total / PAGE_SIZE));

        if (items.length === 0 && page > lastPage) {
          setSearchParams(lastPage === 1 ? {} : { page: String(lastPage) }, {
            replace: true,
          });
          return;
        }

        setLoadError('');
        setResult({ page, reloadKey, items, total });
      })
      .catch((error) => {
        if (error.name === 'AbortError') return;
        setLoadError(error.message);
      });

    return () => controller.abort();
  }, [page, reloadKey, setSearchParams]);

  async function handleDelete(recipe) {
    setDeleteError('');

    try {
      await deleteSavedRecipe(recipe.id);
      setReloadKey((current) => current + 1);
      return true;
    } catch (error) {
      setDeleteError(error.message);
      return false;
    }
  }

  function handlePageChange(nextPage) {
    setSearchParams(nextPage === 1 ? {} : { page: String(nextPage) });
    window.scrollTo({ top: 0 });
  }

  function handleRetry() {
    setLoadError('');
    setReloadKey((current) => current + 1);
  }

  if (loadError) {
    return (
      <div className='favorites__status favorites__status--error' role='alert'>
        <p>{loadError}</p>
        <button
          className='favorites__retry'
          type='button'
          onClick={handleRetry}
        >
          Спробувати ще раз
        </button>
      </div>
    );
  }

  if (result === null) {
    return <p className='favorites__status'>Завантаження…</p>;
  }

  if (result.items.length === 0) {
    return (
      <div className='favorites__empty'>
        <p className='favorites__empty-title'>
          Ви ще не зберегли жодного рецепта
        </p>
        <p className='favorites__empty-text'>
          Згенеруйте рецепт і натисніть «Зберегти», щоб він з'явився тут.
        </p>
      </div>
    );
  }

  const isFetching = result.page !== page || result.reloadKey !== reloadKey;

  return (
    <div className='favorites'>
      <p className='favorites__count'>Збережено рецептів: {result.total}</p>

      {deleteError && (
        <p className='favorites__alert' role='alert'>
          {deleteError}
        </p>
      )}

      <ul
        className={`favorites__grid${isFetching ? ' favorites__grid--busy' : ''}`}
      >
        {result.items.map((recipe) => (
          <li key={recipe.id}>
            <FavoriteRecipeCard recipe={recipe} onDelete={handleDelete} />
          </li>
        ))}
      </ul>

      <Pagination
        page={page}
        totalPages={Math.max(1, Math.ceil(result.total / PAGE_SIZE))}
        onChange={handlePageChange}
      />
    </div>
  );
}
