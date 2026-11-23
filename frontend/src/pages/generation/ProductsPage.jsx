import { useEffect, useState } from 'react';
import {
  FaCheck,
  FaChevronLeft,
  FaChevronRight,
  FaSearch,
  FaTimes,
} from 'react-icons/fa';
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom';
import {
  getGeneration,
  getGenerationCategories,
  getGenerationProducts,
  suggestRecipes,
} from '../../api/generations.js';
import GenerationError from '../../components/generation/GenerationError.jsx';
import GenerationShell from '../../components/generation/GenerationShell.jsx';
import { useDebouncedValue } from '../../hooks/useDebouncedValue.js';
import { ROUTES } from '../../routes.js';
import './ProductsPage.css';

export const PAGE_SIZE = 24;
export const MIN_PRODUCTS = 2;
export const MAX_PRODUCTS = 30;

export default function ProductsPage() {
  const { generationId } = useParams();
  const navigate = useNavigate();

  const [generation, setGeneration] = useState(null);
  const [categories, setCategories] = useState([]);
  const [loadError, setLoadError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  const [search, setSearch] = useState('');
  const [categoryId, setCategoryId] = useState(null);
  const [page, setPage] = useState(1);
  const debouncedSearch = useDebouncedValue(search.trim());

  const [products, setProducts] = useState(null);
  const [productsError, setProductsError] = useState('');

  const [selected, setSelected] = useState([]);
  const [submitError, setSubmitError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    const { signal } = controller;

    Promise.all([
      getGeneration(generationId, { signal }),
      getGenerationCategories(generationId, { signal }),
    ])
      .then(([nextGeneration, nextCategories]) => {
        setGeneration(nextGeneration);
        setCategories(nextCategories);
      })
      .catch((error) => {
        if (error.name === 'AbortError') return;
        setLoadError(error);
      });

    return () => controller.abort();
  }, [generationId, reloadKey]);

  useEffect(() => {
    const controller = new AbortController();

    getGenerationProducts(generationId, {
      categoryId: categoryId ?? undefined,
      search: debouncedSearch || undefined,
      limit: PAGE_SIZE + 1,
      offset: (page - 1) * PAGE_SIZE,
      signal: controller.signal,
    })
      .then((items) => {
        setProductsError('');
        setProducts({
          key: `${categoryId}|${debouncedSearch}|${page}`,
          items: items.slice(0, PAGE_SIZE),
          hasNext: items.length > PAGE_SIZE,
        });
      })
      .catch((error) => {
        if (error.name === 'AbortError') return;
        setProductsError(error.message);
      });

    return () => controller.abort();
  }, [generationId, categoryId, debouncedSearch, page, reloadKey]);

  const selectedIds = new Set(selected.map(({ id }) => id));
  const isLimitReached = selected.length >= MAX_PRODUCTS;

  function toggleProduct(product) {
    setSelected((current) =>
      current.some(({ id }) => id === product.id)
        ? current.filter(({ id }) => id !== product.id)
        : [...current, product],
    );
    setSubmitError('');
  }

  function handleSearchChange(event) {
    setSearch(event.target.value);
    setPage(1);
  }

  function handleCategoryChange(nextCategoryId) {
    setCategoryId(nextCategoryId);
    setPage(1);
  }

  function handleRetry() {
    setLoadError(null);
    setProductsError('');
    setReloadKey((current) => current + 1);
  }

  async function handleSubmit() {
    setIsSubmitting(true);
    setSubmitError('');

    try {
      await suggestRecipes(
        generationId,
        selected.map(({ id }) => id),
      );
      navigate(ROUTES.generationSuggestions(generationId));
    } catch (error) {
      setSubmitError(error.message);
      setIsSubmitting(false);
    }
  }

  if (
    generation?.status === 'awaiting_restrictions' ||
    loadError?.code === 'RESTRICTIONS_NOT_SELECTED'
  ) {
    return (
      <Navigate to={ROUTES.generationRestrictions(generationId)} replace />
    );
  }

  if (loadError) {
    return (
      <GenerationShell step={2} title='Оберіть продукти'>
        <GenerationError error={loadError} onRetry={handleRetry} />
      </GenerationShell>
    );
  }

  if (generation === null) {
    return (
      <GenerationShell step={2} title='Оберіть продукти'>
        <p className='generation__status'>Завантаження…</p>
      </GenerationShell>
    );
  }

  const currentKey = `${categoryId}|${debouncedSearch}|${page}`;
  const isFetching = products !== null && products.key !== currentKey;
  const categoryNames = new Map(categories.map(({ id, name }) => [id, name]));

  return (
    <GenerationShell step={2} title='Оберіть продукти'>
      <p className='products__restrictions'>
        <span>Обмеження:</span>
        {generation.restrictions.length === 0 ? (
          <span className='products__tag'>немає</span>
        ) : (
          generation.restrictions.map(({ id, name }) => (
            <span className='products__tag' key={id}>
              {name}
            </span>
          ))
        )}
        <Link
          className='products__change'
          to={ROUTES.generationRestrictions(generationId)}
        >
          Змінити
        </Link>
      </p>

      <div className='products'>
        <div className='products__catalog generation__card'>
          <div className='products__filters'>
            <label className='products__search'>
              <FaSearch className='products__search-icon' aria-hidden='true' />
              <span className='products__sr'>Пошук продуктів</span>
              <input
                className='products__input products__input--search'
                type='search'
                placeholder='Пошук продуктів'
                maxLength={60}
                value={search}
                onChange={handleSearchChange}
              />
            </label>

            <label className='products__filter'>
              <span className='products__sr'>Категорія</span>
              <select
                className='products__input'
                value={categoryId ?? ''}
                onChange={(event) =>
                  handleCategoryChange(
                    event.target.value ? Number(event.target.value) : null,
                  )
                }
              >
                <option value=''>Усі категорії</option>
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {productsError && (
            <div className='generation__alert' role='alert'>
              {productsError}{' '}
              <button
                className='products__retry'
                type='button'
                onClick={handleRetry}
              >
                Спробувати ще раз
              </button>
            </div>
          )}

          {products === null && !productsError && (
            <p className='generation__status'>Завантаження…</p>
          )}

          {products !== null && products.items.length === 0 && (
            <p className='generation__status'>
              Нічого не знайдено. Спробуйте змінити пошук або категорію.
            </p>
          )}

          {products !== null && products.items.length > 0 && (
            <ul
              className={`products__grid${isFetching ? ' products__grid--busy' : ''}`}
            >
              {products.items.map((product) => {
                const isSelected = selectedIds.has(product.id);

                return (
                  <li key={product.id}>
                    <button
                      className='products__item'
                      type='button'
                      aria-pressed={isSelected}
                      disabled={!isSelected && isLimitReached}
                      onClick={() => toggleProduct(product)}
                    >
                      <span className='products__check' aria-hidden='true'>
                        <FaCheck />
                      </span>
                      <span className='products__item-text'>
                        <span className='products__name'>{product.name}</span>
                        <span className='products__category-name'>
                          {categoryNames.get(product.category_id)}
                        </span>
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}

          {products !== null && (page > 1 || products.hasNext) && (
            <nav className='products__pager' aria-label='Сторінки продуктів'>
              <button
                className='products__pager-button'
                type='button'
                onClick={() => setPage((current) => current - 1)}
                disabled={page <= 1}
                aria-label='Попередня сторінка'
              >
                <FaChevronLeft aria-hidden='true' />
              </button>
              <span className='products__pager-page'>Сторінка {page}</span>
              <button
                className='products__pager-button'
                type='button'
                onClick={() => setPage((current) => current + 1)}
                disabled={!products.hasNext}
                aria-label='Наступна сторінка'
              >
                <FaChevronRight aria-hidden='true' />
              </button>
            </nav>
          )}
        </div>

        <aside className='products__selected generation__card'>
          <h2 className='products__heading'>
            Ваш вибір{' '}
            <span className='products__counter'>
              {selected.length}/{MAX_PRODUCTS}
            </span>
          </h2>

          {selected.length === 0 ? (
            <p className='products__hint'>
              Позначте продукти, які є у вас вдома. Потрібно щонайменше{' '}
              {MIN_PRODUCTS}.
            </p>
          ) : (
            <ul className='products__chips'>
              {selected.map((product) => (
                <li className='products__chip' key={product.id}>
                  {product.name}
                  <button
                    className='products__chip-remove'
                    type='button'
                    onClick={() => toggleProduct(product)}
                    aria-label={`Прибрати «${product.name}»`}
                  >
                    <FaTimes aria-hidden='true' />
                  </button>
                </li>
              ))}
            </ul>
          )}

          {isLimitReached && (
            <p className='products__hint'>
              Обрано максимальну кількість продуктів.
            </p>
          )}

          {submitError && (
            <p className='generation__alert' role='alert'>
              {submitError}
            </p>
          )}

          <button
            className='generation__button products__submit'
            type='button'
            onClick={handleSubmit}
            disabled={selected.length < MIN_PRODUCTS || isSubmitting}
          >
            {isSubmitting ? 'Підбираємо рецепти…' : 'Підібрати рецепти'}
          </button>
        </aside>
      </div>
    </GenerationShell>
  );
}