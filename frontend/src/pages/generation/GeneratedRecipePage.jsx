import { useEffect, useRef, useState } from 'react';
import { FaArrowLeft, FaHeart, FaRegHeart } from 'react-icons/fa';
import { Link, useParams } from 'react-router-dom';
import { generateRecipe } from '../../api/generations.js';
import { deleteSavedRecipe, saveRecipe } from '../../api/recipes.js';
import RecipeDetails from '../../components/recipe/RecipeDetails.jsx';
import RecipeStatus from '../../components/recipe/RecipeStatus.jsx';
import { ROUTES } from '../../routes.js';
import '../../components/recipe/RecipeControls.css';

const INITIAL_SAVE_STATE = { savedId: null, isBusy: false, error: '' };

function isRetryable(error) {
  return error.status === 0 || error.status === 429 || error.status >= 500;
}

export default function GeneratedRecipePage() {
  const { generationId, suggestionId } = useParams();

  const [outcome, setOutcome] = useState(null);
  const [attempt, setAttempt] = useState(0);
  const [saveState, setSaveState] = useState(INITIAL_SAVE_STATE);
  const lastRequestKey = useRef(null);

  const requestKey = `${generationId}:${suggestionId}:${attempt}`;

  useEffect(() => {
    if (lastRequestKey.current === requestKey) return;
    lastRequestKey.current = requestKey;

    generateRecipe(generationId, Number(suggestionId))
      .then((recipe) => {
        if (lastRequestKey.current !== requestKey) return;
        setOutcome({ key: requestKey, recipe });
      })
      .catch((error) => {
        if (lastRequestKey.current !== requestKey) return;
        setOutcome({ key: requestKey, error });
      });
  }, [generationId, suggestionId, requestKey]);

  async function handleToggleFavorite(recipe) {
    const { savedId } = saveState;
    setSaveState({ savedId, isBusy: true, error: '' });

    try {
      if (savedId === null) {
        const saved = await saveRecipe(recipe);
        setSaveState({ savedId: saved.id, isBusy: false, error: '' });
      } else {
        await deleteSavedRecipe(savedId);
        setSaveState(INITIAL_SAVE_STATE);
      }
    } catch (error) {
      if (savedId !== null && error.status === 404) {
        setSaveState(INITIAL_SAVE_STATE);
        return;
      }

      setSaveState({ savedId, isBusy: false, error: error.message });
    }
  }

  function handleRetry() {
    setSaveState(INITIAL_SAVE_STATE);
    setAttempt((current) => current + 1);
  }

  function renderContent() {
    if (outcome?.key !== requestKey) {
      return (
        <RecipeStatus
          message='Готуємо ваш рецепт…'
          hint='Це може зайняти кілька секунд.'
        />
      );
    }

    if (outcome.error) {
      return (
        <RecipeStatus isError message={outcome.error.message}>
          {isRetryable(outcome.error) && (
            <button
              className='recipe-btn recipe-btn--primary'
              type='button'
              onClick={handleRetry}
            >
              Спробувати ще раз
            </button>
          )}
          <Link className='recipe-btn recipe-btn--outline' to={ROUTES.home}>
            На головну
          </Link>
        </RecipeStatus>
      );
    }

    const isSaved = saveState.savedId !== null;

    return (
      <RecipeDetails
        recipe={outcome.recipe}
        actions={
          <>
            <button
              className={`recipe-btn recipe-favorite${isSaved ? ' recipe-favorite--saved' : ''}`}
              type='button'
              title={isSaved ? 'Прибрати з улюблених' : 'Зберегти в улюблені'}
              onClick={() => handleToggleFavorite(outcome.recipe)}
              disabled={saveState.isBusy}
            >
              {isSaved ? (
                <FaHeart aria-hidden='true' />
              ) : (
                <FaRegHeart aria-hidden='true' />
              )}
              {isSaved ? 'Збережено' : 'Зберегти'}
            </button>

            {saveState.error && (
              <p className='recipe-notice recipe-notice--error' role='alert'>
                {saveState.error}
              </p>
            )}
          </>
        }
      />
    );
  }

  return (
    <section className='recipe-page'>
      <Link
        className='recipe-back'
        to={ROUTES.generationSuggestions(generationId)}
      >
        <FaArrowLeft aria-hidden='true' />
        Назад до варіантів
      </Link>

      {renderContent()}
    </section>
  );
}
