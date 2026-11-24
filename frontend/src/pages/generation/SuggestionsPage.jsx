import { useEffect, useRef, useState } from 'react';
import { FaArrowLeft } from 'react-icons/fa';
import { Link, Navigate, useParams } from 'react-router-dom';
import { getSuggestionsPage } from '../../api/generations.js';
import GenerationError from '../../components/generation/GenerationError.jsx';
import GenerationShell from '../../components/generation/GenerationShell.jsx';
import SuggestionCard from '../../components/suggestions/SuggestionCard.jsx';
import { ROUTES } from '../../routes.js';
import './SuggestionsPage.css';

const TITLE = 'Варіанти рецептів';
const NOT_FOUND_MESSAGE =
  'За обраними інгредієнтами та дієтичними обмеженнями рецептів не знайдено';

export default function SuggestionsPage() {
  const { generationId } = useParams();

  return <SuggestionsView key={generationId} generationId={generationId} />;
}

function SuggestionsView({ generationId }) {
  const [suggestions, setSuggestions] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [moreError, setMoreError] = useState('');
  const [focusId, setFocusId] = useState(null);
  const focusRef = useRef(null);
  const moreControllerRef = useRef(null);

  useEffect(() => {
    const controller = new AbortController();

    getSuggestionsPage(generationId, 1, { signal: controller.signal })
      .then(setSuggestions)
      .catch((error) => {
        if (error.name === 'AbortError') return;
        setLoadError(error);
      });

    return () => controller.abort();
  }, [generationId, reloadKey]);

  useEffect(() => {
    focusRef.current?.focus();
  }, [focusId]);

  useEffect(() => () => moreControllerRef.current?.abort(), []);

  function handleRetry() {
    setLoadError(null);
    setSuggestions(null);
    setReloadKey((current) => current + 1);
  }

  async function handleShowMore() {
    const controller = new AbortController();
    moreControllerRef.current = controller;
    setIsLoadingMore(true);
    setMoreError('');

    try {
      const next = await getSuggestionsPage(
        generationId,
        suggestions.page + 1,
        { signal: controller.signal },
      );
      setSuggestions((current) => ({
        ...next,
        items: [...current.items, ...next.items],
      }));
      setFocusId(next.items[0]?.id ?? null);
    } catch (error) {
      if (error.name === 'AbortError') return;
      setMoreError(error.message);
    } finally {
      setIsLoadingMore(false);
    }
  }

  if (loadError?.code === 'SUGGESTIONS_NOT_READY') {
    return <Navigate to={ROUTES.generationProducts(generationId)} replace />;
  }

  if (loadError) {
    return (
      <GenerationShell step={3} title={TITLE}>
        <GenerationError error={loadError} onRetry={handleRetry} />
      </GenerationShell>
    );
  }

  if (suggestions === null) {
    return (
      <GenerationShell step={3} title={TITLE}>
        <p className='generation__status' role='status'>
          Завантаження варіантів…
        </p>
      </GenerationShell>
    );
  }

  const backLink = (
    <Link
      className='suggestions__back'
      to={ROUTES.generationProducts(generationId)}
    >
      <FaArrowLeft aria-hidden='true' />
      Назад до продуктів
    </Link>
  );

  if (suggestions.items.length === 0) {
    return (
      <GenerationShell step={3} title={TITLE}>
        <div className='generation__card generation__status'>
          <p>{NOT_FOUND_MESSAGE}</p>
          {backLink}
        </div>
      </GenerationShell>
    );
  }

  const hasMore = suggestions.page < suggestions.total_pages;

  return (
    <GenerationShell step={3} title={TITLE}>
      <div className='suggestions__bar'>
        <p className='suggestions__summary'>
          Знайдено варіантів: <strong>{suggestions.total}</strong>. Оберіть
          страву, щоб побачити повний рецепт.
        </p>
        {backLink}
      </div>

      <ul className='suggestions__list'>
        {suggestions.items.map((suggestion) => (
          <li key={suggestion.id}>
            <SuggestionCard
              suggestion={suggestion}
              to={ROUTES.generationRecipe(generationId, suggestion.id)}
              ref={suggestion.id === focusId ? focusRef : undefined}
            />
          </li>
        ))}
      </ul>

      {moreError && (
        <p className='generation__alert suggestions__alert' role='alert'>
          {moreError}
        </p>
      )}

      {hasMore && (
        <div className='suggestions__more'>
          <button
            className='suggestions__more-button'
            type='button'
            onClick={handleShowMore}
            disabled={isLoadingMore}
          >
            {isLoadingMore ? 'Завантаження…' : 'Показати інші рецепти'}
          </button>
        </div>
      )}
    </GenerationShell>
  );
}
