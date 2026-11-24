import { useEffect, useState } from 'react';
import { FaArrowLeft, FaRegTrashAlt } from 'react-icons/fa';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { deleteSavedRecipe, getSavedRecipe } from '../../api/recipes.js';
import ProfileShell from '../../components/profile/ProfileShell.jsx';
import RecipeDetails from '../../components/recipe/RecipeDetails.jsx';
import RecipeStatus from '../../components/recipe/RecipeStatus.jsx';
import { ROUTES } from '../../routes.js';
import '../../components/recipe/RecipeControls.css';

const NOT_FOUND_STATUS = 404;

export default function FavoriteRecipePage() {
  const { recipeId } = useParams();
  const navigate = useNavigate();

  const [outcome, setOutcome] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [deleteStep, setDeleteStep] = useState('idle');
  const [deleteError, setDeleteError] = useState('');

  const requestKey = `${recipeId}:${reloadKey}`;

  useEffect(() => {
    const controller = new AbortController();

    getSavedRecipe(recipeId, { signal: controller.signal })
      .then((recipe) => setOutcome({ key: requestKey, recipe }))
      .catch((error) => {
        if (error.name === 'AbortError') return;
        setOutcome({ key: requestKey, error });
      });

    return () => controller.abort();
  }, [recipeId, requestKey]);

  async function handleDelete() {
    setDeleteStep('deleting');
    setDeleteError('');

    try {
      await deleteSavedRecipe(recipeId);
      navigate(ROUTES.favorites, { replace: true });
    } catch (error) {
      setDeleteError(error.message);
      setDeleteStep('idle');
    }
  }

  function renderContent() {
    if (outcome?.key !== requestKey) {
      return <RecipeStatus message='Завантаження рецепта…' />;
    }

    if (outcome.error) {
      return (
        <RecipeStatus isError message={outcome.error.message}>
          {outcome.error.status !== NOT_FOUND_STATUS && (
            <button
              className='recipe-btn recipe-btn--primary'
              type='button'
              onClick={() => setReloadKey((current) => current + 1)}
            >
              Спробувати ще раз
            </button>
          )}
        </RecipeStatus>
      );
    }

    return (
      <RecipeDetails
        recipe={outcome.recipe}
        actions={
          <>
            {deleteStep === 'idle' ? (
              <button
                className='recipe-btn recipe-btn--danger-outline'
                type='button'
                onClick={() => setDeleteStep('confirm')}
              >
                <FaRegTrashAlt aria-hidden='true' />
                Видалити рецепт
              </button>
            ) : (
              <div className='recipe-confirm'>
                <span className='recipe-confirm__text'>
                  Видалити цей рецепт?
                </span>
                <button
                  className='recipe-btn recipe-btn--danger'
                  type='button'
                  onClick={handleDelete}
                  disabled={deleteStep === 'deleting'}
                >
                  Так, видалити
                </button>
                <button
                  className='recipe-btn recipe-btn--outline'
                  type='button'
                  onClick={() => setDeleteStep('idle')}
                  disabled={deleteStep === 'deleting'}
                >
                  Скасувати
                </button>
              </div>
            )}

            {deleteError && (
              <p className='recipe-notice recipe-notice--error' role='alert'>
                {deleteError}
              </p>
            )}
          </>
        }
      />
    );
  }

  return (
    <ProfileShell>
      <Link className='recipe-back' to={ROUTES.favorites}>
        <FaArrowLeft aria-hidden='true' />
        До улюблених рецептів
      </Link>

      {renderContent()}
    </ProfileShell>
  );
}
