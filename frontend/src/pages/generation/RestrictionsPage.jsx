import { useEffect, useState } from 'react';
import { FaCheck } from 'react-icons/fa';
import { useNavigate, useParams } from 'react-router-dom';
import { getDietaryRestrictions } from '../../api/catalog.js';
import {
  getGeneration,
  setGenerationRestrictions,
} from '../../api/generations.js';
import GenerationError from '../../components/generation/GenerationError.jsx';
import GenerationShell from '../../components/generation/GenerationShell.jsx';
import { ROUTES } from '../../routes.js';
import './RestrictionsPage.css';

const NOTHING_SELECTED_MESSAGE =
  'Оберіть хоча б одне обмеження або позначте «Обмежень немає».';

export default function RestrictionsPage() {
  const { generationId } = useParams();
  const navigate = useNavigate();

  const [restrictions, setRestrictions] = useState(null);
  const [selectedIds, setSelectedIds] = useState([]);
  const [hasNone, setHasNone] = useState(false);
  const [loadError, setLoadError] = useState(null);
  const [submitError, setSubmitError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    const { signal } = controller;

    Promise.all([
      getDietaryRestrictions({ signal }),
      getGeneration(generationId, { signal }),
    ])
      .then(([allRestrictions, generation]) => {
        setRestrictions(allRestrictions);

        if (generation.status !== 'awaiting_restrictions') {
          setSelectedIds(generation.restrictions.map(({ id }) => id));
          setHasNone(generation.restrictions.length === 0);
        }
      })
      .catch((error) => {
        if (error.name === 'AbortError') return;
        setLoadError(error);
      });

    return () => controller.abort();
  }, [generationId, reloadKey]);

  function toggleRestriction(id) {
    setSelectedIds((current) =>
      current.includes(id)
        ? current.filter((selectedId) => selectedId !== id)
        : [...current, id],
    );
    setHasNone(false);
    setSubmitError('');
  }

  function toggleNone() {
    setHasNone((current) => !current);
    setSelectedIds([]);
    setSubmitError('');
  }

  async function handleSubmit(event) {
    event.preventDefault();

    if (!hasNone && selectedIds.length === 0) {
      setSubmitError(NOTHING_SELECTED_MESSAGE);
      return;
    }

    setIsSubmitting(true);
    setSubmitError('');

    try {
      await setGenerationRestrictions(generationId, hasNone ? [] : selectedIds);
      navigate(ROUTES.generationProducts(generationId));
    } catch (error) {
      setSubmitError(error.message);
      setIsSubmitting(false);
    }
  }

  function handleRetry() {
    setLoadError(null);
    setReloadKey((current) => current + 1);
  }

  let content;

  if (loadError) {
    content = <GenerationError error={loadError} onRetry={handleRetry} />;
  } else if (restrictions === null) {
    content = <p className='generation__status'>Завантаження…</p>;
  } else {
    content = (
      <form className='generation__card' onSubmit={handleSubmit} noValidate>
        <fieldset className='restrictions'>
          <legend className='generation__text'>
            Позначте всі обмеження, яких потрібно дотримуватися. Від цього
            залежить, які продукти будуть доступні на наступному кроці.
          </legend>

          <div className='restrictions__grid'>
            {restrictions.map((restriction) => (
              <label className='restrictions__option' key={restriction.id}>
                <input
                  className='restrictions__checkbox'
                  type='checkbox'
                  checked={selectedIds.includes(restriction.id)}
                  onChange={() => toggleRestriction(restriction.id)}
                />
                <span className='restrictions__box' aria-hidden='true'>
                  <FaCheck />
                </span>
                {restriction.name}
              </label>
            ))}
          </div>

          <label className='restrictions__option restrictions__option--none'>
            <input
              className='restrictions__checkbox'
              type='checkbox'
              checked={hasNone}
              onChange={toggleNone}
            />
            <span className='restrictions__box' aria-hidden='true'>
              <FaCheck />
            </span>
            Обмежень немає
          </label>
        </fieldset>

        {submitError && (
          <p className='generation__alert' role='alert'>
            {submitError}
          </p>
        )}

        <div className='restrictions__actions'>
          <button
            className='generation__button'
            type='submit'
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Збереження…' : 'Далі: вибір продуктів'}
          </button>
        </div>
      </form>
    );
  }

  return (
    <GenerationShell step={1} title='Дієтичні обмеження'>
      {content}
    </GenerationShell>
  );
}